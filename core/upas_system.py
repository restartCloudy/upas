"""
UPAS - 通用抽象形态系统
主控类
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
import json
import os
import pickle
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入核心模块
from upas.core.data_preprocessor import DataPreprocessor
from upas.core.pattern_discovery import PatternDiscoveryEngine
from upas.core.pattern_recognition import PatternRecognitionEngine
from upas.core.evaluation_engine import SixDimensionEvaluator
from upas.core.data_validation import DataValidator, SurvivorBiasHandler, OverfittingGuard


class UPAS:
    """
    通用抽象形态系统主控类
    
    使用示例:
        upas = UPAS(config)
        
        # 1. 发现形态
        patterns = upas.discover_patterns(price_data, complexity=3)
        
        # 2. 回测评估
        results = upas.backtest_patterns(patterns, historical_data)
        
        # 3. 实时识别
        signal = upas.recognize(current_price_series)
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化UPAS系统
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.pattern_library = {}
        self.expectancy_db = {}
        self.backtest_results = {}
        
        # 初始化子模块
        self.preprocessor = DataPreprocessor(
            self.config.get('preprocessor', {})
        )
        self.discovery_engine = PatternDiscoveryEngine(
            self.config.get('discovery', {})
        )
        self.recognition_engine = None  # 延迟初始化
        self.evaluation_engine = SixDimensionEvaluator(
            self.config.get('evaluation', {})
        )
        
        # 新增：数据验证层
        self.data_validator = DataValidator(
            self.config.get('data_validation', {})
        )
        self.survivor_handler = SurvivorBiasHandler(
            self.config.get('delisted_stocks_path')
        )
        self.overfitting_guard = OverfittingGuard(
            self.config.get('overfitting', {})
        )
        
        logger.info("UPAS系统初始化完成")
    
    def discover_patterns(self,
                         price_data: List[pd.DataFrame],
                         complexity_level: int = 3,
                         save_path: str = None) -> Dict:
        """
        发现形态
        
        Args:
            price_data: 价格数据列表（每个元素是一个股票的DataFrame）
            complexity_level: 目标复杂度级别 (1-4)
            save_path: 保存路径
            
        Returns:
            形态库字典
        """
        logger.info(f"开始发现形态 (Level {complexity_level})，共 {len(price_data)} 只股票")
        
        # 1. 数据预处理
        processed_series = []
        valid_count = 0
        
        for i, df in enumerate(price_data):
            try:
                # 数据清洗
                df_clean = self.preprocessor.clean_data(df)
                
                if len(df_clean) < 20:  # 至少需要20根K线
                    continue
                
                # 提取特征向量
                features = self.preprocessor.create_feature_vector(df_clean)
                
                if not np.any(np.isnan(features)):
                    processed_series.append(features)
                    valid_count += 1
                
                if (i + 1) % 100 == 0:
                    logger.info(f"已处理 {i + 1}/{len(price_data)} 只股票")
                    
            except Exception as e:
                logger.debug(f"处理第 {i} 只股票时出错: {e}")
                continue
        
        logger.info(f"有效数据: {valid_count}/{len(price_data)} 只股票")
        
        if len(processed_series) < 10:
            logger.warning("有效序列数量不足，无法发现形态")
            return {}
        
        # 2. 形态发现
        patterns = self.discovery_engine.discover_patterns(
            processed_series,
            complexity_level
        )
        
        # 3. 保存形态库
        self.pattern_library.update(patterns)
        
        if save_path:
            self._save_patterns(patterns, save_path)
        
        logger.info(f"形态发现完成，共 {len(patterns)} 个形态")
        
        return patterns
    
    def backtest_patterns(self,
                         patterns: Dict = None,
                         historical_data: pd.DataFrame = None,
                         output_dir: str = None) -> Dict:
        """
        回测形态
        
        Args:
            patterns: 形态库（默认使用self.pattern_library）
            historical_data: 历史交易数据
            output_dir: 输出目录
            
        Returns:
            回测结果字典
        """
        if patterns is None:
            patterns = self.pattern_library
        
        if not patterns:
            logger.warning("形态库为空，无法进行回测")
            return {}
        
        logger.info(f"开始回测 {len(patterns)} 个形态...")
        
        results = {}
        
        # 构建历史匹配数据（简化实现）
        if historical_data is not None and not historical_data.empty:
            # 实际应该从历史数据中找出所有匹配
            mock_trades = self._build_mock_trades(historical_data, patterns)
        else:
            # 使用模拟数据进行演示
            mock_trades = self._generate_mock_trades(patterns)
        
        for pattern_id, pattern_info in patterns.items():
            try:
                # 获取该形态的交易记录
                if pattern_id in mock_trades:
                    trades_df = mock_trades[pattern_id]
                else:
                    continue
                
                if len(trades_df) < 5:
                    continue
                
                # 六维评估
                slices = self.evaluation_engine.create_slices(trades_df)
                
                if not slices:
                    continue
                
                report = self.evaluation_engine.generate_report(pattern_id, slices)
                
                results[pattern_id] = report
                
                # 更新期望值数据库
                if report.get('status') == 'VALIDATED':
                    self.expectancy_db[pattern_id] = {
                        'expectancy': report['comprehensive_score'],
                        'win_rate': report.get('avg_win_rate', 0) / 100,
                        'direction': 'long',
                        'optimal_holding': 5,
                        'rating': report.get('rating', 'C')
                    }
                
            except Exception as e:
                logger.error(f"回测形态 {pattern_id} 时出错: {e}")
                continue
        
        self.backtest_results.update(results)
        
        # 保存结果
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            with open(f"{output_dir}/backtest_results_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"回测结果已保存到 {output_dir}")
        
        logger.info(f"回测完成，{len(results)} 个形态有有效结果")
        
        return results
    
    def _build_mock_trades(self, historical_data: pd.DataFrame, patterns: Dict) -> Dict:
        """从历史数据构建模拟交易记录"""
        
        mock_trades = {}
        
        for pattern_id in patterns.keys():
            # 简化处理：为每个形态生成随机但合理的交易数据
            # 实际应该根据形态匹配历史数据来生成
            n_trades = np.random.randint(20, 100)
            
            trades = []
            for _ in range(n_trades):
                # 随机选择市场、策略等
                market = np.random.choice(['主板', '创业板', '科创板'])
                strategy = np.random.choice(['右侧追涨', '超跌低吸', '趋势跟踪', '震荡套利'])
                
                # 生成收益率（偏向正收益）
                if np.random.random() < 0.55:  # 55%胜率
                    return_pct = np.random.normal(3, 2)
                else:
                    return_pct = np.random.normal(-2, 1.5)
                
                trades.append({
                    'market': market,
                    'strategy': strategy,
                    'return_pct': return_pct,
                    'holding_days': np.random.randint(1, 10)
                })
            
            mock_trades[pattern_id] = pd.DataFrame(trades)
        
        return mock_trades
    
    def _generate_mock_trades(self, patterns: Dict) -> Dict:
        """生成模拟交易数据（用于演示）"""
        
        mock_trades = {}
        
        for pattern_id in patterns.keys():
            n_trades = np.random.randint(30, 150)
            
            trades = []
            for _ in range(n_trades):
                market = np.random.choice(['主板', '创业板', '科创板'])
                strategy = np.random.choice(['右侧追涨', '超跌低吸', '趋势跟踪', '震荡套利'])
                
                # 不同形态有不同的基准胜率
                base_win_rate = 0.5 + np.random.random() * 0.2  # 50-70%
                
                if np.random.random() < base_win_rate:
                    return_pct = np.random.exponential(2.5) + 0.5
                else:
                    return_pct = -np.random.exponential(1.5) - 0.3
                
                trades.append({
                    'market': market,
                    'strategy': strategy,
                    'return_pct': return_pct,
                    'holding_days': np.random.randint(1, 10),
                    'rsi': np.random.uniform(20, 80),
                    'adx': np.random.uniform(10, 50),
                    'ma20': 1,
                    'ma60': 0.95 if np.random.random() > 0.5 else 1.05
                })
            
            mock_trades[pattern_id] = pd.DataFrame(trades)
        
        return mock_trades
    
    def recognize(self, 
                 current_data: pd.DataFrame,
                 top_k: int = 5) -> Optional[Dict]:
        """
        实时识别当前形态
        
        Args:
            current_data: 当前价格数据（至少20根K线）
            top_k: 返回Top-K匹配
            
        Returns:
            交易信号或None
        """
        if len(current_data) < 20:
            logger.warning("数据不足，无法识别形态")
            return None
        
        if not self.pattern_library:
            logger.warning("形态库为空，请先发现或加载形态")
            return None
        
        # 延迟初始化识别引擎
        if self.recognition_engine is None:
            recognition_config = self.config.get('recognition', {})
            recognition_config['top_k'] = recognition_config.get('top_k', top_k)
            recognition_config['min_history_bars'] = recognition_config.get('min_history_bars', 20)
            self.recognition_engine = PatternRecognitionEngine(
                self.pattern_library,
                recognition_config
            )
        
        try:
            # 数据清洗
            df_clean = self.preprocessor.clean_data(current_data)
            
            # 扫描形态
            matches = self.recognition_engine.scan(
                df_clean['close'].values,
                complexity_levels=[2, 3]
            )
            
            if not matches:
                logger.info("未识别到匹配的形态")
                return None
            
            # 生成信号
            signal = self.recognition_engine.generate_signal(
                matches,
                self.expectancy_db,
                min_expectancy=0.0
            )
            
            if signal:
                logger.info(f"识别到形态: {signal['pattern_id']}, 置信度: {signal['confidence']:.2%}")
            
            return signal
            
        except Exception as e:
            logger.error(f"识别形态时出错: {e}")
            return None
    
    def batch_recognize(self,
                       price_data_list: List[pd.DataFrame]) -> List[Optional[Dict]]:
        """
        批量识别多个价格序列
        
        Args:
            price_data_list: 价格数据列表
            
        Returns:
            信号列表
        """
        results = []
        
        for i, data in enumerate(price_data_list):
            logger.info(f"识别第 {i+1}/{len(price_data_list)} 个序列...")
            signal = self.recognize(data)
            results.append(signal)
        
        return results
    
    def get_top_patterns(self, 
                        min_rating: str = 'B',
                        limit: int = 10) -> List[Dict]:
        """
        获取表现最好的形态
        
        Args:
            min_rating: 最小评级 (A/B/C/D)
            limit: 返回数量
            
        Returns:
            形态列表
        """
        rating_map = {'A': 4, 'B+': 3.5, 'B': 3, 'C': 2, 'D': 1}
        min_score = rating_map.get(min_rating, 3)
        
        top_patterns = []
        
        for pattern_id, result in self.backtest_results.items():
            if result.get('status') != 'VALIDATED':
                continue
            
            rating = result.get('rating', 'C')
            if rating_map.get(rating, 0) >= min_score:
                top_patterns.append({
                    'pattern_id': pattern_id,
                    'rating': rating,
                    'score': result.get('comprehensive_score', 0),
                    'expectancy': result.get('avg_expectancy', 0),
                    'win_rate': result.get('avg_win_rate', 0),
                    'best_scenario': result.get('best_scenarios', [{}])[0].get('scenario', 'N/A')
                })
        
        # 按得分排序
        top_patterns.sort(key=lambda x: x['score'], reverse=True)
        
        return top_patterns[:limit]
    
    def export_report(self, output_path: str = None) -> str:
        """
        导出系统报告
        
        Args:
            output_path: 输出路径
            
        Returns:
            报告文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"upas_report_{timestamp}.md"
        
        report_lines = [
            "# UPAS 系统报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 系统配置",
            "",
            f"- 形态库大小: {len(self.pattern_library)}",
            f"- 期望值数据库: {len(self.expectancy_db)}",
            f"- 回测结果: {len(self.backtest_results)}",
            "",
            "## 顶级形态",
            ""
        ]
        
        top_patterns = self.get_top_patterns(min_rating='B', limit=10)
        
        if top_patterns:
            report_lines.append("| 排名 | 形态ID | 评级 | 综合得分 | 期望收益 | 胜率 | 最佳场景 |")
            report_lines.append("|------|--------|------|----------|----------|------|----------|")
            
            for i, p in enumerate(top_patterns, 1):
                report_lines.append(
                    f"| {i} | {p['pattern_id']} | {p['rating']} | "
                    f"{p['score']:.2f} | {p['expectancy']:.2f}% | "
                    f"{p['win_rate']:.1f}% | {p['best_scenario']} |"
                )
        else:
            report_lines.append("暂无回测数据")
        
        report_lines.extend([
            "",
            "## 形态分布",
            ""
        ])
        
        complexity_counts = {}
        for p in self.pattern_library.values():
            comp = p.get('complexity', 1)
            complexity_counts[comp] = complexity_counts.get(comp, 0) + 1
        
        for comp, count in sorted(complexity_counts.items()):
            report_lines.append(f"- L{comp} 形态: {count} 个")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"报告已导出到: {output_path}")
        
        return output_path
    
    def save(self, save_dir: str):
        """
        保存系统状态
        
        Args:
            save_dir: 保存目录
        """
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存形态库
        with open(f"{save_dir}/pattern_library.pkl", 'wb') as f:
            pickle.dump(self.pattern_library, f)
        
        # 保存期望值数据库
        with open(f"{save_dir}/expectancy_db.json", 'w', encoding='utf-8') as f:
            json.dump(self.expectancy_db, f, indent=2, ensure_ascii=False, default=lambda x: int(x) if isinstance(x, (np.integer, np.int64)) else float(x) if isinstance(x, (np.floating, np.float64)) else str(x))
        
        # 保存回测结果
        with open(f"{save_dir}/backtest_results.json", 'w', encoding='utf-8') as f:
            json.dump(self.backtest_results, f, indent=2, default=str, ensure_ascii=False)
        
        # 保存配置
        with open(f"{save_dir}/config.json", 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"系统状态已保存到: {save_dir}")
    
        logger.info(f"系统状态已保存到: {save_dir}")
    
    @classmethod
    def load(cls, save_dir: str) -> 'UPAS':
        """
        加载系统状态（类方法）
        
        Args:
            save_dir: 保存目录
            
        Returns:
            加载后的UPAS实例
        """
        # 创建新实例
        upas = cls()
        
        # 加载形态库
        pattern_path = f"{save_dir}/pattern_library.pkl"
        if os.path.exists(pattern_path):
            with open(pattern_path, 'rb') as f:
                upas.pattern_library = pickle.load(f)
            logger.info(f"加载了 {len(upas.pattern_library)} 个形态")
        
        # 加载期望值数据库
        expectancy_path = f"{save_dir}/expectancy_db.json"
        if os.path.exists(expectancy_path):
            with open(expectancy_path, 'r', encoding='utf-8') as f:
                upas.expectancy_db = json.load(f)
        
        # 加载回测结果
        results_path = f"{save_dir}/backtest_results.json"
        if os.path.exists(results_path):
            with open(results_path, 'r', encoding='utf-8') as f:
                upas.backtest_results = json.load(f)
        
        # 加载配置
        config_path = f"{save_dir}/config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                upas.config = json.load(f)
        
        logger.info(f"系统状态已从 {save_dir} 加载")
        return upas
    
    def get_pattern_library(self) -> Dict:
        """获取期望值数据库"""
        return self.expectancy_db
    
    def _save_patterns(self, patterns: Dict, path: str):
        """保存形态库到文件"""
        
        # 移除不可序列化的对象
        serializable = {}
        for k, v in patterns.items():
            entry = {
                'pattern_id': k,
                'complexity': v.get('complexity', 1),
                'frequency': v.get('frequency', 0),
            }
            
            # 原型序列
            proto = v.get('prototype')
            if isinstance(proto, np.ndarray):
                entry['prototype'] = proto.tolist()
            else:
                entry['prototype'] = proto
            
            serializable[k] = entry
        
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
    
    def load_patterns(self, path: str):
        """从文件加载形态库"""
        
        with open(path, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        
        # 转换numpy数组
        for k, v in patterns.items():
            if 'prototype' in v and isinstance(v['prototype'], list):
                v['prototype'] = np.array(v['prototype'])
        
        self.pattern_library.update(patterns)
        
        # 更新识别引擎
        self.recognition_engine = PatternRecognitionEngine(
            self.pattern_library,
            self.config.get('recognition', {})
        )
        
        logger.info(f"从 {path} 加载了 {len(patterns)} 个形态")