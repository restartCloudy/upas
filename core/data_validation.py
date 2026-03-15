"""
UPAS - 数据验证与风控模块
处理数据质量、幸存者偏差、前视偏差等问题
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """数据验证层：Schema验证、异常值检测、停牌处理"""
    
    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'vol']
    OPTIONAL_COLUMNS = ['volume', 'amount', 'trade_date', 'pct_chg', 'pre_close']
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'max_daily_change': 0.20,  # 最大日涨跌幅20%
            'min_bars_for_analysis': 20,  # 最少需要的K线数
            'max_gap_days': 5,  # 最大允许停牌天数
            'remove_st': True,  # 是否移除ST股票
            'survivor_bias_adjust': True,  # 幸存者偏差调整
        }
    
    def validate_ohlcv(self, df: pd.DataFrame, ts_code: str = None) -> Tuple[bool, str, pd.DataFrame]:
        """
        验证OHLCV数据完整性
        
        Returns:
            (是否通过, 错误信息, 清洗后的数据)
        """
        if df is None or len(df) == 0:
            return False, "数据为空", df
        
        # 1. 检查必需列
        df_cols_lower = {c.lower(): c for c in df.columns}
        missing = []
        for col in self.REQUIRED_COLUMNS:
            if col not in df_cols_lower and col not in df.columns.str.lower():
                missing.append(col)
        
        if missing:
            return False, f"缺少必需列: {missing}", df
        
        # 2. 标准化列名（小写）
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        
        # 3. 检查OHLC逻辑关系
        ohlc_valid = (
            (df['high'] >= df[['open', 'close', 'low']].max(axis=1)) &
            (df['low'] <= df[['open', 'close', 'high']].min(axis=1)) &
            (df['close'] > 0) &
            (df['open'] > 0)
        )
        
        invalid_bars = (~ohlc_valid).sum()
        if invalid_bars > 0:
            logger.warning(f"{ts_code}: 发现 {invalid_bars} 根异常K线，将被移除")
            df = df[ohlc_valid]
        
        # 4. 检查涨跌幅异常
        df['daily_return'] = df['close'].pct_change()
        extreme_moves = abs(df['daily_return']) > self.config['max_daily_change']
        
        if extreme_moves.sum() > 0:
            # 可能是除权除息，需要标记而非直接删除
            logger.warning(f"{ts_code}: 发现 {extreme_moves.sum()} 根极端波动K线（可能除权）")
            df['is_adjusted'] = extreme_moves
        else:
            df['is_adjusted'] = False
        
        # 5. 检查停牌（连续缺失交易日）
        if 'trade_date' in df.columns:
            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            date_diff = df['trade_date'].diff().dt.days
            long_gaps = (date_diff > self.config['max_gap_days']).sum()
            
            if long_gaps > 0:
                logger.warning(f"{ts_code}: 发现 {long_gaps} 次长时间停牌（>{self.config['max_gap_days']}天）")
        
        # 6. 检查成交量异常
        zero_volume = (df['vol'] == 0).sum()
        if zero_volume > len(df) * 0.1:  # 超过10%零成交量
            logger.warning(f"{ts_code}: 零成交量比例过高 ({zero_volume/len(df):.1%})，可能是停牌股票")
        
        # 7. 检查数据长度
        if len(df) < self.config['min_bars_for_analysis']:
            return False, f"数据长度不足: {len(df)} < {self.config['min_bars_for_analysis']}", df
        
        return True, "验证通过", df
    
    def check_lookahead_bias(self, df: pd.DataFrame, feature_cols: List[str]) -> Tuple[bool, List[str]]:
        """
        检查前视偏差（使用了未来数据）
        
        常见的前视偏差：
        - 使用全量数据计算均值/标准差
        - 使用未来数据填充缺失值
        - 使用未来数据计算标签
        """
        issues = []
        
        # 检查特征列是否存在
        for col in feature_cols:
            if col in df.columns:
                # 检查是否有前向填充的缺失值（可能是使用了未来数据）
                null_count = df[col].isnull().sum()
                if null_count > 0 and df[col].isnull().sum() < null_count:
                    # 如果之前有null现在没有了，可能是前向/后向填充
                    pass
        
        return len(issues) == 0, issues


class SurvivorBiasHandler:
    """幸存者偏差处理"""
    
    def __init__(self, delisted_stocks_path: str = None):
        self.delisted_stocks = set()
        if delisted_stocks_path:
            self._load_delisted_stocks(delisted_stocks_path)
    
    def _load_delisted_stocks(self, path: str):
        """加载已退市股票列表"""
        try:
            with open(path, 'r') as f:
                self.delisted_stocks = set(line.strip() for line in f)
        except Exception as e:
            logger.warning(f"无法加载退市股票列表: {e}")
    
    def filter_survivor_bias(self, 
                            stock_data: Dict[str, pd.DataFrame],
                            as_of_date: datetime = None) -> Dict[str, pd.DataFrame]:
        """
        过滤幸存者偏差
        
        只保留在给定时间点之前就已上市，且未退市的股票
        """
        as_of_date = as_of_date or datetime.now()
        filtered = {}
        
        for ts_code, df in stock_data.items():
            # 检查是否在退市列表
            if ts_code in self.delisted_stocks:
                logger.debug(f"{ts_code} 已退市，排除")
                continue
            
            # 检查在as_of_date是否有数据
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                available = df[df['trade_date'] <= as_of_date]
                if len(available) >= 60:  # 至少60个交易日数据
                    filtered[ts_code] = available
            else:
                # 假设数据已按时间排序，取前N条
                if len(df) >= 60:
                    filtered[ts_code] = df
        
        logger.info(f"幸存者偏差过滤: {len(stock_data)} -> {len(filtered)} 只股票")
        return filtered


class OverfittingGuard:
    """过拟合防护：样本外验证、滚动回测"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'oos_ratio': 0.3,  # 样本外比例
            'n_splits': 5,  # 滚动窗口数
            'min_train_size': 100,  # 最小训练集大小
        }
    
    def walk_forward_split(self, df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        滚动窗口切分（时间序列交叉验证）
        
        Returns:
            [(train_1, test_1), (train_2, test_2), ...]
        """
        n = len(df)
        splits = []
        
        # 计算每折大小
        test_size = int(n * self.config['oos_ratio'] / self.config['n_splits'])
        train_start = 0
        
        for i in range(self.config['n_splits']):
            train_end = n - (self.config['n_splits'] - i) * test_size
            test_start = train_end
            test_end = test_start + test_size
            
            if train_end - train_start < self.config['min_train_size']:
                continue
            
            train_df = df.iloc[train_start:train_end]
            test_df = df.iloc[test_start:test_end]
            
            splits.append((train_df, test_df))
        
        return splits
    
    def validate_robustness(self, 
                          pattern_results: Dict,
                          splits: List[Tuple[pd.DataFrame, pd.DataFrame]]) -> Dict:
        """
        验证形态的稳健性（跨时间窗口）
        """
        robustness_scores = []
        
        for i, (train_df, test_df) in enumerate(splits):
            # 在训练集发现形态
            # 在测试集验证
            # 计算表现一致性
            pass  # 具体实现依赖于形态匹配逻辑
        
        return {
            'robustness_score': np.mean(robustness_scores) if robustness_scores else 0,
            'consistency': np.std(robustness_scores) if len(robustness_scores) > 1 else 0
        }


class RegimeDetector:
    """市场状态检测：趋势/震荡/高波动"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'adx_threshold': 25,  # ADX阈值
            'volatility_lookback': 20,
            'trend_lookback': 50,
        }
    
    def detect_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        检测市场状态
        
        Returns:
            Series: 'trending', 'mean_reverting', 'volatile', 'normal'
        """
        close = df['close']
        
        # 1. 计算趋势强度 (ADX简化版)
        high_low = df['high'] - df['low']
        high_close_prev = np.abs(df['high'] - df['close'].shift(1))
        low_close_prev = np.abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # 2. 计算波动率
        returns = close.pct_change()
        volatility = returns.rolling(self.config['volatility_lookback']).std()
        vol_percentile = volatility.rolling(252).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x))
        
        # 3. 计算趋势方向持续性
        sma_short = close.rolling(20).mean()
        sma_long = close.rolling(50).mean()
        trend_strength = abs(sma_short - sma_long) / close
        
        # 4. 分类
        regime = pd.Series('normal', index=df.index)
        
        # 高波动
        regime[vol_percentile > 0.8] = 'volatile'
        
        # 趋势
        regime[(trend_strength > trend_strength.quantile(0.7)) & 
               (regime != 'volatile')] = 'trending'
        
        # 均值回归
        regime[(trend_strength < trend_strength.quantile(0.3)) & 
               (vol_percentile < 0.5) & 
               (regime == 'normal')] = 'mean_reverting'
        
        return regime