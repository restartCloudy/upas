# UPAS - Universal Pattern Abstraction System

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-brightgreen)](https://你的用户名.github.io/upas/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**通用抽象形态系统** - 量化交易形态分析平台

![UPAS Dashboard](./docs/images/dashboard.png)

## 🌟 在线演示

🌐 **GitHub Pages**: https://你的用户名.github.io/upas/

> 注：在线演示使用静态数据展示界面。完整功能需要部署后端服务器。

## 📖 系统简介

UPAS是一个多层级形态分析系统，支持：

- **L1形态**: 单根K线形态（锤子线、十字星、吞没等）
- **L2形态**: 简单形态（双底、头肩、三角形等）
- **L3形态**: 复合形态（多K线组合模式）
- **L4形态**: 宏观结构（长期趋势、周期框架）

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/你的用户名/upas.git
cd upas
pip install -r requirements.txt
```

### 使用

```python
from upas import UPAS

# 初始化
upas = UPAS()

# 发现形态
patterns = upas.discover_patterns(stock_data, complexity_level=3)

# 实时识别
signal = upas.recognize(current_price_df)
if signal:
    print(f"买入信号！胜率: {signal['win_rate']:.1%}")
```

## 📊 系统架构

```
数据层 → 预处理层 → 发现层 → 评估层 → 应用层
  ↓         ↓         ↓        ↓        ↓
日线数据   特征向量   聚类分析   六维回测   实时识别
```

## 🛠️ 技术栈

- **Python 3.8+**: 核心算法
- **NumPy/Pandas**: 数据处理
- **scikit-learn**: 聚类算法
- **Matplotlib**: 可视化
- **JavaScript/HTML**: 前端展示

## 📁 项目结构

```
upas/
├── core/                   # 核心算法
│   ├── upas_system.py      # 主控类
│   ├── data_preprocessor.py
│   ├── pattern_discovery.py
│   ├── pattern_recognition.py
│   └── evaluation_engine.py
├── utils/                  # 工具函数
│   └── visualizer.py
├── examples/               # 示例代码
│   └── demo_full.py
├── web_demo/              # GitHub Pages前端
│   └── index.html
├── docs/                  # 文档
│   └── USAGE_GUIDE.md
└── tests/                 # 测试
```

## 🌐 API接口

后端部署后，可通过以下接口获取数据：

```
GET http://你的服务器IP:8080/api/patterns
GET http://你的服务器IP:8080/api/expectancy
GET http://你的服务器IP:8080/api/recognize?code=000001.SZ
```

## 📸 可视化示例

![形态库总览](./docs/images/pattern_library.png)

![形态仪表板](./docs/images/dashboard.png)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**作者**: UPAS Team  
**更新日期**: 2026-03-15