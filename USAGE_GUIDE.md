# UPAS - 通用抽象形态系统 使用说明书

## 📋 目录
1. [系统简介](#系统简介)
2. [安装与配置](#安装与配置)
3. [快速开始](#快速开始)
4. [核心功能详解](#核心功能详解)
5. [API参考](#api参考)
6. [使用示例](#使用示例)
7. [常见问题](#常见问题)

---

## 系统简介

UPAS (Universal Pattern Abstraction System) 是一个量化交易形态分析平台，支持从数据中自动发现、评估和应用K线形态。

### 核心特性
- **六级形态复杂度**：从单根K线到宏观结构
- **自动形态发现**：使用聚类算法从数据中挖掘形态
- **六维评估体系**：市场×策略×周期×行业×市值×波动率
- **实时形态识别**：支持实时行情匹配

---

## 安装与配置

### 环境要求
```bash
Python >= 3.8
numpy >= 1.20
pandas >= 1.3
scikit-learn >= 1.0
scipy >= 1.7
```

### 安装依赖
```bash
cd /root/.openclaw/workspace/upas
pip install -r requirements.txt
```

### 可选依赖（增强功能）
```bash
pip install fastdtw  # DTW距离计算
pip install hmmlearn  # HMM模型
```

---

## 快速开始

### 3分钟上手

```python
from upas import UPAS
import pandas as pd

# 1. 初始化系统
upas = UPAS()

# 2. 准备数据（你的A股数据）
stock_data = []
for ts_code in ['000001.SZ', '000002.SZ', '600000.SH']:
    df = pd.read_csv(f'data/{ts_code}.csv')  # 你的数据
    stock_data.append(df)

# 3. 发现形态
patterns = upas.discover_patterns(stock_data, complexity_level=3)

# 4. 实时识别
signal = upas.recognize(current_price_df)
if signal:
    print(f"发现形态: {signal['pattern_id']}, 置信度: {signal['confidence']}")
```

---

## 核心功能详解

### 1. 形态发现 (discover_patterns)

从一批股票历史数据中自动发现重复出现的K线形态。

```python
patterns = upas.discover_patterns(
    price_data,           # List[DataFrame]: 股票数据列表
    complexity_level=3,   # int: 形态复杂度 (1-4)
    save_path=None,       # str: 保存路径
    validate_data=True    # bool: 是否进行数据验证
)
```

**参数说明**:
- `complexity_level`: 
  - L1-L2 (1-2): 简单形态，4-8根K线
  - L3 (3): 复合形态，特征向量聚类
  - L4 (4): 复杂形态，30+根K线

**返回**: 形态库字典，每个形态包含原型、频率、样本索引等

---

### 2. 回测评估 (backtest_patterns)

对发现的形态进行六维度回测评估。

```python
results = upas.backtest_patterns(
    patterns=None,        # Dict: 形态库（默认使用已发现的）
    historical_data=None, # DataFrame: 历史交易数据
    output_dir='./results'  # str: 结果输出目录
)
```

**返回**: 回测结果字典，包含：
- 综合评分
- 各维度表现
- 最佳交易场景
- 胜率、盈亏比、夏普比率

---

### 3. 实时识别 (recognize)

在实时行情中识别已发现的形态。

```python
signal = upas.recognize(
    price_series,      # DataFrame: 当前价格数据
    top_k=3,           # int: 返回前K个匹配
    min_confidence=0.6 # float: 最小置信度
)
```

**返回**: 交易信号字典，包含：
- `pattern_id`: 匹配的形态ID
- `confidence`: 匹配置信度
- `expectancy`: 期望收益
- `win_rate`: 历史胜率
- `recommendation`: 交易建议

---

### 4. 保存与加载 (save/load)

```python
# 保存系统状态
upas.save(save_dir='./upas_state')

# 加载系统状态
upas2 = UPAS.load(load_dir='./upas_state')
```

---

## API参考

### UPAS主类

| 方法 | 功能 | 返回值 |
|------|------|--------|
| `discover_patterns()` | 发现形态 | Dict |
| `backtest_patterns()` | 回测评估 | Dict |
| `recognize()` | 实时识别 | Dict/None |
| `save()` | 保存状态 | None |
| `load()` | 加载状态 | UPAS |
| `export_report()` | 导出报告 | str |

### 配置参数

```python
config = {
    'preprocessor': {
        'zigzag_threshold': 0.05,   # ZigZag转折阈值
        'atr_period': 14            # ATR计算周期
    },
    'discovery': {
        'min_pattern_freq': 3,      # 最小形态频率
        'similarity_threshold': 0.70, # 相似度阈值
        'max_clusters': 10          # 最大聚类数
    },
    'evaluation': {
        'holding_periods': [1, 3, 5, 10, 20],
        'commission': 0.00025,      # 手续费
        'slippage': 0.001           # 滑点
    }
}
upas = UPAS(config)
```

---

## 使用示例

### 示例1：完整的形态发现流程

```python
from upas import UPAS
from upas.utils.helpers import load_stock_data
import pandas as pd

# 初始化
upas = UPAS()

# 加载多只股票数据
stock_list = ['000001.SZ', '000002.SZ', '600519.SH', '000858.SZ']
price_data = []

for code in stock_list:
    df = load_stock_data(code, start='20230101', end='20241231')
    if df is not None and len(df) > 60:
        price_data.append(df)

print(f"加载了 {len(price_data)} 只股票")

# 发现L3复合形态
patterns = upas.discover_patterns(
    price_data,
    complexity_level=3,
    save_path='./my_patterns.json'
)

print(f"发现 {len(patterns)} 个形态")
for pid, info in patterns.items():
    print(f"  {pid}: 频率={info['frequency']}")
```

### 示例2：回测评估

```python
# 准备历史回测数据
backtest_data = []
for code in stock_list:
    df = load_stock_data(code, start='20220101', end='20241231')
    backtest_data.append(df)

# 执行回测
results = upas.backtest_patterns(
    patterns=patterns,
    historical_data=backtest_data,
    output_dir='./backtest_results'
)

# 查看最佳形态
for pid, result in sorted(results.items(), 
                          key=lambda x: x[1].get('comprehensive_score', 0), 
                          reverse=True)[:3]:
    print(f"\n{pid}:")
    print(f"  综合评分: {result['comprehensive_score']:.3f}")
    print(f"  评级: {result['rating']}")
    print(f"  建议: {result['recommendation']}")
```

### 示例3：实时交易信号

```python
# 实时监控循环
while True:
    # 获取最新行情（示例）
    current_df = get_latest_bars('000001.SZ', n=20)
    
    # 识别形态
    signal = upas.recognize(current_df, top_k=1)
    
    if signal and signal['confidence'] > 0.7:
        print(f"\n🎯 发现交易机会!")
        print(f"  形态: {signal['pattern_id']}")
        print(f"  置信度: {signal['confidence']:.1%}")
        print(f"  历史胜率: {signal['win_rate']:.1%}")
        print(f"  期望收益: {signal['expectancy']:.2f}%")
        print(f"  建议持有: {signal['optimal_holding']}天")
        print(f"  方向: {'买入' if signal['direction'] == 'long' else '卖出'}")
        
        # 发送交易信号...
        send_trade_signal(signal)
    
    time.sleep(60)  # 每分钟检查一次
```

### 示例4：批量选股

```python
def scan_market(upas, stock_universe):
    """扫描全市场，找出符合条件的股票"""
    signals = []
    
    for code in stock_universe:
        try:
            df = get_realtime_data(code)
            if len(df) < 20:
                continue
                
            signal = upas.recognize(df, min_confidence=0.65)
            if signal:
                signals.append({
                    'code': code,
                    **signal
                })
        except Exception as e:
            continue
    
    # 按期望收益排序
    signals.sort(key=lambda x: x['expectancy'], reverse=True)
    
    return signals[:10]  # 返回前10只

# 使用
stock_list = get_all_stocks()  # 获取全市场股票
top_picks = scan_market(upas, stock_list)

print("今日选股结果:")
for pick in top_picks:
    print(f"  {pick['code']}: 期望={pick['expectancy']:.2f}%, 胜率={pick['win_rate']:.1%}")
```

---

## 常见问题

### Q1: 数据格式要求？

数据必须是包含以下列的DataFrame：
```
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- vol/volume: 成交量（可选）
- trade_date: 交易日期（可选）
```

### Q2: 发现0个形态怎么办？

- 增加股票数量（建议至少20只）
- 降低 `min_pattern_freq` 参数
- 检查数据质量（是否有缺失值）
- 尝试不同的 `complexity_level`

### Q3: 如何提高识别准确率？

- 增加训练数据的时间跨度
- 使用L3级别而非L1/L2
- 筛选回测评级A/B的形态
- 调整 `similarity_threshold` 参数

### Q4: 支持哪些市场？

目前支持：
- A股（主板、创业板、科创板）
- 港股
- 美股

需要数据格式统一为OHLCV。

---

## 文件结构

```
upas/
├── core/                      # 核心模块
│   ├── data_preprocessor.py   # 数据预处理
│   ├── pattern_discovery.py   # 形态发现
│   ├── pattern_recognition.py # 形态识别
│   ├── evaluation_engine.py   # 评估引擎
│   └── data_validation.py     # 数据验证
├── utils/                     # 工具函数
│   └── helpers.py
├── examples/                  # 示例代码
│   ├── demo_simple.py         # 简单演示
│   └── demo_full.py           # 完整演示
├── data/                      # 数据目录
└── requirements.txt           # 依赖清单
```

---

## 联系与支持

如有问题，请查看：
- 详细文档: `README.md`
- 示例代码: `examples/`
- 日志输出: 控制台日志

---

*文档版本: v1.0*  
*最后更新: 2026-03-15*
