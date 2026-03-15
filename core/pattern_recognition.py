"""
UPAS - 通用抽象形态系统
形态识别引擎
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PatternRecognitionEngine:
    """
    形态识别引擎
    
    实时扫描价格序列，识别匹配的形态
    """
    
    def __init__(self, pattern_library: Dict, config: Dict = None):
        self.pattern_library = pattern_library
        self.config = config or {
            'similarity_threshold': 0.75,  # 相似度阈值
            'top_k': 5,                     # 返回Top-K匹配
            'min_history_bars': 20,         # 最小历史数据
            'scan_complexity': [1, 2, 3]    # 扫描的复杂度级别
        }
    
    def scan(self, 
             price_series: np.ndarray,
             complexity_levels: List[int] = None) -> List[Dict]:
        """
        扫描价格序列，识别形态
        
        Args:
            price_series: 当前价格序列
            complexity_levels: 要识别的复杂度级别
            
        Returns:
            匹配的形态列表（按相似度排序）
        """
        if complexity_levels is None:
            complexity_levels = self.config['scan_complexity']
        
        if len(price_series) < self.config['min_history_bars']:
            logger.warning(f"价格序列太短: {len(price_series)} < {self.config['min_history_bars']}")
            return []
        
        matches = []
        
        for level in complexity_levels:
            level_matches = self._scan_level(price_series, level)
            matches.extend(level_matches)
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return matches[:self.config['top_k']]
    
    def _scan_level(self, 
                   price_series: np.ndarray,
                   level: int) -> List[Dict]:
        """扫描指定复杂度级别的形态"""
        
        matches = []
        
        # 从形态库中筛选该级别的形态
        level_patterns = {
            k: v for k, v in self.pattern_library.items()
            if v.get('complexity', 1) == level
        }
        
        if not level_patterns:
            return []
        
        for pattern_id, pattern_info in level_patterns.items():
            # 获取原型
            prototype = pattern_info.get('prototype')
            if prototype is None or len(prototype) == 0:
                continue
            
            # 提取对应长度的序列
            window_size = len(prototype)
            if len(price_series) < window_size:
                continue
            
            # 取最后window_size根K线
            recent = price_series[-window_size:]
            
            # 归一化
            from upas.core.data_preprocessor import DataPreprocessor
            dp = DataPreprocessor()
            
            try:
                recent_norm = dp.normalize_prices(recent, 'structure')
                prototype_norm = dp.normalize_prices(prototype, 'structure')
                
                # 处理NaN
                if np.any(np.isnan(recent_norm)) or np.any(np.isnan(prototype_norm)):
                    continue
                
                # 计算相似度
                from upas.core.pattern_discovery import PatternDiscoveryEngine
                pde = PatternDiscoveryEngine()
                
                similarity = pde.calculate_similarity(
                    recent_norm, 
                    prototype_norm,
                    method='correlation' if level >= 3 else 'euclidean'
                )
                
                if similarity >= self.config['similarity_threshold']:
                    matches.append({
                        'pattern_id': pattern_id,
                        'similarity': float(similarity),
                        'complexity': level,
                        'frequency': pattern_info.get('frequency', 0),
                        'window_size': window_size,
                        'match_time': pd.Timestamp.now().isoformat()
                    })
            
            except Exception as e:
                logger.debug(f"匹配形态 {pattern_id} 时出错: {e}")
                continue
        
        return matches
    
    def generate_signal(self, 
                       matches: List[Dict],
                       pattern_expectancy: Dict,
                       min_expectancy: float = 0.0) -> Optional[Dict]:
        """
        基于形态匹配生成交易信号
        
        Args:
            matches: 匹配的形态列表
            pattern_expectancy: 形态期望值数据库
            min_expectancy: 最小期望收益阈值
            
        Returns:
            交易信号字典或None
        """
        if not matches:
            return None
        
        # 选择最佳匹配
        best_match = matches[0]
        pattern_id = best_match['pattern_id']
        
        # 查询期望值
        if pattern_id not in pattern_expectancy:
            logger.debug(f"形态 {pattern_id} 不在期望值数据库中")
            return None
        
        expectancy = pattern_expectancy[pattern_id]
        
        # 期望值阈值检查
        exp_value = expectancy.get('expectancy', 0)
        if exp_value < min_expectancy:
            logger.debug(f"形态 {pattern_id} 期望收益 {exp_value:.2f} 低于阈值 {min_expectancy}")
            return None
        
        # 生成信号
        signal = {
            'pattern_id': pattern_id,
            'confidence': best_match['similarity'],
            'direction': expectancy.get('direction', 'unknown'),
            'expected_return': exp_value,
            'win_rate': expectancy.get('win_rate', 0),
            'risk_reward': expectancy.get('risk_reward', 1.0),
            'optimal_holding': expectancy.get('optimal_holding', 5),
            'complexity': best_match['complexity'],
            'frequency': best_match['frequency'],
            'secondary_matches': [
                {
                    'pattern_id': m['pattern_id'],
                    'confidence': m['similarity']
                }
                for m in matches[1:3]  # 次级匹配
            ],
            'generated_at': pd.Timestamp.now().isoformat()
        }
        
        return signal
    
    def scan_multi_window(self,
                         price_series: np.ndarray,
                         window_sizes: List[int] = None) -> Dict[int, List[Dict]]:
        """
        多窗口扫描
        
        在不同时间窗口上扫描形态，用于识别跨尺度的形态
        
        Args:
            price_series: 价格序列
            window_sizes: 窗口大小列表
            
        Returns:
            按窗口大小分组的匹配结果
        """
        if window_sizes is None:
            # 默认窗口：短、中、长
            window_sizes = [10, 20, 40]
        
        results = {}
        
        for size in window_sizes:
            if len(price_series) < size:
                continue
            
            # 过滤匹配该窗口大小的形态
            window_patterns = {
                k: v for k, v in self.pattern_library.items()
                if abs(len(v.get('prototype', [])) - size) <= 5  # 允许5个单位的误差
            }
            
            if not window_patterns:
                continue
            
            # 临时替换形态库
            original_library = self.pattern_library
            self.pattern_library = window_patterns
            
            # 扫描
            matches = self.scan(price_series, complexity_levels=[2, 3])
            results[size] = matches
            
            # 恢复形态库
            self.pattern_library = original_library
        
        return results
    
    def calculate_match_strength(self, matches: List[Dict]) -> float:
        """
        计算匹配强度综合得分
        
        考虑：
        - 最高相似度
        - 匹配数量
        - 匹配形态的复杂度分布
        """
        if not matches:
            return 0.0
        
        # 最高相似度权重 0.5
        max_similarity = max(m['similarity'] for m in matches)
        
        # 匹配数量权重 0.3
        count_score = min(len(matches) / 5, 1.0)  # 最多5个匹配得满分
        
        # 复杂度权重 0.2
        complexity_bonus = 0.0
        for m in matches:
            if m['complexity'] >= 3:
                complexity_bonus = 0.2
                break
        
        return max_similarity * 0.5 + count_score * 0.3 + complexity_bonus
    
    def filter_by_expectancy(self,
                            matches: List[Dict],
                            pattern_expectancy: Dict,
                            min_win_rate: float = 0.5,
                            min_expectancy: float = 0.0) -> List[Dict]:
        """
        根据期望值过滤匹配结果
        
        Args:
            matches: 匹配列表
            pattern_expectancy: 期望值数据库
            min_win_rate: 最小胜率
            min_expectancy: 最小期望收益
            
        Returns:
            过滤后的匹配列表
        """
        filtered = []
        
        for match in matches:
            pattern_id = match['pattern_id']
            if pattern_id not in pattern_expectancy:
                continue
            
            exp = pattern_expectancy[pattern_id]
            
            if (exp.get('win_rate', 0) >= min_win_rate and 
                exp.get('expectancy', 0) >= min_expectancy):
                filtered.append(match)
        
        return filtered