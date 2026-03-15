#!/usr/bin/env python3
"""
UPAS - 形态可视化模块
将发现的形态绘制成图表
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import json
import os
from typing import List, Dict, Tuple

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


def visualize_pattern_prototype(pattern_id: str, 
                                prototype: np.ndarray,
                                frequency: int,
                                rating: str = None,
                                win_rate: float = None,
                                expectancy: float = None,
                                output_path: str = None):
    """
    可视化单个形态原型
    
    Args:
        pattern_id: 形态ID
        prototype: 形态原型序列
        frequency: 出现频率
        rating: 评级
        win_rate: 历史胜率
        expectancy: 期望收益
        output_path: 输出路径
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 绘制形态原型
    x = np.arange(len(prototype))
    ax.plot(x, prototype, linewidth=3, color='#2E86AB', label='Pattern Prototype')
    ax.fill_between(x, prototype, alpha=0.3, color='#2E86AB')
    
    # 添加关键点标注
    max_idx = np.argmax(prototype)
    min_idx = np.argmin(prototype)
    
    ax.scatter([max_idx], [prototype[max_idx]], color='green', s=100, zorder=5, label='Peak')
    ax.scatter([min_idx], [prototype[min_idx]], color='red', s=100, zorder=5, label='Valley')
    
    # 标题和标签
    title = f'Pattern: {pattern_id} | Frequency: {frequency}'
    if rating:
        title += f' | Rating: {rating}'
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    ax.set_xlabel('Time Step', fontsize=12)
    ax.set_ylabel('Normalized Price', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # 添加统计信息
    info_text = []
    if win_rate is not None:
        info_text.append(f'Win Rate: {win_rate:.1%}')
    if expectancy is not None:
        info_text.append(f'Expectancy: {expectancy:.2f}%')
    
    if info_text:
        ax.text(0.02, 0.98, '\n'.join(info_text), 
                transform=ax.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✅ 形态图已保存: {output_path}")
    
    return fig


def visualize_pattern_library(pattern_library: Dict,
                              expectancy_db: Dict = None,
                              output_dir: str = None,
                              top_n: int = 9):
    """
    可视化形态库（多子图）
    
    Args:
        pattern_library: 形态库字典
        expectancy_db: 期望值数据库
        output_dir: 输出目录
        top_n: 显示前N个形态
    """
    if not pattern_library:
        print("❌ 形态库为空")
        return
    
    # 选择评分最高的形态
    if expectancy_db:
        sorted_patterns = sorted(
            pattern_library.items(),
            key=lambda x: expectancy_db.get(x[0], {}).get('expectancy', 0),
            reverse=True
        )[:top_n]
    else:
        sorted_patterns = list(pattern_library.items())[:top_n]
    
    n_patterns = len(sorted_patterns)
    n_cols = 3
    n_rows = (n_patterns + n_cols - 1) // n_cols
    
    fig = plt.figure(figsize=(15, 5 * n_rows))
    gs = GridSpec(n_rows, n_cols, figure=fig, hspace=0.3, wspace=0.3)
    
    for idx, (pattern_id, info) in enumerate(sorted_patterns):
        row = idx // n_cols
        col = idx % n_cols
        ax = fig.add_subplot(gs[row, col])
        
        prototype = info.get('prototype', np.array([]))
        if isinstance(prototype, list):
            prototype = np.array(prototype)
        
        frequency = info.get('frequency', 0)
        
        # 获取回测信息
        exp_info = expectancy_db.get(pattern_id, {}) if expectancy_db else {}
        rating = exp_info.get('rating', 'N/A')
        win_rate = exp_info.get('win_rate', 0)
        expectancy = exp_info.get('expectancy', 0)
        
        # 绘制形态
        x = np.arange(len(prototype))
        color = '#2E86AB' if rating in ['A', 'B+'] else '#A23B72' if rating in ['B'] else '#F18F01'
        
        ax.plot(x, prototype, linewidth=2, color=color)
        ax.fill_between(x, prototype, alpha=0.2, color=color)
        
        # 标题
        title = f'{pattern_id}\nFreq: {frequency}'
        if rating != 'N/A':
            title += f' | Rating: {rating}'
        ax.set_title(title, fontsize=11, fontweight='bold')
        
        ax.set_ylabel('Price', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # 统计信息
        if win_rate:
            ax.text(0.5, 0.95, f'Win: {win_rate:.1%}\nExp: {expectancy:.2f}',
                    transform=ax.transAxes, fontsize=9,
                    verticalalignment='top', horizontalalignment='center',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    fig.suptitle('UPAS Pattern Library Visualization', fontsize=16, fontweight='bold', y=1.02)
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/pattern_library_visualization.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✅ 形态库可视化已保存: {output_path}")
        return output_path
    
    return fig


def visualize_pattern_comparison(pattern_library: Dict,
                                 pattern_ids: List[str],
                                 output_path: str = None):
    """
    对比多个形态
    
    Args:
        pattern_library: 形态库
        pattern_ids: 要对比的形态ID列表
        output_path: 输出路径
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(pattern_ids)))
    
    for i, pid in enumerate(pattern_ids):
        if pid not in pattern_library:
            continue
        
        prototype = pattern_library[pid].get('prototype', [])
        if isinstance(prototype, list):
            prototype = np.array(prototype)
        
        x = np.arange(len(prototype))
        ax.plot(x, prototype, linewidth=2.5, label=pid, color=colors[i])
    
    ax.set_title('Pattern Comparison', fontsize=16, fontweight='bold')
    ax.set_xlabel('Time Step', fontsize=12)
    ax.set_ylabel('Normalized Price', fontsize=12)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✅ 对比图已保存: {output_path}")
    
    return fig


def create_pattern_dashboard(pattern_library: Dict,
                            expectancy_db: Dict,
                            output_path: str = None):
    """
    创建形态仪表板（综合可视化）
    """
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # 1. 形态分布（左上）
    ax1 = fig.add_subplot(gs[0, 0])
    ratings = [expectancy_db.get(pid, {}).get('rating', 'N/A') for pid in pattern_library.keys()]
    rating_counts = pd.Series(ratings).value_counts()
    colors = {'A': '#2E86AB', 'B+': '#A23B72', 'B': '#F18F01', 'C': '#C73E1D', 'N/A': '#888888'}
    rating_counts.plot(kind='bar', ax=ax1, color=[colors.get(r, '#888888') for r in rating_counts.index])
    ax1.set_title('Rating Distribution', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Rating')
    ax1.set_ylabel('Count')
    
    # 2. 胜率分布（中上）
    ax2 = fig.add_subplot(gs[0, 1])
    win_rates = [expectancy_db.get(pid, {}).get('win_rate', 0) * 100 for pid in pattern_library.keys()]
    ax2.hist(win_rates, bins=10, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax2.axvline(x=50, color='red', linestyle='--', label='50% (Random)')
    ax2.set_title('Win Rate Distribution', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Win Rate (%)')
    ax2.set_ylabel('Count')
    ax2.legend()
    
    # 3. 期望收益分布（右上）
    ax3 = fig.add_subplot(gs[0, 2])
    expectancies = [expectancy_db.get(pid, {}).get('expectancy', 0) for pid in pattern_library.keys()]
    ax3.hist(expectancies, bins=10, color='#A23B72', alpha=0.7, edgecolor='black')
    ax3.set_title('Expectancy Distribution', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Expectancy')
    ax3.set_ylabel('Count')
    
    # 4. 最佳形态展示（下方大区域）
    ax4 = fig.add_subplot(gs[1, :])
    
    # 选择Top 5形态
    top_patterns = sorted(
        pattern_library.items(),
        key=lambda x: expectancy_db.get(x[0], {}).get('expectancy', 0),
        reverse=True
    )[:5]
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(top_patterns)))
    
    for i, (pid, info) in enumerate(top_patterns):
        prototype = info.get('prototype', [])
        if isinstance(prototype, list):
            prototype = np.array(prototype)
        
        exp_info = expectancy_db.get(pid, {})
        win_rate = exp_info.get('win_rate', 0)
        expectancy = exp_info.get('expectancy', 0)
        
        x = np.arange(len(prototype)) + i * (len(prototype) + 5)
        ax4.plot(x, prototype, linewidth=2.5, label=f'{pid} ({win_rate:.1%}, {expectancy:.2f})', 
                color=colors[i])
    
    ax4.set_title('Top 5 Patterns', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Time Step (Pattern ID)', fontsize=12)
    ax4.set_ylabel('Normalized Price', fontsize=12)
    ax4.legend(loc='best', fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    fig.suptitle('UPAS Pattern Dashboard', fontsize=18, fontweight='bold', y=0.98)
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✅ 仪表板已保存: {output_path}")
        return output_path
    
    return fig


def main():
    """主函数 - 演示可视化"""
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace')
    
    print("=" * 70)
    print("UPAS 形态可视化演示")
    print("=" * 70)
    
    output_dir = '/root/.openclaw/workspace/upas/data/visualizations'
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载形态库
    pattern_file = '/root/.openclaw/workspace/upas/data/demo_patterns.json'
    expectancy_file = '/root/.openclaw/workspace/upas/data/demo_saved_state/expectancy_db.json'
    
    if not os.path.exists(pattern_file):
        print("❌ 形态库文件不存在，请先运行 demo_full.py")
        return
    
    print("\n1. 加载形态库...")
    with open(pattern_file, 'r') as f:
        pattern_library = json.load(f)
    
    # 转换原型为numpy数组
    for pid, info in pattern_library.items():
        if 'prototype' in info and isinstance(info['prototype'], list):
            pattern_library[pid]['prototype'] = np.array(info['prototype'])
    
    expectancy_db = {}
    if os.path.exists(expectancy_file):
        with open(expectancy_file, 'r') as f:
            expectancy_db = json.load(f)
    
    print(f"   ✅ 加载了 {len(pattern_library)} 个形态")
    
    # 2. 可视化形态库
    print("\n2. 生成形态库可视化...")
    viz_path = visualize_pattern_library(pattern_library, expectancy_db, output_dir)
    
    # 3. 生成仪表板
    print("\n3. 生成形态仪表板...")
    if expectancy_db:
        dashboard_path = create_pattern_dashboard(pattern_library, expectancy_db, 
                                                  f"{output_dir}/pattern_dashboard.png")
    
    # 4. 单独可视化最佳形态
    print("\n4. 生成最佳形态详情图...")
    if expectancy_db:
        best_pattern = max(expectancy_db.items(), key=lambda x: x[1].get('expectancy', 0))
        pid = best_pattern[0]
        if pid in pattern_library:
            info = pattern_library[pid]
            visualize_pattern_prototype(
                pid, 
                info['prototype'],
                info['frequency'],
                rating=best_pattern[1].get('rating'),
                win_rate=best_pattern[1].get('win_rate'),
                expectancy=best_pattern[1].get('expectancy'),
                output_path=f"{output_dir}/best_pattern_{pid}.png"
            )
    
    print("\n" + "=" * 70)
    print("可视化完成！")
    print("=" * 70)
    print(f"\n📁 输出文件:")
    if viz_path:
        print(f"   - 形态库总览: {viz_path}")
    if expectancy_db:
        print(f"   - 形态仪表板: {output_dir}/pattern_dashboard.png")
        print(f"   - 最佳形态详情: {output_dir}/best_pattern_{best_pattern[0]}.png")
    print("=" * 70)


if __name__ == '__main__':
    main()