"""
UPAS - 通用抽象形态系统
数据预处理模块
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """数据预处理：清洗、归一化、特征提取"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'zigzag_threshold': 0.05,      # 5% ZigZag阈值
            'atr_period': 14,               # ATR计算周期
            'normalize_method': 'relative'  # 归一化方法
        }
    
    def extract_zigzag(self, df: pd.DataFrame, threshold: float = None) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        ZigZag极值点提取
        
        Args:
            df: 包含OHLCV的DataFrame
            threshold: 转折阈值（默认5%）
            
        Returns:
            (带zigzag标记的DataFrame, 极值点列表)
        """
        threshold = threshold or self.config['zigzag_threshold']
        
        highs = df['high'].values
        lows = df['low'].values
        n = len(df)
        
        if n < 2:
            df['zigzag'] = 0
            return df, []
        
        # ZigZag算法实现
        zigzag = np.zeros(n)
        pivot_points = []
        
        last_pivot_price = highs[0]
        last_pivot_idx = 0
        trend = 1  # 1=上升, -1=下降
        
        for i in range(1, n):
            if trend == 1:
                # 上升趋势中寻找高点
                if highs[i] > last_pivot_price:
                    last_pivot_price = highs[i]
                    last_pivot_idx = i
                elif lows[i] < last_pivot_price * (1 - threshold):
                    # 转折确认
                    pivot_points.append({
                        'idx': last_pivot_idx,
                        'price': last_pivot_price,
                        'type': 'peak',
                        'date': df.index[last_pivot_idx] if hasattr(df.index, '__getitem__') else last_pivot_idx
                    })
                    zigzag[last_pivot_idx] = 1
                    trend = -1
                    last_pivot_price = lows[i]
                    last_pivot_idx = i
            else:
                # 下降趋势中寻找低点
                if lows[i] < last_pivot_price:
                    last_pivot_price = lows[i]
                    last_pivot_idx = i
                elif highs[i] > last_pivot_price * (1 + threshold):
                    # 转折确认
                    pivot_points.append({
                        'idx': last_pivot_idx,
                        'price': last_pivot_price,
                        'type': 'valley',
                        'date': df.index[last_pivot_idx] if hasattr(df.index, '__getitem__') else last_pivot_idx
                    })
                    zigzag[last_pivot_idx] = -1
                    trend = 1
                    last_pivot_price = highs[i]
                    last_pivot_idx = i
        
        # 循环结束后，记录最后一个极值点
        if len(df) > 1:
            pivot_points.append({
                'idx': last_pivot_idx,
                'price': last_pivot_price,
                'type': 'peak' if trend == 1 else 'valley',
                'date': df.index[last_pivot_idx] if hasattr(df.index, '__getitem__') else last_pivot_idx
            })
            zigzag[last_pivot_idx] = 1 if trend == 1 else -1
        
        df['zigzag'] = zigzag
        return df, pivot_points
    
    def normalize_prices(self, prices: np.ndarray, method: str = None) -> np.ndarray:
        """
        价格归一化
        
        Methods:
            - 'relative': 对数收益率
            - 'structure': 几何结构归一化(0-1)
            - 'zscore': Z-score标准化
        """
        method = method or self.config['normalize_method']
        prices = np.array(prices)
        
        if len(prices) == 0:
            return prices
        
        if method == 'relative':
            # 对数收益率
            log_prices = np.log(prices + 1e-10)
            return np.diff(log_prices)
        
        elif method == 'structure':
            # 几何结构归一化
            min_p, max_p = np.min(prices), np.max(prices)
            if max_p == min_p:
                return np.zeros_like(prices, dtype=float)
            return (prices - min_p) / (max_p - min_p)
        
        elif method == 'zscore':
            # Z-score标准化
            mean = np.mean(prices)
            std = np.std(prices)
            if std == 0:
                return np.zeros_like(prices, dtype=float)
            return (prices - mean) / std
        
        else:
            raise ValueError(f"Unknown normalization method: {method}")
    
    def calculate_atr(self, df: pd.DataFrame, period: int = None) -> pd.Series:
        """计算ATR（真实波幅）- 修复版：包含三个要素"""
        period = period or self.config['atr_period']
        
        # 真实波幅 = max(high-low, |high-previous_close|, |low-previous_close|)
        high_low = df['high'] - df['low']
        high_close_prev = np.abs(df['high'] - df['close'].shift(1))
        low_close_prev = np.abs(df['low'] - df['close'].shift(1))
        
        # 取三者最大值
        tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # 使用Wilder平滑（RMA）
        atr = tr.ewm(alpha=1/period, min_periods=period).mean()
        
        return atr
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def calculate_bollinger(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        return upper, middle, lower
    
    def create_feature_vector(self, df: pd.DataFrame, window: int = 20) -> np.ndarray:
        """
        创建特征向量
        
        Returns:
            特征向量数组
        """
        if len(df) < window:
            window = len(df)
        
        features = []
        
        # 1. 归一化价格
        try:
            normalized = self.normalize_prices(df['close'].values[-window:], 'structure')
            if len(normalized) < window:
                normalized = np.pad(normalized, (0, window - len(normalized)), mode='edge')
            features.extend(normalized.tolist()[:window])
        except:
            features.extend([0.5] * window)
        
        # 2. 收益率特征
        try:
            returns = df['close'].pct_change().values[-window:]
            returns_clean = returns[~np.isnan(returns)]
            if len(returns_clean) > 0:
                features.extend([
                    float(np.nanmean(returns)),
                    float(np.nanstd(returns)) if not np.isnan(np.nanstd(returns)) else 0,
                    float(np.nanmax(returns)),
                    float(np.nanmin(returns)),
                    float(np.nanpercentile(returns, 75)) if len(returns_clean) > 3 else 0,
                    float(np.nanpercentile(returns, 25)) if len(returns_clean) > 3 else 0
                ])
            else:
                features.extend([0, 0, 0, 0, 0, 0])
        except:
            features.extend([0, 0, 0, 0, 0, 0])
        
        # 3. 成交量特征
        try:
            vol_col = None
            if 'vol' in df.columns:
                vol_col = 'vol'
            elif 'volume' in df.columns:
                vol_col = 'volume'
            
            if vol_col:
                vol = df[vol_col].values[-window:]
                vol_clean = vol[~np.isnan(vol)]
                if len(vol_clean) > 0:
                    features.extend([
                        float(np.nanmean(vol)),
                        float(np.nanstd(vol)) if not np.isnan(np.nanstd(vol)) else 0,
                        float(vol[-1] / (np.nanmean(vol) + 1e-10))
                    ])
                else:
                    features.extend([0, 0, 1])
            else:
                features.extend([0, 0, 1])
        except:
            features.extend([0, 0, 1])
        
        # 4. 技术指标 - 注意：使用历史数据避免前视偏差
        try:
            close = df['close']
            
            # RSI - 确保有足够的历史数据
            rsi = self.calculate_rsi(close)
            # 使用最新值（基于历史计算）
            rsi_val = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            features.append(float(rsi_val))
            
            # MACD
            macd_line, _, histogram = self.calculate_macd(close)
            macd_val = macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0
            hist_val = histogram.iloc[-1] if not pd.isna(histogram.iloc[-1]) else 0
            features.extend([float(macd_val), float(hist_val)])
            
            # 布林带位置
            upper, middle, lower = self.calculate_bollinger(close)
            if not pd.isna(upper.iloc[-1]) and not pd.isna(lower.iloc[-1]) and upper.iloc[-1] != lower.iloc[-1]:
                bb_position = (close.iloc[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1] + 1e-10)
            else:
                bb_position = 0.5
            features.append(float(bb_position))
        except:
            features.extend([50, 0, 0, 0.5])
        
        # 5. 均线特征
        try:
            close = df['close']
            current = close.iloc[-1]
            
            ma5 = close.rolling(5).mean().iloc[-1]
            ma10 = close.rolling(10).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            
            features.extend([
                float((current - ma5) / ma5) if not pd.isna(ma5) and ma5 != 0 else 0,
                float((current - ma10) / ma10) if not pd.isna(ma10) and ma10 != 0 else 0,
                float((current - ma20) / ma20) if not pd.isna(ma20) and ma20 != 0 else 0,
                1.0 if not pd.isna(ma5) and not pd.isna(ma10) and ma5 > ma10 else 0.0,
                1.0 if not pd.isna(ma10) and not pd.isna(ma20) and ma10 > ma20 else 0.0
            ])
        except:
            features.extend([0, 0, 0, 0, 0])
        
        # 6. 波动率特征
        try:
            atr = self.calculate_atr(df)
            atr_val = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
            current = df['close'].iloc[-1]
            features.append(float(atr_val / current) if current != 0 else 0)
        except:
            features.append(0)
        
        result = np.array(features, dtype=np.float32)
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=-1.0)
        
        return result
    
    def extract_pattern_window(self, df: pd.DataFrame, start_idx: int, end_idx: int) -> np.ndarray:
        """提取指定窗口的价格序列"""
        if start_idx < 0:
            start_idx = 0
        if end_idx > len(df):
            end_idx = len(df)
        
        window_data = df.iloc[start_idx:end_idx]['close'].values
        return self.normalize_prices(window_data, 'structure')
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        # 重置索引以确保有trade_date列
        if 'trade_date' not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                df.rename(columns={'index': 'trade_date'}, inplace=True)
            else:
                df = df.reset_index(drop=True)
        
        # 去除重复
        if 'trade_date' in df.columns:
            df = df.drop_duplicates(subset=['trade_date'])
        
        # 去除缺失值
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        # 去除异常值（涨跌幅超过20%的可能是除权除息）
        if 'pct_chg' in df.columns:
            df = df[abs(df['pct_chg']) < 20]
        
        # 排序
        if 'trade_date' in df.columns:
            df = df.sort_values('trade_date')
        
        return df.reset_index(drop=True)