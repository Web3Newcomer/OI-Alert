# 币安永续合约交易信号系统 - 快速开始指南

## 🚀 5分钟快速上手

### 1. 安装依赖
```bash
pip3 install -r requirements.txt
```

### 2. 配置环境变量（可选）
创建 `.env` 文件：
```bash
# 企业微信配置
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_webhook_key
ENABLE_WECHAT_NOTIFICATION=true

# CoinMarketCap API 配置（推荐）
COINMARKETCAP_API_KEY=your_coinmarketcap_api_key
ENABLE_COINMARKETCAP=true
```

### 3. 运行主程序
```bash
# 立即运行一次
python3 scheduler.py --run-now

# 启动定时任务（推荐）
python3 scheduler.py --daemon --funding-rate
```

## 📊 查看结果

运行完成后，您将看到：
- 实时交易信号分析报告
- 买入信号列表（OI市值警报）
- 异常警报信号（OI异常警报）
- 风险评分和综合指标
- 企业微信推送通知

## 🔄 币种列表与流通量管理

### 自动管理（推荐）
系统会自动维护币种列表和流通量数据：
- **币种列表更新**：每次运行自动检测无效币种，添加新币种
- **流通量数据**：自动获取并缓存，支持手动覆盖

### 手动更新（可选）
```bash
# 更新币种列表和流通量数据
python3 update_symbols.py --update

# 只获取有效币种列表
python3 update_symbols.py --get-valid
```

### 手动设置流通量
在 `manual_supply.py` 中添加需要手动覆盖的币种：
```python
MANUAL_SUPPLY = {
    'BTC': 19889596,  # 手动设置BTC流通量
    'ETH': 120716539,  # 手动设置ETH流通量
    # ... 其他币种
}
```

### 自动更新流通量（推荐）
使用流通量更新工具自动获取最新数据：
```bash
# 强制更新所有币种的流通量（推荐）
python3 update_supply.py --force-all --save

# 只更新新币种的流通量
python3 update_supply.py --new --save

# 更新指定币种的流通量
python3 update_supply.py --symbols BTC ETH BNB --force --save
```

**工具特性：**
- ✅ 优先使用CoinMarketCap API，失败时自动降级到CoinGecko
- ✅ 支持强制更新所有币种，不再因为"已有数据"就跳过
- ✅ 获取失败的币种记录为None，便于后续处理
- ✅ 自动备份原文件，生成详细更新报告

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

# 平衡策略（默认）
config = StrategyConfig.get_balanced_config()
analyzer = TradingSignalAnalyzer(config)
```

### 方法2: 编辑配置文件
打开 `strategy_config.py`，修改以下参数：
```python
# OI市值警报参数
OI_MARKET_CAP_RATIO_THRESHOLD = 0.5  # OI/市值比率阈值
MIN_OI_VALUE = 5_000_000  # 最小OI价值
SIGNAL_STRENGTH_THRESHOLD = 60  # 信号强度阈值

# OI异常警报参数
FUNDING_RATE_ABS_THRESHOLD = 0.001  # 资金费率绝对值阈值（0.1%）
OI_SURGE_RATIO_THRESHOLD = 2.0  # OI短期激增比率阈值
```

## 🎯 核心策略参数说明

| 参数 | 说明 | 默认值 | 建议范围 |
|------|------|--------|----------|
| OI_MARKET_CAP_RATIO_THRESHOLD | OI/市值比率阈值 | 0.5 | 0.3-0.8 |
| MIN_OI_VALUE | 最小OI价值(USDT) | 5,000,000 | 2M-10M |
| VOLUME_MARKET_CAP_RATIO_THRESHOLD | 成交量/市值比率 | 0.1 | 0.05-0.15 |
| SIGNAL_STRENGTH_THRESHOLD | 信号强度阈值 | 60 | 50-75 |
| MAX_RISK_SCORE | 最大风险评分 | 70 | 50-80 |
| FUNDING_RATE_ABS_THRESHOLD | 资金费率绝对值阈值 | 0.001 | 0.0005-0.002 |
| OI_SURGE_RATIO_THRESHOLD | OI短期激增比率阈值 | 2.0 | 1.5-2.5 |

## 🚨 双重警报机制

### 1. OI市值警报（买入信号）
- **触发条件**：OI/市值 > 0.5 + OI > 5M + 成交量/市值 > 0.1 + 信号强度 > 60
- **用途**：寻找投资机会
- **示例**：`OI/市值警报 | OI/市值比高(0.57) | OI充足(8.4M)`

### 2. OI异常警报（市场异常警告）
- **触发条件**：资金费率绝对值 > 0.1% AND OI短期激增 > 2.0
- **用途**：市场异常警告，风险提示
- **示例**：`🚨OI异常警报 | 资金费率异常(0.15%) | OI激增(2.5x)`

## 📈 策略选择建议

### 新手投资者
- 使用**保守策略**
- 关注信号强度 > 75 的交易对
- 风险评分 < 50
- 资金费率阈值：0.2%
- OI激增阈值：2.5倍

### 经验投资者
- 使用**平衡策略**
- 关注信号强度 > 60 的交易对
- 风险评分 < 70
- 资金费率阈值：0.1%
- OI激增阈值：2.0倍

### 专业投资者
- 使用**激进策略**
- 关注信号强度 > 50 的交易对
- 风险评分 < 80
- 资金费率阈值：0.05%
- OI激增阈值：1.5倍

## 🔧 常见问题

### Q: 如何获取更多交易对数据？
A: 修改 `config.py` 中的 `TOP_VOLUME_LIMIT` 参数

### Q: 如何调整信号灵敏度？
A: 修改 `strategy_config.py` 中的阈值参数

### Q: 币种列表会自动更新吗？
A: 是的，每次运行主程序时都会自动更新币种列表

### Q: 流通量数据如何管理？
A: 系统自动获取，`manual_supply.py` 可手动覆盖，优先级最高

### Q: 如何更新流通量数据？
A: 使用 `python3 update_supply.py --force-all --save` 强制更新所有币种

### Q: 流通量获取失败怎么办？
A: 失败的币种会记录为None，可以手动在 `manual_supply.py` 中设置，或重新运行更新工具

### Q: OI历史数据保存在哪里？
A: 保存在 `oi_history_data/` 目录，每天一个文件，自动保留10天

### Q: 如何查看下次运行时间？
A: 运行 `python3 scheduler.py --show-next`

## 📞 技术支持

如果遇到问题，请检查：
1. 网络连接是否正常
2. Python版本是否为3.7+
3. 依赖包是否正确安装
4. 企业微信webhook配置是否正确
5. 查看日志输出，了解具体错误信息

## 🎉 开始使用

现在您可以开始使用交易信号系统了！建议：

1. **先运行一次测试**：`python3 scheduler.py --run-now`
2. **查看推送效果**：确认企业微信通知正常
3. **选择合适的策略**：根据风险偏好选择保守/平衡/激进策略
4. **启动定时任务**：`python3 scheduler.py --daemon --funding-rate`
5. **定期监控**：查看日志和推送结果，调整策略参数

系统会自动维护币种列表、收集OI历史数据、分析交易信号，为您提供专业的量化交易支持！ 