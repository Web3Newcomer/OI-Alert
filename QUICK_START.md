# 币安永续合约交易信号系统 - 快速开始指南

## 🚀 5分钟快速上手

### 1. 安装依赖
```bash
pip3 install -r requirements.txt
```

### 2. 测试API连接
```bash
python3 test_data_collection.py
```

### 3. 运行交易信号分析
```bash
python3 binance_data_collector.py
```

### 4. 测试不同策略配置
```bash
python3 test_strategy_configs.py
```

## 📊 查看结果

运行完成后，您将看到：
- 实时交易信号分析报告
- 买入信号列表
- 风险评分
- 自动保存的CSV文件

## ⚙️ 调整策略参数

### 方法1: 使用预设策略
```python
from strategy_config import StrategyConfig
from trading_signal_analyzer import TradingSignalAnalyzer

# 保守策略
config = StrategyConfig.get_conservative_config()
analyzer = TradingSignalAnalyzer(config)

# 激进策略
config = StrategyConfig.get_aggressive_config()
analyzer = TradingSignalAnalyzer(config)
```

### 方法2: 编辑配置文件
打开 `strategy_config.py`，修改以下参数：
```python
OI_MARKET_CAP_RATIO_THRESHOLD = 0.5  # OI/市值比率阈值
MIN_OI_VALUE = 5_000_000  # 最小OI价值
SIGNAL_STRENGTH_THRESHOLD = 60  # 信号强度阈值
```

## 🎯 核心策略参数说明

| 参数 | 说明 | 默认值 | 建议范围 |
|------|------|--------|----------|
| OI_MARKET_CAP_RATIO_THRESHOLD | OI/市值比率阈值 | 0.5 | 0.3-0.8 |
| MIN_OI_VALUE | 最小OI价值(USDT) | 5,000,000 | 2M-10M |
| VOLUME_MARKET_CAP_RATIO_THRESHOLD | 成交量/市值比率 | 0.1 | 0.05-0.15 |
| SIGNAL_STRENGTH_THRESHOLD | 信号强度阈值 | 60 | 50-75 |
| MAX_RISK_SCORE | 最大风险评分 | 70 | 50-80 |

## 📈 策略选择建议

### 新手投资者
- 使用**保守策略**
- 关注信号强度 > 75 的交易对
- 风险评分 < 50

### 经验投资者
- 使用**平衡策略**
- 关注信号强度 > 60 的交易对
- 风险评分 < 70

### 专业投资者
- 使用**激进策略**
- 关注信号强度 > 50 的交易对
- 风险评分 < 80

## 🔧 常见问题

### Q: 如何获取更多交易对数据？
A: 修改 `binance_data_collector.py` 中的 `limit` 参数

### Q: 如何调整信号灵敏度？
A: 修改 `strategy_config.py` 中的阈值参数

### Q: 如何添加新的过滤条件？
A: 在 `trading_signal_analyzer.py` 中添加新的过滤逻辑

## 📞 技术支持

如果遇到问题，请检查：
1. 网络连接是否正常
2. Python版本是否为3.7+
3. 依赖包是否正确安装

## 🎉 开始使用

现在您可以开始使用交易信号系统了！建议先运行测试脚本熟悉功能，然后根据您的风险偏好选择合适的策略配置。 