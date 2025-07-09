# 币安永续合约交易信号系统

本项目为币安永续合约量化信号自动分析与推送系统，支持本地流通量维护、自动采集行情、信号分析、企业微信推送等全流程。

## 功能特性

- 自动获取币安USDT合约所有币种的最新行情、资金费率、未平仓合约、24h涨跌幅等
- 支持本地流通量维护，manual_supply.py 可手动优先覆盖
- **优先使用 CoinMarketCap API**，Coingecko 作为备用数据源，大幅提高流通量数据获取成功率
- 只分析成交量前N（如100）币种，自动过滤冷门币
- 市值、OI/市值、资金费率、风险评分等多维信号分析
- 一键推送企业微信，推送内容美观、包含市值等关键信息
- 完善的异常处理与进度提示

## 快速开始

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量（可选，见 config.py）
   - 企业微信 webhook 地址
   - **CoinMarketCap API Key（推荐配置，提高流通量数据获取成功率）**

3. 维护本地流通量（可选）
- 运行 `python update_local_supply.py` 自动批量更新流通量
- 在 `manual_supply.py` 填写需手动覆盖的币种流通量

4. 一键运行主流程
```bash
python scheduler.py --run-now
```

## 配置说明

### 环境变量配置

创建 `.env` 文件（可选）：
```bash
# 企业微信配置
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_webhook_key
ENABLE_WECHAT_NOTIFICATION=true

# CoinMarketCap API 配置（推荐配置）
COINMARKETCAP_API_KEY=your_coinmarketcap_api_key
ENABLE_COINMARKETCAP=true

# 其他配置
LOG_LEVEL=INFO
```

### CoinMarketCap API Key 获取

1. 访问 [CoinMarketCap Developer Portal](https://coinmarketcap.com/api/)
2. 注册账号并创建 API Key
3. 将 API Key 添加到环境变量或 `.env` 文件

**优势：**
- **优先使用 CoinMarketCap API**，数据更准确可靠
- 当 CoinMarketCap 获取失败时，自动降级到 Coingecko
- 大幅提高流通量数据获取成功率
- 支持更多币种的数据获取

### 其他配置

- `TOP_VOLUME_LIMIT`：只分析成交量前N币种（默认100），可在 config.py 配置
- `manual_supply.py`：手动优先覆盖流通量，未填写则用自动采集
- 其他策略参数详见 `strategy_config.py`

## 推送内容示例

企业微信推送内容如下：

```
【币安永续合约交易信号分析报告】
分析时间: 2025-07-07 15:43:49 (东八区)
分析币种: 20
买入信号: 2
卖出信号: 0
强信号: 2
平均信号强度: 55.2
平均风险评分: 37.0
平均OI/市值比: 0.45
平均资金费率: 0.01%
平均价格变化: 0.12%

【推荐买入信号】
1. MYX  价格: $0.1200  市值: $14.9M  信号强度: 100.0/100  风险: 45.9/100  OI/市值: 1.82  资金费率: 4.200%  24h涨跌: +0.59%
2. VIC  价格: $0.2700  市值: $32.4M  信号强度: 100.0/100  风险: 47.4/100  OI/市值: 0.50  资金费率: -2.000%  24h涨跌: +0.74%

【推荐卖出信号】
暂无推荐卖出信号
```

## 数据字段说明

- `symbol`: 交易对符号
- `price`: 当前价格
- `quote_volume_24h`: 24小时成交额（USDT）
- `open_interest_value`: 未平仓合约价值
- `funding_rate`: 资金费率
- `price_change_percent_24h`: 24小时价格变化百分比（小数）
- `market_cap_estimate`: 市值估算

## 策略配置

- 策略参数可在 `strategy_config.py` 调整，支持保守、平衡、激进等多种风格
- 主要参数包括 OI/市值阈值、最小OI、成交量阈值、信号强度阈值、风险评分等

## 注意事项

- 建议定期运行 `update_local_supply.py` 保持流通量数据新鲜
- 企业微信推送需配置 webhook 地址
- API有速率限制，主流程已自动分批防限流

## 许可证

MIT License 

## 定时任务与自动化

- 支持每天定时自动运行主流程，或每N小时自动运行
- 通过 `scheduler.py` 可设置定时任务、立即运行、守护进程等

### 常用命令

- 立即运行一次主流程：
  ```bash
  python scheduler.py --run-now
  ```
- 启动定时任务守护进程（每天东八区上午8点自动运行）：
  ```bash
  python scheduler.py --daemon
  ```
- 每1小时自动运行一次：
  ```bash
  python scheduler.py --daemon --every-hours 1
  ```
- 每2小时自动运行一次：
  ```bash
  python scheduler.py --daemon --every-hours 2
  ```
- 查看下次运行时间：
  ```bash
  python scheduler.py --show-next
  ```
- 日志输出：详见 `scheduler.log`，包含每次任务执行详情、推送状态、异常等

> 默认定时任务为每天东八区上午8点自动执行主流程，可用 `--every-hours` 灵活调整为每N小时自动运行。 # OI-Alert
