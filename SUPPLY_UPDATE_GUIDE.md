# 流通量更新工具使用指南

## 概述

`update_supply.py` 是币安永续合约交易信号系统的流通量数据更新工具，支持自动获取所有币种的最新流通量数据，并提供多种更新模式和详细报告。

## 主要功能

### 🔄 自动流通量更新
- **双重数据源**：优先使用CoinMarketCap API，失败时自动降级到CoinGecko
- **强制更新**：支持强制更新所有币种，不再因为"已有数据"就跳过
- **失败记录**：获取失败的币种记录为None，便于后续处理
- **自动备份**：更新前自动备份原文件
- **详细报告**：生成更新报告，记录成功和失败的币种

### 📊 数据管理
- **优先级机制**：`manual_supply.py` 优先级最高，可手动覆盖自动获取的数据
- **完整记录**：所有币种都会记录，成功获取显示数值，失败显示None
- **格式统一**：Python字典格式，便于维护和编辑

## 使用方法

### 基本命令格式
```bash
python3 update_supply.py [选项] [参数]
```

### 常用命令

#### 1. 强制更新所有币种（推荐）
```bash
python3 update_supply.py --force-all --save
```
- **功能**：强制更新所有币种的流通量，包括已有数据的币种
- **适用场景**：定期更新，确保数据最新
- **特点**：会覆盖现有数据，获取最新的流通量信息

#### 2. 只更新新币种
```bash
python3 update_supply.py --new --save
```
- **功能**：只更新没有流通量数据的币种
- **适用场景**：新增币种时使用
- **特点**：不会覆盖已有数据，只补充缺失数据

#### 3. 更新指定币种
```bash
python3 update_supply.py --symbols BTC ETH BNB --force --save
```
- **功能**：更新指定币种的流通量
- **适用场景**：需要更新特定币种时
- **特点**：精确控制，只更新需要的币种

#### 4. 更新所有币种（包括已有数据的）
```bash
python3 update_supply.py --all --force --save
```
- **功能**：更新所有币种，包括已有数据的
- **适用场景**：与 `--force-all` 类似，但会包含 `manual_supply.py` 中的币种

### 命令行选项说明

| 选项 | 说明 | 示例 |
|------|------|------|
| `--force-all` | 强制更新所有币种的流通量 | `--force-all --save` |
| `--new` | 只更新新币种的流通量 | `--new --save` |
| `--all` | 更新所有币种的流通量 | `--all --force --save` |
| `--symbols` | 指定要更新的币种列表 | `--symbols BTC ETH BNB` |
| `--force` | 强制更新，覆盖现有数据 | `--force` |
| `--save` | 保存到manual_supply.py文件 | `--save` |

## 数据源说明

### CoinMarketCap API（优先）
- **优势**：数据准确可靠，支持更多币种
- **要求**：需要API Key（推荐配置）
- **配置**：在 `.env` 文件中设置 `COINMARKETCAP_API_KEY`

### CoinGecko API（备用）
- **优势**：免费使用，无需API Key
- **特点**：当CoinMarketCap失败时自动使用
- **限制**：部分币种可能无法获取

## 输出文件

### 1. manual_supply.py - 主要数据文件
```python
MANUAL_SUPPLY = {
    'BTC': 19891356,        # 成功获取
    'ETH': 120715200,       # 成功获取
    '1MBABYDOGE': None,     # 获取失败
    'TESTFAIL': None,       # 获取失败
}
```

### 2. supply_update_report.json - 更新报告
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

### 3. manual_supply_backup_YYYYMMDD_HHMMSS.py - 备份文件
- **位置**：项目根目录
- **命名**：包含时间戳，如 `manual_supply_backup_20250712_230103.py`
- **作用**：每次更新前自动备份原文件

## 使用建议

### 定期更新策略
1. **每日更新**：`python3 update_supply.py --force-all --save`
2. **新币种更新**：`python3 update_supply.py --new --save`
3. **重要币种更新**：`python3 update_supply.py --symbols BTC ETH BNB --force --save`

### 错误处理
1. **查看失败币种**：检查 `supply_update_report.json` 中的 `failed_symbols`
2. **手动补充**：在 `manual_supply.py` 中手动设置失败的币种
3. **重新尝试**：过一段时间后重新运行更新工具

### 性能优化
1. **分批更新**：对于大量币种，可以分批更新避免API限制
2. **网络稳定**：确保网络连接稳定，避免请求超时
3. **API限制**：工具已内置1秒延迟，避免触发API限制

## 常见问题

### Q: 为什么有些币种获取失败？
A: 可能原因：
- 币种名称在数据源中不存在
- API返回数据格式异常
- 网络连接问题
- API限制或错误

### Q: 失败的币种如何处理？
A: 建议：
1. 检查币种名称是否正确
2. 手动在 `manual_supply.py` 中设置流通量
3. 等待一段时间后重新尝试
4. 使用其他数据源验证

### Q: 如何恢复备份文件？
A: 方法：
1. 找到对应的备份文件
2. 复制备份文件内容到 `manual_supply.py`
3. 或重命名备份文件为 `manual_supply.py`

### Q: 更新过程被中断怎么办？
A: 处理：
1. 检查 `supply_update_report.json` 了解已更新的币种
2. 重新运行更新命令
3. 工具会自动跳过已成功更新的币种

## 最佳实践

1. **定期更新**：建议每周至少更新一次流通量数据
2. **备份重要数据**：更新前确保重要数据已备份
3. **监控失败率**：关注失败币种数量，及时处理
4. **验证数据**：对重要币种的数据进行交叉验证
5. **记录更新日志**：记录每次更新的时间和结果

## 技术支持

如果遇到问题：
1. 检查网络连接
2. 验证API Key配置
3. 查看控制台错误信息
4. 检查更新报告文件
5. 尝试手动设置失败的币种 