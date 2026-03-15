#!/usr/bin/env python3
"""
UPAS 图表查看器 - 终端友好的形态展示
在无法显示图形的环境中使用
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, '/root/.openclaw/workspace')

VIZ_DIR = '/root/.openclaw/workspace/upas/data/visualizations'
DATA_DIR = '/root/.openclaw/workspace/upas/data'


def print_pattern_ascii(prototype, width=60, height=15):
    """用ASCII字符打印形态走势"""
    if isinstance(prototype, list):
        prototype = np.array(prototype)
    
    min_val, max_val = prototype.min(), prototype.max()
    range_val = max_val - min_val if max_val != min_val else 1
    
    # 归一化到 0-height
    normalized = ((prototype - min_val) / range_val * (height - 1)).astype(int)
    
    # 创建画布
    canvas = [[' ' for _ in range(width)] for _ in range(height)]
    
    # 绘制坐标轴
    mid_y = height // 2
    for x in range(width):
        canvas[mid_y][x] = '·'
    
    # 绘制走势
    step = len(prototype) / width
    prev_y = None
    
    for i in range(width):
        idx = int(i * step)
        if idx < len(prototype):
            y = height - 1 - normalized[idx]  # 翻转Y轴
            if prev_y is not None:
                # 画线
                for yy in range(min(prev_y, y), max(prev_y, y) + 1):
                    canvas[yy][i-1] = '│'
            canvas[y][i] = '●'
            prev_y = y
    
    # 打印
    print('┌' + '─' * width + '┐')
    for row in canvas:
        print('│' + ''.join(row) + '│')
    print('└' + '─' * width + '┘')


def show_pattern_report():
    """显示形态报告"""
    print("\n" + "="*70)
    print("UPAS 形态分析报告".center(70))
    print("="*70)
    
    # 加载形态库
    pattern_file = os.path.join(DATA_DIR, 'demo_patterns.json')
    expectancy_file = os.path.join(DATA_DIR, 'demo_saved_state/expectancy_db.json')
    
    if not os.path.exists(pattern_file):
        print("❌ 形态库文件不存在")
        return
    
    with open(pattern_file, 'r') as f:
        pattern_library = json.load(f)
    
    expectancy_db = {}
    if os.path.exists(expectancy_file):
        with open(expectancy_file, 'r') as f:
            expectancy_db = json.load(f)
    
    print(f"\n📊 形态库概览:")
    print(f"   发现形态数量: {len(pattern_library)}")
    
    # 排序
    sorted_patterns = sorted(
        pattern_library.items(),
        key=lambda x: expectancy_db.get(x[0], {}).get('expectancy', 0),
        reverse=True
    )
    
    print(f"\n🏆 Top 5 形态:")
    print("-"*70)
    print(f"{'排名':<4} {'形态ID':<10} {'评级':<6} {'胜率':<8} {'期望':<8} {'频率':<6}")
    print("-"*70)
    
    for i, (pid, info) in enumerate(sorted_patterns[:5], 1):
        exp_info = expectancy_db.get(pid, {})
        rating = exp_info.get('rating', 'N/A')
        win_rate = exp_info.get('win_rate', 0)
        expectancy = exp_info.get('expectancy', 0)
        freq = info.get('frequency', 0)
        
        print(f"{i:<4} {pid:<10} {rating:<6} {win_rate*100:>6.1f}% {expectancy:>6.2f}  {freq:<6}")
    
    print("-"*70)
    
    # 显示最佳形态的ASCII图
    if sorted_patterns:
        best_id, best_info = sorted_patterns[0]
        prototype = best_info.get('prototype', [])
        exp_info = expectancy_db.get(best_id, {})
        
        print(f"\n🎯 最佳形态详情: {best_id}")
        print(f"   评级: {exp_info.get('rating', 'N/A')}")
        print(f"   胜率: {exp_info.get('win_rate', 0)*100:.1f}%")
        print(f"   期望收益: {exp_info.get('expectancy', 0):.2f}")
        print(f"   出现频率: {best_info.get('frequency', 0)}")
        print(f"\n   形态走势 (ASCII):")
        print_pattern_ascii(prototype)
    
    print("\n" + "="*70)
    print(f"\n📁 生成的图表文件:")
    if os.path.exists(VIZ_DIR):
        for f in os.listdir(VIZ_DIR):
            if f.endswith('.png'):
                print(f"   - {VIZ_DIR}/{f}")
    
    print("\n💡 查看图表的方法:")
    print("   1. SSH端口转发: ssh -L 8080:localhost:8080 root@你的IP")
    print("   2. 下载图片: scp root@你的IP:/root/.openclaw/workspace/upas/data/visualizations/*.png ./")
    print("   3. 浏览器访问: http://服务器IP:8080 (如果开放端口)")
    print("="*70 + "\n")


def list_visualizations():
    """列出所有可视化文件"""
    print("\n📂 可用的可视化文件:")
    print("-"*70)
    
    if not os.path.exists(VIZ_DIR):
        print("   可视化目录不存在")
        return
    
    files = [f for f in os.listdir(VIZ_DIR) if f.endswith('.png')]
    
    if not files:
        print("   暂无可视化文件")
        return
    
    for i, f in enumerate(files, 1):
        filepath = os.path.join(VIZ_DIR, f)
        size = os.path.getsize(filepath) / 1024  # KB
        print(f"   {i}. {f} ({size:.1f} KB)")
    
    print("-"*70)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='UPAS 终端可视化工具')
    parser.add_argument('--report', '-r', action='store_true', help='显示完整报告')
    parser.add_argument('--list', '-l', action='store_true', help='列出可视化文件')
    
    args = parser.parse_args()
    
    if args.list:
        list_visualizations()
    elif args.report:
        show_pattern_report()
    else:
        # 默认显示报告
        show_pattern_report()