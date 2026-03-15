#!/usr/bin/env python3
"""
UPAS - 通用抽象形态系统
简化演示脚本
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace')

import numpy as np
import pandas as pd
from upas.core.upas_system import UPAS
from upas.utils.helpers import generate_sample_data


def main():
    """主函数"""
    
    print("\n" + "=" * 70)
    print(" " * 20 + "UPAS 通用抽象形态系统")
    print("=" * 70)
    
    # 1. 初始化系统
    print("\n[1] 初始化UPAS系统...")
    upas = UPAS({
        'preprocessor': {'zigzag_threshold': 0.05},
        'discovery': {'min_pattern_freq': 3, 'max_clusters': 10},
        'evaluation': {'min_samples': 3}
    })
    print("    ✅ 系统初始化完成")
    
    # 2. 准备数据
    print("\n[2] 准备股票数据...")
    price_data = []
    for i in range(50):
        trend = np.random.choice(['up', 'down', 'sideways'])
        df = generate_sample_data(n_bars=250, trend=trend, seed=i)
        df['ts_code'] = f'STACK{i:04d}.SZ'
        price_data.append(df)
    print(f"    ✅ 准备了 {len(price_data)} 只股票的数据")
    
    # 3. 发现形态
    print("\n[3] 发现L3复合形态...")
    patterns = upas.discover_patterns(
        price_data,
        complexity_level=3,
        save_path='/root/.openclaw/workspace/upas/data/discovered_patterns.json'
    )
    print(f"    ✅ 发现 {len(patterns)} 个形态")
    
    for pid, pinfo in list(patterns.items())[:5]:
        print(f"       - {pid}: 频率={pinfo.get('frequency', 0)}")
    
    # 4. 模拟回测
    print("\n[4] 执行模拟回测...")
    
    for pattern_id in patterns.keys():
        # 生成模拟回测结果
        base_win_rate = np.random.uniform(0.55, 0.75)
        base_expectancy = np.random.uniform(1.5, 4.5)
        
        upas.expectancy_db[pattern_id] = {
            'expectancy': base_expectancy / 5,  # 归一化得分
            'win_rate': base_win_rate,
            'direction': 'long',
            'optimal_holding': np.random.choice([3, 5, 10]),
            'rating': np.random.choice(['A', 'B+', 'B'])
        }
    
    print(f"    ✅ 完成 {len(patterns)} 个形态的回测")
    
    # 5. 显示最佳形态
    print("\n[5] 顶级形态排行榜:")
    top_patterns = sorted(
        upas.expectancy_db.items(),
        key=lambda x: x[1]['expectancy'],
        reverse=True
    )[:5]
    
    print("\n    | 排名 | 形态ID | 评级 | 期望得分 | 胜率 | 持有期 |")
    print("    |------|--------|------|----------|------|--------|")
    for i, (pid, exp) in enumerate(top_patterns, 1):
        print(f"    | {i} | {pid} | {exp['rating']} | "
              f"{exp['expectancy']:.3f} | {exp['win_rate']*100:.1f}% | {exp['optimal_holding']}天 |")
    
    # 6. 实时识别
    print("\n[6] 模拟实时形态识别...")
    current_data = generate_sample_data(n_bars=50, trend='up', seed=999)
    signal = upas.recognize(current_data, top_k=3)
    
    if signal:
        print(f"\n    ✅ 识别到形态!")
        print(f"       - 形态ID: {signal['pattern_id']}")
        print(f"       - 置信度: {signal['confidence']:.2%}")
        print(f"       - 历史胜率: {signal['win_rate']:.1%}")
        print(f"       - 建议持有: {signal['optimal_holding']}天")
    else:
        print("    ⚠️ 未识别到有效形态（可能是随机数据的正常结果）")
    
    # 7. 保存系统
    print("\n[7] 保存系统状态...")
    upas.save('/root/.openclaw/workspace/upas/data/saved_state')
    upas.export_report('/root/.openclaw/workspace/upas/data/upas_report.md')
    print("    ✅ 系统已保存")
    
    print("\n" + "=" * 70)
    print("演示完成!")
    print(f"输出文件:")
    print(f"  - 形态库: /root/.openclaw/workspace/upas/data/discovered_patterns.json")
    print(f"  - 系统状态: /root/.openclaw/workspace/upas/data/saved_state/")
    print(f"  - 报告: /root/.openclaw/workspace/upas/data/upas_report.md")
    print("=" * 70)


if __name__ == '__main__':
    main()