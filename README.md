# 币安永续合约交易信号系统

本项目为币安永续合约量化信号自动分析与推送系统，支持本地流通量维护、自动采集行情、信号分析、企业微信推送等全流程。

## 功能特性

- 自动获取币安USDT合约所有币种的最新行情、资金费率、未平仓合约、24h涨跌幅等
- **动态币种列表更新**：自动检测无效币种，添加新币种，保持与币安API同步
- **智能流通量管理**：支持本地流通量维护，manual_supply.py 可手动优先覆盖
- **优先使用 CoinMarketCap API**，Coingecko 作为备用数据源，大幅提高流通量数据获取成功率
- **OI历史数据收集**：每4小时自动收集OI数据，支持历史分析和异常检测
- 只分析成交量前N（如100）币种，自动过滤冷门币
- 市值、OI/市值、资金费率、风险评分等多维信号分析
- **双重警报机制**：OI市值警报（买入信号）+ OI异常警报（市场异常警告）
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

3. **币种列表与流通量管理**
   - 系统会自动维护币种列表，无需手动操作
   - 如需手动更新：`python update_symbols.py --update`
   - 在 `manual_supply.py` 填写需手动覆盖的币种流通量

4. 一键运行主流程
```bash
python scheduler.py --run-now
```

## 核心功能详解

### 🔄 动态币种更新机制

#### **自动更新流程**
- **触发时机**：每次运行主程序时自动执行
- **更新内容**：
  - 移除无效币种（API返回400错误的币种）
  - 添加新币种（币安新增的永续合约）
  - 保持流通量数据完整性
- **缓存机制**：24小时缓存，避免重复API调用

#### **手动更新工具**
```bash
# 更新币种列表和流通量数据
python update_symbols.py --update

# 只获取有效币种列表
python update_symbols.py --get-valid
```

#### **更新示例**
```
币种列表更新报告
==================================================
更新前币种数量: 484
更新后币种数量: 449
移除的币种 (42): ['AGIX', 'ALPACA', 'AMB', 'BNX', 'FTM', 'LINA', 'OCEAN', 'STRAX', 'VIDT', 'WAVES', ...]
新增的币种 (7): ['1000SHIB', '1000PEPE', '1000BONK', '1000X', 'TANSSI', 'CROSS', 'AIN']
```

### 📊 流通量数据管理

#### **数据来源优先级**
1. **manual_supply.py** - 手动设置的流通量（优先级最高）
2. **local_supply.py** - 自动获取的流通量（优先级较低）

#### **流通量合并逻辑**
```python
def get_final_supply():
    """manual_supply.py 有值优先，否则用 local_supply.py"""
    supply = COIN_SUPPLY.copy()  # 从 local_supply.py 复制
    for k, v in MANUAL_SUPPLY.items():
        if v is not None:
            supply[k] = v  # manual_supply.py 有值则覆盖
    return supply
```

#### **币种更新时的流通量保护**
- ✅ **保留现有流通量**：更新币种列表时，保留所有现有币种的流通量数据
- ✅ **移除无效币种**：只移除API返回400错误的币种
- ✅ **添加新币种**：新币种的流通量设为None，等待后续补充

#### **流通量更新工具**

##### **自动流通量更新**
```bash
# 强制更新所有币种的流通量（推荐）
python3 update_supply.py --force-all --save

# 只更新新币种的流通量
python3 update_supply.py --new --save

# 更新指定币种的流通量
python3 update_supply.py --symbols BTC ETH BNB --force --save

# 更新所有币种（包括已有数据的）
python3 update_supply.py --all --force --save
```

##### **工具特性**
- **双重数据源**：优先使用CoinMarketCap API，失败时自动降级到CoinGecko
- **强制更新**：支持强制更新所有币种，不再因为"已有数据"就跳过
- **失败记录**：获取失败的币种记录为None，便于后续处理
- **自动备份**：更新前自动备份原文件
- **详细报告**：生成更新报告，记录成功和失败的币种

##### **更新报告示例**
```json
{
  "update_time": "2025-07-12 23:21:02",
  "total_symbols": 449,
  "updated_symbols": [
    {"symbol": "BTC", "supply": 19891356},
    {"symbol": "ETH", "supply": 120715200}
  ],
  "failed_symbols": [
    "1MBABYDOGE",
    "TESTFAIL"
  ]
}
```

##### **数据文件格式**
```python
# manual_supply.py
MANUAL_SUPPLY = {
    'BTC': 19891356,        # 成功获取
    'ETH': 120715200,       # 成功获取
    '1MBABYDOGE': None,     # 获取失败
    'TESTFAIL': None,       # 获取失败
}
```

### 📈 OI历史数据收集

#### **数据收集机制**
- **收集频率**：每4小时收集一次当前OI数据
- **存储位置**：`oi_history_data/oi_data_YYYY-MM-DD.json`
- **保留期限**：自动保留最近10天数据，超过10天的文件会被删除
- **数据格式**：每个币种包含时间戳、OI值、收集时间等信息

#### **历史数据分析**
- **OI比率计算**：最近3次4小时OI均值 / 最近10次4小时OI均值
- **异常检测**：用于OI异常警报的触发条件
- **数据积累**：随着时间推移，历史数据逐渐丰富，分析更准确

### 🚨 双重警报机制

