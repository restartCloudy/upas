#!/usr/bin/env python3
"""
UPAS 示例脚本 - 形态发现与回测

本脚本演示如何使用UPAS系统进行：
1. 加载股票数据
2. 发现形态
3. 回测评估
4. 生成报告
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace')

import numpy as np
import pandas as pd
from upas.core.upas_system import UPAS
from upas.utils.helpers import generate_sample_data, load_stock_data


def demo_pattern_discovery():
    """演示形态发现"""
    
    print("=" * 60)
    print("UPAS 形态发现演示")
    print("=" * 60)
    
    # 1. 初始化系统
    print("\n[1] 初始化UPAS系统...")
    upas = UPAS({
        'preprocessor': {'zigzag_threshold': 0.05},
        'discovery': {'min_pattern_freq': 5, 'max_clusters': 10},
        'evaluation': {'min_samples': 5}
    })
    
    # 2. 准备数据（使用模拟数据演示）
    print("\n[2] 准备股票数据...")
    
    # 生成多只股票的数据
    price_data = []
    for i in range(50):  # 50只股票
        trend = np.random.choice(['up', 'down', 'sideways'])
        df = generate_sample_data(n_bars=250, trend=trend, seed=i)
        df['ts_code'] = f'STACK{i:04d}.SZ'
        price_data.append(df)
    
    print(f"    准备了 {len(price_data)} 只股票的数据")
    
    # 3. 发现形态
    print("\n[3] 发现L3复合形态...")
    patterns = upas.discover_patterns(
        price_data,
        complexity_level=3,
        save_path='/root/.openclaw/workspace/upas/data/discovered_patterns.json'
    )
    
    print(f"    发现 {len(patterns)} 个形态")
    
    # 显示形态详情
    for i, (pid, pinfo) in enumerate(list(patterns.items())[:5]):
        print(f"    - {pid}: 频率={pinfo.get('frequency', 0)}, "
              f"复杂度=L{pinfo.get('complexity', 1)}")
    
    return upas, patterns


def demo_backtest(upas, patterns):
    """演示回测评估"""
    
    print("\n" + "=" * 60)
    print("UPAS 六维回测评估演示")
    print("=" * 60)
    
    # 回测形态
    print("\n[4] 执行六维回测评估...")
    results = upas.backtest_patterns(
        patterns,
        output_dir='/root/.openclaw/workspace/upas/data/backtest'
    )
    
    print(f"    {len(results)} 个形态通过回测验证")
    
    # 显示回测结果
    print("\n[5] 回测结果摘要:")
    
    for i, (pid, report) in enumerate(list(results.items())[:5]):
        if report.get('status') == 'VALIDATED':
            print(f"\n    形态: {pid}")
            print(f"    - 评级: {report['rating']}")
            print(f"    - 综合得分: {report['comprehensive_score']:.3f}")
            print(f"    - 平均胜率: {report['avg_win_rate']:.1f}%")
            print(f"    - 平均期望: {report['avg_expectancy']:.2f}%")
            
            if report.get('best_scenarios'):
                best = report['best_scenarios'][0]
                print(f"    - 最佳场景: {best['scenario']} "
                      f"(胜率{best['win_rate']}%, 期望{best['expectancy']}%)")
    
    return results


def demo_recognition(upas):
    """演示形态识别"""
    
    print("\n" + "=" * 60)
    print("UPAS 实时形态识别演示")
    print("=" * 60)
    
    # 生成当前价格数据
    print("\n[6] 模拟实时数据识别...")
    
    current_data = generate_sample_data(n_bars=50, trend='up')
    
    # 识别形态
    signal = upas.recognize(current_data, top_k=3)
    
    if signal:
        print(f"\n    ✅ 识别到形态!")
        print(f"    - 形态ID: {signal['pattern_id']}")
        print(f"    - 置信度: {signal['confidence']:.2%}")
        print(f"    - 方向: {signal['direction']}")
        print(f"    - 期望收益: {signal['expected_return']:.2f}")
        print(f"    - 历史胜率: {signal['win_rate']:.1%}")
        print(f"    - 建议持有: {signal['optimal_holding']}天")
    else:
        print("    ⚠️ 未识别到有效形态")
    
    return signal


def demo_report(upas):
    """演示报告生成"""
    
    print("\n" + "=" * 60)
    print("UPAS 报告生成演示")
    print("=" * 60)
    
    # 获取顶级形态
    print("\n[7] 顶级形态排行榜:")
    
    top_patterns = upas.get_top_patterns(min_rating='B', limit=10)
    
    if top_patterns:
        print("\n    | 排名 | 形态ID | 评级 | 得分 | 期望 | 胜率 |")
        print("    |------|--------|------|------|------|------|")
        
        for i, p in enumerate(top_patterns, 1):
            print(f"    | {i} | {p['pattern_id']} | {p['rating']} | "
                  f"{p['score']:.2f} | {p['expectancy']:.2f}% | {p['win_rate']:.1f}% |")
    
    # 导出报告
    print("\n[8] 导出完整报告...")
    report_path = upas.export_report(
        '/root/.openclaw/workspace/upas/data/upas_report.md'
    )
    print(f"    报告已保存到: {report_path}")
    
    # 保存系统状态
    print("\n[9] 保存系统状态...")
    upas.save('/root/.openclaw/workspace/upas/data/saved_state')
    print("    系统状态已保存")


def demo_load_and_reuse():
    """演示加载和复用"""
    
    print("\n" + "=" * 60)
    print("UPAS 状态加载演示")
    print("=" * 60)
    
    # 创建新实例
    upas2 = UPAS()
    
    # 加载之前保存的状态
    print("\n[10] 加载保存的系统状态...")
    upas2.load('/root/.openclaw/workspace/upas/data/saved_state')
    
    print(f"    加载了 {len(upas2.pattern_library)} 个形态")
    print(f"    加载了 {len(upas2.expectancy_db)} 条期望值记录")
    
    # 再次识别
    print("\n[11] 使用加载的形态库进行识别...")
    current_data = generate_sample_data(n_bars=50, trend='up')
    signal = upas2.recognize(current_data)
    
    if signal:
        print(f"    ✅ 识别成功: {signal['pattern_id']}")
    else:
        print("    ⚠️ 未识别到形态")


def main():
    """主函数"""
    
    print("\n" + "=" * 70)
    print(" " * 20 + "UPAS 通用抽象形态系统")
    print(" " * 15 + "Universal Pattern Abstraction System")
    print("=" * 70)
    
    try:
        # 1. 形态发现
        upas, patterns = demo_pattern_discovery()
        
        if not patterns:
            print("\n❌ 形态发现失败，退出演示")
            return
        
        # 2. 回测评估
        results = demo_backtest(upas, patterns)
        
        # 3. 实时识别
        demo_recognition(upas)
        
        # 4. 报告生成
        demo_report(upas)
        
        # 5. 加载复用
        demo_load_and_reuse()
        
        print("\n" + "=" * 70)
        print("演示完成! 所有输出文件保存在 /root/.openclaw/workspace/upas/data/")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()