#!/usr/bin/env python3
"""
UPAS - 完整使用演示
展示从数据准备到交易信号的完整流程
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace')

import numpy as np
import pandas as pd
from upas import UPAS
from upas.utils.helpers import generate_sample_data


def demo_data_preparation():
    """演示1: 数据准备"""
    print("\n" + "="*70)
    print("【演示1】数据准备")
    print("="*70)
    
    print("\n1. 模拟加载股票数据...")
    print("   在实际使用中，这里应该替换为你的真实数据源:")
    print("   - Tushare Pro")
    print("   - AKShare")
    print("   - 本地CSV文件")
    print("   - 数据库")
    
    # 模拟50只股票的数据
    stock_data = []
    stock_codes = []
    
    print("\n2. 生成50只股票的模拟数据...")
    for i in range(50):
        # 随机选择趋势类型
        trend = np.random.choice(['up', 'down', 'sideways', 'volatile'])
        
        # 生成数据
        df = generate_sample_data(n_bars=250, trend=trend, seed=i)
        df['ts_code'] = f'STACK{i:04d}.SZ'
        
        stock_data.append(df)
        stock_codes.append(f'STACK{i:04d}.SZ')
    
    print(f"   ✅ 已准备 {len(stock_data)} 只股票的数据")
    print(f"   示例股票代码: {stock_codes[:5]}")
    
    # 展示数据结构
    print("\n3. 数据示例 (STACK0001.SZ):")
    print(stock_data[1].tail(5).to_string())
    
    return stock_data, stock_codes


def demo_pattern_discovery(stock_data):
    """演示2: 形态发现"""
    print("\n" + "="*70)
    print("【演示2】形态发现")
    print("="*70)
    
    # 初始化UPAS
    print("\n1. 初始化UPAS系统...")
    upas = UPAS({
        'preprocessor': {'zigzag_threshold': 0.05},
        'discovery': {'min_pattern_freq': 3, 'max_clusters': 10},
        'evaluation': {'min_samples': 3}
    })
    print("   ✅ 系统初始化完成")
    
    # 发现形态
    print("\n2. 开始发现L3复合形态...")
    print("   参数设置:")
    print("   - 复杂度级别: L3 (复合形态)")
    print("   - 最小频率: 3")
    print("   - 最大聚类数: 10")
    
    patterns = upas.discover_patterns(
        price_data=stock_data,
        complexity_level=3,
        save_path='/root/.openclaw/workspace/upas/data/demo_patterns.json'
    )
    
    print(f"\n   ✅ 发现 {len(patterns)} 个形态")
    
    # 展示发现的形态
    print("\n3. 形态详情:")
    for i, (pid, info) in enumerate(patterns.items(), 1):
        print(f"\n   形态 {i}: {pid}")
        print(f"   - 出现频率: {info['frequency']} 次")
        print(f"   - 复杂度: L{info['complexity']}")
        print(f"   - 原型维度: {len(info['prototype'])} 维")
    
    return upas, patterns


def demo_backtest(upas, patterns):
    """演示3: 回测评估"""
    print("\n" + "="*70)
    print("【演示3】六维回测评估")
    print("="*70)
    
    print("\n1. 执行回测...")
    print("   评估维度:")
    print("   - 市场: 主板/创业板/科创板")
    print("   - 策略: 右侧追涨/超跌低吸/趋势跟踪/震荡套利")
    print("   - 周期: T+1/T+3/T+5/T+10/T+20")
    
    # 这里使用模拟数据演示
    # 实际应用中，应该传入真实的历史交易数据
    print("\n2. 模拟回测结果:")
    
    # 为每个形态生成模拟回测数据
    for pattern_id in patterns.keys():
        # 模拟回测结果
        base_win_rate = np.random.uniform(0.55, 0.75)
        base_expectancy = np.random.uniform(1.5, 4.5)
        rating = np.random.choice(['A', 'B+', 'B', 'C'])
        
        upas.expectancy_db[pattern_id] = {
            'expectancy': base_expectancy / 5,
            'win_rate': base_win_rate,
            'direction': 'long',
            'optimal_holding': np.random.choice([3, 5, 10]),
            'rating': rating
        }
    
    print(f"   ✅ 完成 {len(patterns)} 个形态的回测")
    
    # 展示回测结果
    print("\n3. 形态排行榜:")
    top_patterns = sorted(
        upas.expectancy_db.items(),
        key=lambda x: x[1]['expectancy'],
        reverse=True
    )
    
    print("\n   ┌────────┬──────────┬────────┬──────────┬────────┬──────────┐")
    print("   │ 排名   │ 形态ID   │ 评级   │ 期望得分 │ 胜率   │ 持有期   │")
    print("   ├────────┼──────────┼────────┼──────────┼────────┼──────────┤")
    
    for i, (pid, exp) in enumerate(top_patterns[:5], 1):
        print(f"   │ {i}<{4} │ {pid:<8} │ {exp['rating']:<6} │ "
              f"{exp['expectancy']:.3f}<{8} │ {exp['win_rate']*100:.1f}%<{6} │ "
              f"{exp['optimal_holding']}天<{8} │")
    
    print("   └────────┴──────────┴────────┴──────────┴────────┴──────────┘")
    
    return upas


def demo_realtime_recognition(upas, stock_codes):
    """演示4: 实时形态识别"""
    print("\n" + "="*70)
    print("【演示4】实时形态识别")
    print("="*70)
    
    print("\n1. 模拟实时行情监控...")
    print("   场景：扫描全市场寻找匹配的形态")
    
    found_signals = []
    
    # 模拟扫描10只股票
    print("\n2. 扫描股票:")
    for i, code in enumerate(stock_codes[:10], 1):
        # 生成当前行情数据
        current_df = generate_sample_data(n_bars=30, trend='up', seed=100+i)
        
        # 识别形态
        signal = upas.recognize(current_df, top_k=1)
        
        if signal and signal.get('confidence', 0) > 0.5:
            print(f"   [{i}/10] {code}: ✅ 发现形态 {signal['pattern_id']} "
                  f"(置信度: {signal['confidence']:.1%})")
            found_signals.append({
                'code': code,
                **signal
            })
        else:
            print(f"   [{i}/10] {code}: ❌ 未匹配")
    
    # 展示识别结果
    if found_signals:
        print(f"\n3. 识别结果汇总:")
        print(f"   共发现 {len(found_signals)} 个交易信号")
        
        for sig in found_signals[:3]:
            print(f"\n   🎯 {sig['code']}")
            print(f"      匹配形态: {sig['pattern_id']}")
            print(f"      置信度: {sig['confidence']:.1%}")
            print(f"      历史胜率: {sig['win_rate']:.1%}")
            print(f"      建议持有: {sig['optimal_holding']}天")
            print(f"      交易方向: {'买入' if sig['direction'] == 'long' else '卖出'}")
    else:
        print("\n   ⚠️ 未识别到有效形态（使用随机数据是正常现象）")
    
    return found_signals


def demo_save_load(upas):
    """演示5: 保存与加载"""
    print("\n" + "="*70)
    print("【演示5】系统状态保存与加载")
    print("="*70)
    
    # 保存系统
    print("\n1. 保存系统状态...")
    save_path = '/root/.openclaw/workspace/upas/data/demo_saved_state'
    upas.save(save_path)
    print(f"   ✅ 系统已保存到: {save_path}")
    
    # 导出报告
    print("\n2. 导出评估报告...")
    report_path = '/root/.openclaw/workspace/upas/data/demo_report.md'
    upas.export_report(report_path)
    print(f"   ✅ 报告已导出到: {report_path}")
    
    # 加载系统
    print("\n3. 加载系统状态...")
    upas2 = UPAS.load(save_path)
    print(f"   ✅ 已加载 {len(upas2.pattern_library)} 个形态")
    print(f"   ✅ 已加载 {len(upas2.expectancy_db)} 条期望值记录")
    
    return upas2


def demo_practical_usage():
    """演示6: 实际使用场景"""
    print("\n" + "="*70)
    print("【演示6】实际使用场景示例")
    print("="*70)
    
    print("\n1. 盘前选股流程:")
    print("""
    # 每天早上9:00执行的选股脚本
    
    from upas import UPAS
    
    # 加载已训练的系统
    upas = UPAS.load('./upas_state')
    
    # 获取全市场股票列表
    stock_list = get_stock_universe()  # 约5000只
    
    signals = []
    for code in stock_list:
        df = get_realtime_data(code, n=30)
        signal = upas.recognize(df, min_confidence=0.65)
        if signal:
            signals.append({'code': code, **signal})
    
    # 按期望收益排序
    signals.sort(key=lambda x: x['expectancy'], reverse=True)
    
    # 输出今日选股
    print("今日推荐:")
    for s in signals[:5]:
        print(f"  {s['code']}: 胜率{s['win_rate']:.1%}, 期望{s['expectancy']:.2f}%")
    """)
    
    print("\n2. 盘中监控流程:")
    print("""
    # 实时监控系统
    
    while market_is_open():
        for code in watch_list:
            df = get_latest_bars(code, n=30)
            signal = upas.recognize(df)
            
            if signal and signal['confidence'] > 0.7:
                send_alert(f"发现机会: {code}")
                # 触发交易...
        
        time.sleep(60)  # 每分钟检查一次
    """)
    
    print("\n3. 盘后复盘流程:")
    print("""
    # 盘后更新形态库
    
    # 获取当日全部交易数据
    today_data = get_today_data()
    
    # 重新发现形态（增量）
    new_patterns = upas.discover_patterns(
        today_data,
        complexity_level=3
    )
    
    # 合并到现有形态库
    upas.pattern_library.update(new_patterns)
    
    # 重新回测
    upas.backtest_patterns()
    
    # 保存更新后的系统
    upas.save('./upas_state')
    """)


def main():
    """主函数 - 完整演示"""
    
    print("\n" + "="*70)
    print(" " * 15 + "UPAS 通用抽象形态系统")
    print(" " * 20 + "完整使用演示")
    print("="*70)
    
    # 演示1: 数据准备
    stock_data, stock_codes = demo_data_preparation()
    
    # 演示2: 形态发现
    upas, patterns = demo_pattern_discovery(stock_data)
    
    # 演示3: 回测评估
    upas = demo_backtest(upas, patterns)
    
    # 演示4: 实时识别
    signals = demo_realtime_recognition(upas, stock_codes)
    
    # 演示5: 保存加载
    upas2 = demo_save_load(upas)
    
    # 演示6: 实际使用场景
    demo_practical_usage()
    
    # 总结
    print("\n" + "="*70)
    print("演示完成！")
    print("="*70)
    print("\n📁 输出文件:")
    print("   - 形态库: /root/.openclaw/workspace/upas/data/demo_patterns.json")
    print("   - 系统状态: /root/.openclaw/workspace/upas/data/demo_saved_state/")
    print("   - 报告: /root/.openclaw/workspace/upas/data/demo_report.md")
    print("\n📖 详细文档: /root/.openclaw/workspace/upas/USAGE_GUIDE.md")
    print("="*70)


if __name__ == '__main__':
    main()