#### **1. OI市值警报（买入信号）**
- **触发条件**：OI/市值 > 0.5 + OI > 5M + 成交量/市值 > 0.1 + 信号强度 > 60
- **用途**：寻找投资机会
- **示例**：`OI/市值警报 | OI/市值比高(0.57) | OI充足(8.4M)`

#### **2. OI异常警报（市场异常警告）**
- **触发条件**：资金费率绝对值 > 0.1% AND OI短期激增 > 2.0
- **用途**：市场异常警告，风险提示
- **示例**：`🚨OI异常警报 | 资金费率异常(0.15%) | OI激增(2.5x)`

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

### 策略配置

#### **主要参数（strategy_config.py）**
- `OI_MARKET_CAP_RATIO_THRESHOLD`：OI/市值比率阈值（默认0.5）
- `FUNDING_RATE_ABS_THRESHOLD`：资金费率绝对值阈值（默认0.001，即0.1%）
- `OI_SURGE_RATIO_THRESHOLD`：OI短期激增比率阈值（默认2.0）
- `MIN_OI_VALUE`：最小OI价值（默认5,000,000 USDT）
- `SIGNAL_STRENGTH_THRESHOLD`：信号强度阈值（默认60）

#### **策略预设**
- **保守策略**：更严格的阈值，降低风险
- **激进策略**：更宽松的阈值，提高信号数量
- **平衡策略**：标准阈值，平衡风险与收益

### 其他配置

- `TOP_VOLUME_LIMIT`：只分析成交量前N币种（默认100），可在 config.py 配置
- `manual_supply.py`：手动优先覆盖流通量，未填写则用自动采集

## 推送内容示例

企业微信推送内容如下：

```
【币安永续合约交易信号分析报告】
分析时间: 2025-07-07 15:43:49 (东八区)
分析币种: 100
买入信号: 1
卖出信号: 0
强信号: 4
平均信号强度: 55.1
平均风险评分: 29.2
🚨 OI异常警报: 0
📈 平均OI激增比率: 1.00
💰 平均资金费率绝对值: 0.039%

【推荐买入信号】
1. MYX  价格: $0.1200  市值: $14.7M  信号强度: 91.9/100  风险: 23.5/100  OI/市值: 0.57  资金费率: 0.23%  24h涨跌: +0.23%
 描述: OI/市值警报 | OI/市值比高(0.57) | OI充足(8.4M)

【OI异常警报信号】
暂无OI异常警报信号
```

## 数据字段说明

- `symbol`: 交易对符号
- `price`: 当前价格
- `quote_volume_24h`: 24小时成交额（USDT）
- `open_interest_value`: 未平仓合约价值
- `funding_rate`: 资金费率
- `price_change_percent_24h`: 24小时价格变化百分比（小数）
- `market_cap_estimate`: 市值估算
- `oi_surge_ratio`: OI短期激增比率
- `funding_rate_abs`: 资金费率绝对值

## 定时任务与自动化

- 支持每天定时自动运行主流程，或每N小时自动运行
- **新增：按币安资金费率结算时间自动运行（每8小时一次）**
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
- **按币安资金费率结算时间运行（推荐）**：
  ```bash
  python scheduler.py --daemon --funding-rate
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
- 查看资金费率调度下次运行时间：
  ```bash
  python scheduler.py --show-next --funding-rate
  ```

### 资金费率结算时间

币安永续合约资金费率每8小时结算一次：

| UTC时间 | 东八区时间 | 说明 |
|---------|------------|------|
| 00:00 | 08:00 | 上午结算 |
| 08:00 | 16:00 | 下午结算 |
| 16:00 | 00:00 (次日) | 夜间结算 |

> **推荐使用 `--funding-rate` 模式**，在每次资金费率结算后立即分析市场信号，确保及时捕捉市场变化。

## 文件结构说明

### 核心程序文件
- `scheduler.py` - 主调度器，支持定时任务和立即运行
- `trading_signal_analyzer.py` - 交易信号分析器，包含双重警报机制
- `oi_history_collector.py` - OI历史数据收集器
- `wechat_notifier.py` - 企业微信通知器
- `update_symbols.py` - 币种列表更新工具
- `update_supply.py` - 流通量数据更新工具

### 配置文件
- `config.py` - 基础配置文件
- `strategy_config.py` - 策略参数配置
- `local_supply.py` - 自动获取的流通量数据
- `manual_supply.py` - 手动设置的流通量数据

### 数据文件
- `oi_history_data/` - OI历史数据存储目录
- `valid_symbols_cache.json` - 有效币种缓存
- `oi_history_cache.json` - OI历史数据缓存

### 文档文件
- `README.md` - 项目说明文档
- `QUICK_START.md` - 快速开始指南
- `SUPPLY_UPDATE_GUIDE.md` - 流通量更新工具使用指南
- `PROJECT_CLEANUP.md` - 项目清理说明
- `LOCAL_DATA_SYSTEM.md` - 本地数据系统说明

## 注意事项

- **币种列表自动更新**：系统会自动维护币种列表，无需手动干预
- **流通量数据保护**：更新币种列表时会保留现有流通量数据
- **OI历史数据积累**：历史数据需要时间积累，初期OI比率可能不准确
- **企业微信推送**：需配置 webhook 地址
- **API速率限制**：主流程已自动分批防限流
- **日志监控**：建议定期查看日志，了解系统运行状态

## 许可证

MIT License
