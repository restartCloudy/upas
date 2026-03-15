"""
UPAS - 通用抽象形态系统
形态发现引擎 - 修正版
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.cluster import DBSCAN, KMeans
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PatternDiscoveryEngine:
    """
    形态发现引擎
    
    使用改进的聚类机制：
    - L1-L2: DTW + 层次聚类（支持变长序列）
    - L3: 时序特征 + DBSCAN聚类
    - L4: 极值点模式 + HMM状态解码
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'min_pattern_freq': 3,       # 最小出现频率
            'similarity_threshold': 0.70, # 相似度阈值（降低以匹配更多）
            'max_clusters': 10,          # 最大聚类数
            'dtw_radius': 3              # DTW搜索半径
        }
        self.pattern_library = {}
    
    def discover_patterns(self, 
                         price_series: List[np.ndarray],
                         complexity_level: int = 3) -> Dict:
        """
        自动发现形态
        
        Args:
            price_series: 价格序列列表（已归一化）
            complexity_level: 目标复杂度级别 (1-4)
            
        Returns:
            形态库字典
        """
        logger.info(f"开始发现形态 (Level {complexity_level})...")
        
        # 过滤有效序列
        valid_series = [s for s in price_series if len(s) >= 5]
        
        if len(valid_series) < self.config['min_pattern_freq']:
            logger.warning(f"有效序列数量不足: {len(valid_series)}")
            return {}
        
        if complexity_level <= 2:
            patterns = self._discover_simple_patterns(valid_series)
        elif complexity_level == 3:
            patterns = self._discover_composite_patterns(valid_series)
        else:
            patterns = self._discover_complex_patterns(valid_series)
        
        logger.info(f"发现 {len(patterns)} 个形态")
        return patterns
    
    def _discover_simple_patterns(self, series: List[np.ndarray]) -> Dict:
        """
        L2: 简单形态发现（4-8根K线）
        使用DTW距离矩阵 + 层次聚类，支持变长序列
        """
        
        patterns = {}
        
        # 过滤长度在4-8之间的序列
        valid_series = []
        valid_indices = []
        for i, s in enumerate(series):
            if 4 <= len(s) <= 8:
                valid_series.append(s)
                valid_indices.append(i)
        
        if len(valid_series) < self.config['min_pattern_freq']:
            return {}
        
        # 计算DTW距离矩阵
        n = len(valid_series)
        distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                try:
                    from fastdtw import fastdtw
                    distance, _ = fastdtw(valid_series[i], valid_series[j])
                    distance_matrix[i, j] = distance
                    distance_matrix[j, i] = distance
                except ImportError:
                    # 如果没有fastdtw，使用简单的欧氏距离
                    min_len = min(len(valid_series[i]), len(valid_series[j]))
                    s1 = np.interp(np.linspace(0, 1, min_len), 
                                   np.linspace(0, 1, len(valid_series[i])), 
                                   valid_series[i])
                    s2 = np.interp(np.linspace(0, 1, min_len), 
                                   np.linspace(0, 1, len(valid_series[j])), 
                                   valid_series[j])
                    distance = np.sqrt(np.sum((s1 - s2) ** 2))
                    distance_matrix[i, j] = distance
                    distance_matrix[j, i] = distance
        
        # 使用层次聚类
        from scipy.cluster.hierarchy import linkage, fcluster
        from scipy.spatial.distance import squareform
        
        # 将距离矩阵转换为condensed形式
        condensed_dist = squareform(distance_matrix)
        Z = linkage(condensed_dist, method='average')
        
        # 确定聚类数
        max_clusters = min(self.config['max_clusters'], len(valid_series) // self.config['min_pattern_freq'])
        
        if max_clusters < 2:
            return {}
        
        # 切分聚类
        labels = fcluster(Z, t=max_clusters, criterion='maxclust')
        
        # 构建形态库
        for label in range(1, max_clusters + 1):
            cluster_mask = labels == label
            cluster_indices = [valid_indices[i] for i in range(len(valid_indices)) if cluster_mask[i]]
            
            if len(cluster_indices) >= self.config['min_pattern_freq']:
                pattern_id = f"L2-{label:03d}"
                
                # 计算原型：DTW重心
                cluster_series = [series[i] for i in cluster_indices]
                prototype = self._compute_dtw_barycenter(cluster_series)
                
                patterns[pattern_id] = {
                    'prototype': prototype,
                    'frequency': len(cluster_indices),
                    'sample_indices': cluster_indices,
                    'complexity': 2,
                    'avg_length': int(np.mean([len(s) for s in cluster_series])),
                    'length_std': float(np.std([len(s) for s in cluster_series])),
                    'creation_time': pd.Timestamp.now().isoformat()
                }
        
        return patterns
    
    def _discover_composite_patterns(self, series: List[np.ndarray]) -> Dict:
        """
        L3: 复合形态发现（使用K-Means聚类）
        输入是特征向量（而非原始价格序列），直接使用进行聚类
        """
        
        patterns = {}
        
        # 直接使用特征向量进行聚类
        if len(series) < self.config['min_pattern_freq']:
            return {}
        
        X = np.array(series)
        
        # 标准化特征
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 确定聚类数
        n_clusters = min(
            self.config['max_clusters'],
            max(2, len(X) // self.config['min_pattern_freq'])
        )
        
        if n_clusters < 2:
            return {}
        
        # K-Means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        # 构建形态库
        for label in range(n_clusters):
            cluster_indices = [i for i in range(len(series)) if labels[i] == label]
            
            if len(cluster_indices) >= self.config['min_pattern_freq']:
                pattern_id = f"L3-{label:03d}"
                
                # 计算原型（聚类中心）
                prototype = kmeans.cluster_centers_[label]
                
                patterns[pattern_id] = {
                    'prototype': prototype,
                    'frequency': len(cluster_indices),
                    'sample_indices': cluster_indices,
                    'complexity': 3,
                    'creation_time': pd.Timestamp.now().isoformat()
                }
        
        return patterns
    
    def _extract_temporal_features(self, series: np.ndarray) -> np.ndarray:
        """提取时序特征（保留时序结构信息）"""
        
        # 标准化序列
        s = (series - np.mean(series)) / (np.std(series) + 1e-10)
        
        features = []
        
        # 1. 形状统计（标准化后）
        features.extend([
            0.0,  # 均值（标准化后为0）
            1.0,  # 标准差（标准化后为1）
            float(np.max(s)),
            float(np.min(s)),
        ])
        
        # 2. 子序列特征（Shapelet候选）
        for window in [5, 10]:
            if len(s) >= window:
                for i in range(0, len(s) - window + 1, max(1, window // 2)):
                    sub = s[i:i+window]
                    features.extend([
                        float(np.mean(sub)),
                        float(np.std(sub) + 1e-10),
                        float(sub[-1] - sub[0]),  # 变化趋势
                    ])
        
        # 3. 频域特征（FFT简化）
        if len(s) >= 8:
            fft = np.abs(np.fft.fft(s))[:len(s)//2]
            features.extend([
                float(fft[0]),  # DC分量
                float(np.mean(fft[1:4])),  # 低频
                float(np.mean(fft[4:])),  # 高频
            ])
        
        # 4. 转折点特征
        peaks, valleys = self._find_extrema(s)
        features.extend([
            float(len(peaks)),
            float(len(valleys)),
            float(len(peaks) + len(valleys)),
        ])
        
        return np.array(features, dtype=np.float32)
    
    def _compute_dtw_barycenter(self, series_list: List[np.ndarray]) -> np.ndarray:
        """计算DTW重心（简化版：取中位数长度的序列，然后平均）"""
        
        if not series_list:
            return np.array([])
        
        # 找到中位数长度的序列
        lengths = [len(s) for s in series_list]
        median_len = int(np.median(lengths))
        
        # 将所有序列重采样到相同长度
        resampled = []
        for s in series_list:
            if len(s) == median_len:
                resampled.append(s)
            else:
                # 线性插值
                indices = np.linspace(0, len(s) - 1, median_len)
                interpolated = np.interp(indices, np.arange(len(s)), s)
                resampled.append(interpolated)
        
        # 计算平均值作为原型
        prototype = np.mean(resampled, axis=0)
        
        return prototype
    
    def _discover_complex_patterns(self, series: List[np.ndarray]) -> Dict:
        """L4: 复杂形态发现（基于极值点模式 + HMM状态解码）"""
        
        patterns = {}
        pattern_counter = 0
        
        for i, s in enumerate(series):
            if len(s) < 30:  # L4需要至少30根K线
                continue
            
            # 提取极值点模式
            peaks, valleys = self._find_extrema(s)
            
            if len(peaks) >= 2 and len(valleys) >= 2:
                # 构建模式特征
                pattern_features = {
                    'n_peaks': len(peaks),
                    'n_valleys': len(valleys),
                    'peak_valley_ratio': len(peaks) / len(valleys) if len(valleys) > 0 else 0,
                    'total_variation': np.sum(np.abs(np.diff(s))),
                    'trend_direction': 1 if s[-1] > s[0] else -1
                }
                
                pattern_id = f"L4-{pattern_counter:04d}"
                patterns[pattern_id] = {
                    'prototype': s,
                    'features': pattern_features,
                    'peaks': peaks,
                    'valleys': valleys,
                    'frequency': 1,
                    'complexity': 4,
                    'creation_time': pd.Timestamp.now().isoformat()
                }
                
                pattern_counter += 1
        
        # 对L4形态进行二次聚类
        if len(patterns) >= self.config['min_pattern_freq']:
            patterns = self._cluster_complex_patterns(patterns)
        
        return patterns
    
    def _find_extrema(self, series: np.ndarray, order: int = 2) -> Tuple[List[int], List[int]]:
        """查找极值点"""
        from scipy.signal import argrelextrema
        
        try:
            peaks = argrelextrema(series, np.greater, order=order)[0].tolist()
            valleys = argrelextrema(series, np.less, order=order)[0].tolist()
        except:
            # 如果scipy不可用，使用简单方法
            peaks = []
            valleys = []
            for i in range(1, len(series) - 1):
                if series[i] > series[i-1] and series[i] > series[i+1]:
                    peaks.append(i)
                elif series[i] < series[i-1] and series[i] < series[i+1]:
                    valleys.append(i)
        
        return peaks, valleys
    
    def _cluster_complex_patterns(self, patterns: Dict) -> Dict:
        """对复杂形态进行二次聚类"""
        
        pattern_ids = list(patterns.keys())
        features = []
        
        for pid in pattern_ids:
            feat = patterns[pid].get('features', {})
            features.append([
                feat.get('n_peaks', 0),
                feat.get('n_valleys', 0),
                feat.get('total_variation', 0),
                feat.get('trend_direction', 0)
            ])
        
        if len(features) < self.config['min_pattern_freq']:
            return patterns
        
        X = np.array(features)
        
        # K-Means聚类
        n_clusters = min(10, len(X) // self.config['min_pattern_freq'])
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        # 合并同类形态
        clustered = {}
        for i in range(n_clusters):
            cluster_pids = [pattern_ids[j] for j in range(len(pattern_ids)) if labels[j] == i]
            
            if len(cluster_pids) >= self.config['min_pattern_freq']:
                pattern_id = f"L4-C{i:03d}"
                
                # 选择代表性形态（最接近聚类中心）
                center = kmeans.cluster_centers_[i]
                distances = [np.linalg.norm(X[pattern_ids.index(pid)] - center) 
                            for pid in cluster_pids]
                representative_idx = np.argmin(distances)
                representative_pid = cluster_pids[representative_idx]
                
                clustered[pattern_id] = patterns[representative_pid].copy()
                clustered[pattern_id]['cluster_size'] = len(cluster_pids)
                clustered[pattern_id]['members'] = cluster_pids
                clustered[pattern_id]['pattern_id'] = pattern_id
        
        return clustered if clustered else patterns
    
    def calculate_similarity(self, 
                           pattern1: np.ndarray, 
                           pattern2: np.ndarray,
                           method: str = 'dtw') -> float:
        """
        计算形态相似度
        
        Args:
            pattern1: 形态序列1
            pattern2: 形态序列2
            method: 'euclidean' | 'correlation' | 'dtw'
            
        Returns:
            相似度得分 (0-1)
        """
        # 标准化到相同长度
        min_len = min(len(pattern1), len(pattern2))
        if min_len == 0:
            return 0.0
        
        # 重采样到相同长度
        if len(pattern1) != len(pattern2):
            indices = np.linspace(0, len(pattern1) - 1, min_len)
            p1 = np.interp(indices, np.arange(len(pattern1)), pattern1)
            indices = np.linspace(0, len(pattern2) - 1, min_len)
            p2 = np.interp(indices, np.arange(len(pattern2)), pattern2)
        else:
            p1, p2 = pattern1, pattern2
        
        if method == 'euclidean':
            dist = np.linalg.norm(p1 - p2)
            max_dist = np.sqrt(min_len)
            return max(0, 1 - dist / max_dist)
        
        elif method == 'correlation':
            if np.std(p1) == 0 or np.std(p2) == 0:
                return 0.0
            corr = np.corrcoef(p1, p2)[0, 1]
            return (corr + 1) / 2
        
        elif method == 'dtw':
            try:
                from fastdtw import fastdtw
                distance, _ = fastdtw(p1, p2, radius=self.config['dtw_radius'])
                # 归一化距离
                max_dist = np.sqrt(min_len) * 2  # 近似最大距离
                similarity = max(0, 1 - distance / (max_dist + 1e-10))
                return similarity
            except ImportError:
                logger.warning("fastdtw not available, using euclidean")
                return self.calculate_similarity(pattern1, pattern2, 'euclidean')
        
        else:
            raise ValueError(f"Unknown similarity method: {method}")