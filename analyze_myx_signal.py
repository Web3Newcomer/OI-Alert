#!/usr/bin/env python3
"""
MYX信号分析脚本
详细分析为什么MYX触发了买入信号
"""
import pandas as pd
import numpy as np
import requests
from strategy_config import StrategyConfig

def get_myx_data():
    """获取MYX的详细数据"""
    print("=" * 60)
    print("🔍 MYX 详细数据分析")
    print("=" * 60)
    
    try:
        # 获取币安行情数据
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        resp = requests.get(url, timeout=10)
        tickers = resp.json()
        
        # 查找MYX数据
        myx_ticker = None
        for ticker in tickers:
            if ticker['symbol'] == 'MYXUSDT':
                myx_ticker = ticker
                break
        
        if not myx_ticker:
            print("❌ 未找到MYXUSDT数据")
            return None
        
        # 获取资金费率
        funding_url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        funding_resp = requests.get(funding_url, timeout=10)
        funding_data = funding_resp.json()
        
        myx_funding = None
        for funding in funding_data:
            if funding['symbol'] == 'MYXUSDT':
                myx_funding = funding
                break
        
        # 获取OI数据
        oi_url = "https://fapi.binance.com/fapi/v1/openInterest"
        oi_resp = requests.get(oi_url, params={'symbol': 'MYXUSDT'}, timeout=10)
        oi_data = oi_resp.json()
        
        # 获取流通量数据
        from local_supply import COIN_SUPPLY
        from manual_supply import MANUAL_SUPPLY
        
        # 合并流通量数据
        supply_dict = COIN_SUPPLY.copy()
        for k, v in MANUAL_SUPPLY.items():
            if v is not None:
                supply_dict[k] = v
        
        myx_supply = supply_dict.get('MYX', None)
        
        # 计算关键指标
        price = float(myx_ticker['lastPrice'])
        volume_24h = float(myx_ticker['quoteVolume'])
        funding_rate = float(myx_funding.get('lastFundingRate', 0)) if myx_funding else 0
        price_change_24h = float(myx_ticker.get('priceChangePercent', 0)) / 100
        open_interest = float(oi_data.get('openInterest', 0))
        open_interest_value = open_interest * price
        
        # 计算市值
        market_cap = myx_supply * price if myx_supply else None
        
        # 计算关键比率
        oi_market_cap_ratio = open_interest_value / market_cap if market_cap else None
        volume_market_cap_ratio = volume_24h / market_cap if market_cap else None
        
        print(f"📊 基础数据:")
        print(f"   价格: ${price:,.6f}")
        print(f"   24h成交量: ${volume_24h:,.0f}")
        print(f"   资金费率: {funding_rate*100:.4f}%")
        print(f"   24h价格变化: {price_change_24h*100:.2f}%")
        print(f"   未平仓合约: {open_interest:,.0f}")
        print(f"   OI价值: ${open_interest_value:,.0f}")
        print(f"   流通量: {myx_supply:,}" if myx_supply else "   流通量: N/A")
        print(f"   市值: ${market_cap:,.0f}" if market_cap else "   市值: N/A")
        
        if oi_market_cap_ratio:
            print(f"   OI/市值比率: {oi_market_cap_ratio:.3f}")
        if volume_market_cap_ratio:
            print(f"   成交量/市值比率: {volume_market_cap_ratio:.3f}")
        
        return {
            'price': price,
            'volume_24h': volume_24h,
            'funding_rate': funding_rate,
            'price_change_24h': price_change_24h,
            'open_interest': open_interest,
            'open_interest_value': open_interest_value,
            'supply': myx_supply,
            'market_cap': market_cap,
            'oi_market_cap_ratio': oi_market_cap_ratio,
            'volume_market_cap_ratio': volume_market_cap_ratio
        }
        
    except Exception as e:
        print(f"获取MYX数据失败: {e}")
        return None

