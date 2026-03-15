"""
UPAS - 通用抽象形态系统
工具函数
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional


def load_stock_data(ts_code: str, start_date: str, end_date: str, db_path: str = None) -> pd.DataFrame:
    """
    从数据库加载股票数据
    
    Args:
        ts_code: 股票代码
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        db_path: 数据库路径
        
    Returns:
        DataFrame
    """
    try:
        import sqlite3
        
        if db_path is None:
            db_path = '/root/ai-trading/data/stock_data.db'
        
        conn = sqlite3.connect(db_path)
        
        query = f"""
        SELECT * FROM daily_data_fq 
        WHERE ts_code = '{ts_code}' 
        AND trade_date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY trade_date
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
        
        return df
        
    except Exception as e:
        print(f"加载数据失败: {e}")
        return pd.DataFrame()


def generate_sample_data(n_bars: int = 100, trend: str = 'up', seed: int = None) -> pd.DataFrame:
    """
    生成示例数据
    
    Args:
        n_bars: K线数量
        trend: 趋势方向 ('up', 'down', 'sideways')
        seed: 随机种子
        
    Returns:
        DataFrame
    """
    if seed is not None:
        np.random.seed(seed)
    else:
        np.random.seed()
    
    if trend == 'up':
        drift = 0.002
    elif trend == 'down':
        drift = -0.002
    else:
        drift = 0
    
    # 生成收益率序列
    returns = np.random.normal(drift, 0.015, n_bars)
    prices = 100 * np.exp(np.cumsum(returns))
    
    # 生成OHLC
    opens = prices * (1 + np.random.normal(0, 0.003, n_bars))
    closes = prices
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.008, n_bars)))
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.008, n_bars)))
    
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'vol': np.random.randint(1000000, 10000000, n_bars)
    })
    
    # 确保high >= max(open, close), low <= min(open, close)
    df['high'] = np.maximum(df['high'], df[['open', 'close']].max(axis=1))
    df['low'] = np.minimum(df['low'], df[['open', 'close']].min(axis=1))
    
    df.index = pd.date_range(start='2024-01-01', periods=n_bars, freq='D')
    
    return df


def calculate_pattern_statistics(pattern_library: Dict) -> Dict:
    """计算形态库统计信息"""
    
    stats = {
        'total_patterns': len(pattern_library),
        'by_complexity': {},
        'avg_frequency': 0,
        'total_frequency': 0
    }
    
    for pattern in pattern_library.values():
        comp = pattern.get('complexity', 1)
        stats['by_complexity'][comp] = stats['by_complexity'].get(comp, 0) + 1
        stats['total_frequency'] += pattern.get('frequency', 0)
    
    if pattern_library:
        stats['avg_frequency'] = stats['total_frequency'] / len(pattern_library)
    
    return stats


def format_expectancy_report(expectancy_db: Dict, top_n: int = 10) -> str:
    """格式化期望值报告"""
    
    lines = ["# 形态期望值报告", ""]
    
    # 排序
    sorted_items = sorted(
        expectancy_db.items(),
        key=lambda x: x[1].get('expectancy', 0),
        reverse=True
    )[:top_n]
    
    lines.append("| 排名 | 形态ID | 评级 | 期望收益 | 胜率 | 推荐持有 |")
    lines.append("|------|--------|------|----------|------|----------|")
    
    for i, (pattern_id, exp) in enumerate(sorted_items, 1):
        lines.append(
            f"| {i} | {pattern_id} | {exp.get('rating', 'N/A')} | "
            f"{exp.get('expectancy', 0):.3f} | {exp.get('win_rate', 0)*100:.1f}% | "
            f"{exp.get('optimal_holding', 5)}天 |"
        )
    
    return '\n'.join(lines)