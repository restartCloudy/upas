"""
UPAS - 通用抽象形态系统
六维评估引擎
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易记录"""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    direction: str  # 'long' or 'short'
    holding_days: int
    
    @property
    def return_pct(self) -> float:
        if self.direction == 'long':
            return (self.exit_price - self.entry_price) / self.entry_price * 100
        else:
            return (self.entry_price - self.exit_price) / self.entry_price * 100


class SixDimensionEvaluator:
    """
    六维评估系统
    
    维度：
    1. 市场板块（主板/创业板/科创板）
    2. 策略模式（右侧追涨/超跌低吸/趋势跟踪/震荡套利）
    3. 持有周期（T+1/T+3/T+5/T+10/T+20）
    4. 行业板块（科技/医药/消费/周期/金融/制造）
    5. 市值分层（大盘/中盘/小盘/微盘）
    6. 波动率环境（低/中/高/极端）
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'holding_periods': [1, 3, 5, 10, 20],
            'min_samples': 5,
            'commission': 0.00025,
            'slippage': 0.001,
            'output_raw_data': False
        }
        
        self.dimensions = {
            'market': ['主板', '创业板', '科创板', '北交所'],
            'strategy': ['右侧追涨', '超跌低吸', '趋势跟踪', '震荡套利'],
            'sector': ['科技', '医药', '消费', '周期', '金融', '制造', '其他'],
            'market_cap': ['大盘', '中盘', '小盘', '微盘'],
            'vol_regime': ['低波动', '中波动', '高波动', '极端波动']
        }
    
    def create_slices(self, trades_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        创建六维交叉切片
        
        Returns:
            切片字典，key为"市场_策略_T+N"格式
        """
        if trades_df.empty:
            return {}
        
        slices = {}
        
        for market in self.dimensions['market']:
            if 'market' in trades_df.columns:
                market_data = trades_df[trades_df['market'] == market]
            else:
                market_data = trades_df  # 如果没有市场列，使用全部数据
            
            if market_data.empty:
                continue
            
            for strategy in self.dimensions['strategy']:
                strategy_data = self._apply_strategy_filter(market_data, strategy)
                
                if strategy_data.empty:
                    continue
                
                for holding in self.config['holding_periods']:
                    # 按持有期截断收益
                    slice_data = strategy_data.copy()
                    
                    if 'return_pct' in slice_data.columns:
                        # 已经计算好收益率
                        pass
                    else:
                        # 需要计算收益率
                        slice_data['return_pct'] = slice_data.apply(
                            lambda x: self._calculate_holding_return(x, holding), axis=1
                        )
                    
                    # 添加持有期标记
                    slice_data['target_holding'] = holding
                    
                    slice_key = f"{market}_{strategy}_T+{holding}"
                    slices[slice_key] = slice_data
        
        return slices
    
    def _apply_strategy_filter(self, df: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """应用策略过滤条件"""
        
        if df.empty:
            return df
        
        filters = {
            '右侧追涨': lambda x: (
                (x.get('trend') == 'up' if 'trend' in x else True) and
                (x.get('adx', 0) > 25 if 'adx' in x else True) and
                (x.get('rsi', 50) > 50 if 'rsi' in x else True)
            ),
            '超跌低吸': lambda x: (
                (x.get('rsi', 50) < 30 if 'rsi' in x else False) or
                (x.get('distance_60ma', 0) < -0.15 if 'distance_60ma' in x else False)
            ),
            '趋势跟踪': lambda x: (
                (x.get('ma20', 0) > x.get('ma60', 0) if 'ma20' in x and 'ma60' in x else True) and
                (x.get('volume_5d', 0) > x.get('volume_20d', 0) if 'volume_5d' in x else True)
            ),
            '震荡套利': lambda x: (
                (x.get('adx', 100) < 25 if 'adx' in x else False) or
                (x.get('bb_width', 1) < 0.1 if 'bb_width' in x else False)
            )
        }
        
        if strategy in filters:
            try:
                mask = df.apply(filters[strategy], axis=1)
                return df[mask]
            except:
                return df
        
        return df
    
    def _calculate_holding_return(self, trade_row: pd.Series, days: int) -> float:
        """计算指定持有期的收益"""
        
        actual_holding = trade_row.get('holding_days', days)
        
        if 'return_pct' in trade_row:
            full_return = trade_row['return_pct']
        elif 'exit_price' in trade_row and 'entry_price' in trade_row:
            full_return = (trade_row['exit_price'] - trade_row['entry_price']) / trade_row['entry_price'] * 100
        else:
            return 0.0
        
        if actual_holding >= days:
            # 简化处理：按比例计算
            return full_return * min(days / max(actual_holding, 1), 1.0)
        else:
            return full_return
    
    def evaluate_slice(self, slice_df: pd.DataFrame) -> Dict:
        """评估单个切片的表现"""
        
        if len(slice_df) < self.config['min_samples']:
            return {
                'sample_size': len(slice_df),
                'valid': False,
                'reason': '样本不足'
            }
        
        returns = slice_df['return_pct'].dropna().values
        
        if len(returns) == 0:
            return {
                'sample_size': 0,
                'valid': False,
                'reason': '无有效收益率数据'
            }
        
        # 基础指标
        win_rate = (returns > 0).mean()
        avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
        avg_loss = returns[returns < 0].mean() if (returns < 0).any() else 0
        risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # 期望收益
        expectancy = win_rate * avg_win - (1 - win_rate) * abs(avg_loss)
        
        # 夏普比率（年化）- 修复：使用正确的holding_days
        if returns.std() > 0:
            # 从切片键中提取持有期，或使用默认值
            holding_days = 5  # 默认值
            if 'target_holding' in slice_df.columns and len(slice_df) > 0:
                holding_days = slice_df['target_holding'].iloc[0]
            elif 'holding_days' in slice_df.columns and len(slice_df) > 0:
                holding_days = slice_df['holding_days'].iloc[0]
            
            sharpe = returns.mean() / (returns.std() + 1e-10) * np.sqrt(252 / max(holding_days, 1))
        else:
            sharpe = 0
        
        # 最大回撤
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        # 连续亏损
        consecutive_losses = self._calculate_consecutive_losses(returns)
        
        # 经成本调整的收益
        cost = (self.config['commission'] * 2 + self.config['slippage'] * 2) * 100
        adjusted_returns = returns - cost
        net_expectancy = adjusted_returns.mean()
        
        return {
            'sample_size': len(returns),
            'valid': True,
            'win_rate': float(win_rate),
            'risk_reward': float(risk_reward) if risk_reward != float('inf') else 999,
            'expectancy': float(expectancy),
            'net_expectancy': float(net_expectancy),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': float(max_drawdown),
            'consecutive_losses': int(consecutive_losses),
            'avg_return': float(returns.mean()),
            'volatility': float(returns.std()),
            'skewness': float(pd.Series(returns).skew()) if len(returns) > 2 else 0,
            'kurtosis': float(pd.Series(returns).kurtosis()) if len(returns) > 3 else 0,
            'min_return': float(returns.min()),
            'max_return': float(returns.max())
        }
    
    def _calculate_consecutive_losses(self, returns: np.ndarray) -> int:
        """计算最大连续亏损次数"""
        
        if len(returns) == 0:
            return 0
        
        losses = returns < 0
        max_consecutive = 0
        current = 0
        
        for loss in losses:
            if loss:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 0
        
        return max_consecutive
    
    def generate_report(self, 
                       pattern_id: str,
                       slices: Dict[str, pd.DataFrame]) -> Dict:
        """生成形态的全维度评估报告"""
        
        # 评估所有切片
        slice_results = {}
        for key, df in slices.items():
            result = self.evaluate_slice(df)
            if result['valid']:
                slice_results[key] = result
        
        if not slice_results:
            return {
                'pattern_id': pattern_id,
                'status': 'INSUFFICIENT_DATA',
                'message': '所有切片样本不足，无法评估',
                'evaluated_at': pd.Timestamp.now().isoformat()
            }
        
        # 计算综合得分
        scorecard = self._calculate_comprehensive_score(slice_results)
        
        # 找出最佳场景
        sorted_scenarios = sorted(
            slice_results.items(),
            key=lambda x: x[1]['expectancy'],
            reverse=True
        )
        
        best_scenarios = sorted_scenarios[:5]
        worst_scenarios = sorted_scenarios[-3:] if len(sorted_scenarios) >= 3 else sorted_scenarios
        
        # 按维度聚合
        dimension_analysis = self._analyze_by_dimensions(slice_results)
        
        return {
            'pattern_id': pattern_id,
            'status': 'VALIDATED',
            'comprehensive_score': float(scorecard['total_score']),
            'rating': scorecard['rating'],
            'recommendation': scorecard['recommendation'],
            'dimension_scores': scorecard['dimension_scores'],
            'best_scenarios': [
                {
                    'scenario': k,
                    'win_rate': round(v['win_rate'] * 100, 1),
                    'expectancy': round(v['expectancy'], 2),
                    'sharpe': round(v['sharpe_ratio'], 2),
                    'sample_size': v['sample_size']
                }
                for k, v in best_scenarios
            ],
            'worst_scenarios': [
                {
                    'scenario': k,
                    'win_rate': round(v['win_rate'] * 100, 1),
                    'expectancy': round(v['expectancy'], 2)
                }
                for k, v in worst_scenarios
            ],
            'dimension_analysis': dimension_analysis,
            'total_trades': sum(r['sample_size'] for r in slice_results.values()),
            'avg_win_rate': round(np.mean([r['win_rate'] for r in slice_results.values()]) * 100, 1),
            'avg_expectancy': round(np.mean([r['expectancy'] for r in slice_results.values()]), 2),
            'evaluated_at': pd.Timestamp.now().isoformat()
        }
    
    def _calculate_comprehensive_score(self, slice_results: Dict) -> Dict:
        """计算综合评分"""
        
        weights = {
            'profitability': 0.25,     # 盈利能力
            'consistency': 0.20,       # 稳定性
            'adaptability': 0.15,      # 适应性
            'risk_control': 0.20,      # 风险控制
            'capacity': 0.10,          # 容量
            'timeliness': 0.10         # 及时性
        }
        
        scores = {}
        
        # 1. 盈利能力
        expectancies = [r['expectancy'] for r in slice_results.values()]
        scores['profitability'] = min(1.0, max(0, np.mean(expectancies) / 5 + 0.5))
        
        # 2. 稳定性（夏普比率）
        sharpes = [r['sharpe_ratio'] for r in slice_results.values()]
        scores['consistency'] = min(1.0, max(0, np.mean(sharpes) / 2 + 0.5))
        
        # 3. 适应性（跨场景标准差倒数）
        exp_std = np.std(expectancies)
        scores['adaptability'] = min(1.0, max(0, 1 - exp_std / 5))
        
        # 4. 风险控制（回撤控制）
        drawdowns = [r['max_drawdown'] for r in slice_results.values()]
        scores['risk_control'] = min(1.0, max(0, 1 + np.mean(drawdowns) / 20))
        
        # 5. 容量（样本量）
        samples = [r['sample_size'] for r in slice_results.values()]
        scores['capacity'] = min(1.0, np.sum(samples) / 500)
        
        # 6. 及时性（T+1表现）
        t1_scenarios = {k: v for k, v in slice_results.items() if 'T+1' in k}
        if t1_scenarios:
            t1_expectancies = [r['expectancy'] for r in t1_scenarios.values()]
            scores['timeliness'] = min(1.0, max(0, np.mean(t1_expectancies) / 3 + 0.5))
        else:
            scores['timeliness'] = 0.5
        
        # 综合得分
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        # 评级
        if total_score >= 0.8:
            rating = 'A'
            recommendation = '核心形态：适合作为策略主力'
        elif total_score >= 0.6:
            if scores['adaptability'] >= 0.7:
                rating = 'B+'
                recommendation = '稳健形态：适合作为策略补充'
            else:
                rating = 'B'
                recommendation = '场景形态：特定条件下使用'
        elif total_score >= 0.4:
            rating = 'C'
            recommendation = '观察形态：需进一步优化'
        else:
            rating = 'D'
            recommendation = '废弃形态：不建议使用'
        
        return {
            'total_score': float(total_score),
            'dimension_scores': {k: round(v, 2) for k, v in scores.items()},
            'rating': rating,
            'recommendation': recommendation
        }
    
    def _analyze_by_dimensions(self, slice_results: Dict) -> Dict:
        """按维度分析表现"""
        
        analysis = {}
        
        # 按市场分析
        market_performance = {}
        for market in self.dimensions['market']:
            market_scenarios = {k: v for k, v in slice_results.items() if k.startswith(market)}
            if market_scenarios:
                market_performance[market] = {
                    'avg_expectancy': round(np.mean([s['expectancy'] for s in market_scenarios.values()]), 2),
                    'avg_win_rate': round(np.mean([s['win_rate'] for s in market_scenarios.values()]) * 100, 1),
                    'scenario_count': len(market_scenarios)
                }
        analysis['by_market'] = market_performance
        
        # 按策略分析
        strategy_performance = {}
        for strategy in self.dimensions['strategy']:
            strategy_scenarios = {k: v for k, v in slice_results.items() if strategy in k}
            if strategy_scenarios:
                strategy_performance[strategy] = {
                    'avg_expectancy': round(np.mean([s['expectancy'] for s in strategy_scenarios.values()]), 2),
                    'avg_win_rate': round(np.mean([s['win_rate'] for s in strategy_scenarios.values()]) * 100, 1),
                    'scenario_count': len(strategy_scenarios)
                }
        analysis['by_strategy'] = strategy_performance
        
        # 按持有期分析
        period_performance = {}
        for period in self.config['holding_periods']:
            period_key = f"T+{period}"
            period_scenarios = {k: v for k, v in slice_results.items() if period_key in k}
            if period_scenarios:
                period_performance[period_key] = {
                    'avg_expectancy': round(np.mean([s['expectancy'] for s in period_scenarios.values()]), 2),
                    'avg_win_rate': round(np.mean([s['win_rate'] for s in period_scenarios.values()]) * 100, 1),
                    'scenario_count': len(period_scenarios)
                }
        analysis['by_period'] = period_performance
        
        return analysis
    
    def dynamic_weight_adjustment(self, market_regime: str) -> Dict:
        """根据市场状态动态调整评估权重"""
        
        base_weights = {
            'profitability': 0.25,
            'consistency': 0.20,
            'adaptability': 0.15,
            'risk_control': 0.20,
            'capacity': 0.10,
            'timeliness': 0.10
        }
        
        adjustments = {
            '强趋势': {
                'profitability': +0.10,
                'risk_control': -0.05,
                'timeliness': +0.05
            },
            '高波动': {
                'consistency': +0.10,
                'risk_control': +0.10,
                'profitability': -0.10,
                'capacity': -0.05
            },
            '震荡市': {
                'adaptability': +0.10,
                'timeliness': +0.05,
                'capacity': +0.05
            },
            '低波动': {
                'consistency': +0.05,
                'capacity': +0.05,
                'timeliness': -0.05
            }
        }
        
        if market_regime in adjustments:
            adj = adjustments[market_regime]
            adjusted = {k: base_weights[k] + adj.get(k, 0) for k in base_weights}
            total = sum(adjusted.values())
            return {k: round(v/total, 3) for k, v in adjusted.items()}
        
        return base_weights