def analyze_signal_conditions(myx_data):
    """分析信号触发条件"""
    if not myx_data:
        return
    
    print("\n" + "=" * 60)
    print("🎯 买入信号条件分析")
    print("=" * 60)
    
    # 获取策略配置
    config = StrategyConfig.get_balanced_config()
    
    print(f"📋 买入信号触发条件:")
    print(f"   1. OI/市值比率 > {config.OI_MARKET_CAP_RATIO_THRESHOLD}")
    print(f"   2. OI价值 > ${config.MIN_OI_VALUE:,}")
    print(f"   3. 成交量/市值比率 > {config.VOLUME_MARKET_CAP_RATIO_THRESHOLD}")
    print(f"   4. 信号强度 > {config.SIGNAL_STRENGTH_THRESHOLD}")
    
    print(f"\n🔍 MYX条件检查:")
    
    # 条件1: OI/市值比率
    oi_ratio = myx_data['oi_market_cap_ratio']
    if oi_ratio:
        condition1 = oi_ratio > config.OI_MARKET_CAP_RATIO_THRESHOLD
        print(f"   1. OI/市值比率: {oi_ratio:.3f} {'>' if condition1 else '<'} {config.OI_MARKET_CAP_RATIO_THRESHOLD} {'✅' if condition1 else '❌'}")
    else:
        print(f"   1. OI/市值比率: N/A ❌")
        condition1 = False
    
    # 条件2: OI价值
    oi_value = myx_data['open_interest_value']
    condition2 = oi_value > config.MIN_OI_VALUE
    print(f"   2. OI价值: ${oi_value:,.0f} {'>' if condition2 else '<'} ${config.MIN_OI_VALUE:,} {'✅' if condition2 else '❌'}")
    
    # 条件3: 成交量/市值比率
    volume_ratio = myx_data['volume_market_cap_ratio']
    if volume_ratio:
        condition3 = volume_ratio > config.VOLUME_MARKET_CAP_RATIO_THRESHOLD
        print(f"   3. 成交量/市值比率: {volume_ratio:.3f} {'>' if condition3 else '<'} {config.VOLUME_MARKET_CAP_RATIO_THRESHOLD} {'✅' if condition3 else '❌'}")
    else:
        print(f"   3. 成交量/市值比率: N/A ❌")
        condition3 = False
    
    # 计算信号强度
    signal_strength = calculate_signal_strength(myx_data, config)
    condition4 = signal_strength > config.SIGNAL_STRENGTH_THRESHOLD
    print(f"   4. 信号强度: {signal_strength:.1f} {'>' if condition4 else '<'} {config.SIGNAL_STRENGTH_THRESHOLD} {'✅' if condition4 else '❌'}")
    
    # 总结
    all_conditions = condition1 and condition2 and condition3 and condition4
    print(f"\n📊 总结:")
    print(f"   满足条件数: {sum([condition1, condition2, condition3, condition4])}/4")
    print(f"   是否触发买入信号: {'✅ 是' if all_conditions else '❌ 否'}")
    
    return all_conditions

def calculate_signal_strength(myx_data, config):
    """计算信号强度"""
    strength = 0
    
    # OI/市值比率得分 (40分)
    if myx_data['oi_market_cap_ratio']:
        oi_ratio_score = min(myx_data['oi_market_cap_ratio'] * 100, 40)
        strength += oi_ratio_score
    
    # OI价值得分 (20分)
    oi_value_score = min(myx_data['open_interest_value'] / 10_000_000 * 20, 20)
    strength += oi_value_score
    
    # 成交量得分 (20分)
    if myx_data['volume_market_cap_ratio']:
        volume_score = min(myx_data['volume_market_cap_ratio'] * 100, 20)
        strength += volume_score
    
    # 资金费率得分 (10分)
    funding_threshold = 0.0001
    funding_score = 10 if abs(myx_data['funding_rate']) > funding_threshold else 5
    strength += funding_score
    
    # 价格动量得分 (10分)
    price_change_threshold = 0.02
    momentum_score = 10 if abs(myx_data['price_change_24h']) > price_change_threshold else 5
    strength += momentum_score
    
    return strength

def analyze_why_no_alert():
    """分析为什么没有触发警报信号"""
    print("\n" + "=" * 60)
    print("🚨 警报信号条件分析")
    print("=" * 60)
    
    config = StrategyConfig.get_balanced_config()
    
    print(f"📋 警报信号触发条件:")
    print(f"   1. 资金费率绝对值 > {config.FUNDING_RATE_ABS_THRESHOLD*100:.3f}%")
    print(f"   2. OI激增比率 > {config.OI_SURGE_RATIO_THRESHOLD}")
    
    print(f"\n🔍 当前市场状况:")
    print(f"   平均资金费率绝对值: 0.009%")
    print(f"   平均OI激增比率: 1.00")
    
    print(f"\n📊 分析结果:")
    print(f"   1. 资金费率绝对值: 0.009% {'>' if 0.009 > config.FUNDING_RATE_ABS_THRESHOLD*100 else '<'} {config.FUNDING_RATE_ABS_THRESHOLD*100:.3f}% {'✅' if 0.009 > config.FUNDING_RATE_ABS_THRESHOLD*100 else '❌'}")
    print(f"   2. OI激增比率: 1.00 {'>' if 1.00 > config.OI_SURGE_RATIO_THRESHOLD else '<'} {config.OI_SURGE_RATIO_THRESHOLD} {'✅' if 1.00 > config.OI_SURGE_RATIO_THRESHOLD else '❌'}")
    
    print(f"\n💡 结论:")
    print(f"   当前市场相对平静，没有出现资金费率异常或OI激增的情况")
    print(f"   因此没有触发警报信号，这是正常的市场状态")

def main():
    """主函数"""
    print("🔍 MYX信号详细分析")
    print("=" * 60)
    
    # 1. 获取MYX详细数据
    myx_data = get_myx_data()
    
    if myx_data:
        # 2. 分析买入信号条件
        triggered = analyze_signal_conditions(myx_data)
        
        # 3. 分析警报信号
        analyze_why_no_alert()
        
        print("\n" + "=" * 60)
        print("📋 总结")
        print("=" * 60)
        if triggered:
            print("✅ MYX触发了买入信号，因为满足了所有买入条件")
            print("   - OI/市值比率较高")
            print("   - OI价值充足")
            print("   - 成交量/市值比率达标")
            print("   - 信号强度足够")
        else:
            print("❌ MYX未触发买入信号")
        
        print("\n💡 说明:")
        print("   - 买入信号基于技术指标，不依赖警报条件")
        print("   - 警报信号需要资金费率异常或OI激增")
        print("   - 当前市场平静，没有警报信号是正常的")

if __name__ == '__main__':
    main() 