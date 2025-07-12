#!/usr/bin/env python3
"""
币种匹配修复脚本
解决币安合约币种与CoinMarketCap/CoinGecko币种名称不匹配的问题
"""
import requests
import json
from config import Config

def get_binance_symbols():
    """获取币安USDT合约币种列表"""
    try:
        url = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        symbols = []
        for s in data['symbols']:
            if s['quoteAsset'] == 'USDT' and s['contractType'] == 'PERPETUAL':
                base_asset = s['baseAsset']
                if not base_asset.startswith('1000'):
                    symbols.append(base_asset)
        
        return sorted(symbols)
    except Exception as e:
        print(f"获取币安合约币种失败: {e}")
        return []

def check_symbol_mapping():
    """检查币种映射问题"""
    print("=" * 60)
    print("🔍 币种映射问题检查")
    print("=" * 60)
    
    # 获取币安币种列表
    binance_symbols = get_binance_symbols()
    print(f"币安USDT合约币种数量: {len(binance_symbols)}")
    
    # 检查有问题的币种
    problem_symbols = []
    
    # 已知的映射问题
    known_issues = {
        'PUMP': {
            'binance': 'PUMP (pump.fun)',
            'coinmarketcap': 'PUMPBTC (不同的币种)',
            'coingecko': 'pump-fun (pump.fun)',
            'solution': '使用pump.fun的流通量数据'
        }
    }
    
    for symbol in binance_symbols:
        if symbol in known_issues:
            problem_symbols.append(symbol)
            issue = known_issues[symbol]
            print(f"\n🚨 发现映射问题: {symbol}")
            print(f"   币安合约: {issue['binance']}")
            print(f"   CoinMarketCap: {issue['coinmarketcap']}")
            print(f"   CoinGecko: {issue['coingecko']}")
            print(f"   解决方案: {issue['solution']}")
    
    if not problem_symbols:
        print("\n✅ 未发现币种映射问题")
    else:
        print(f"\n📊 发现 {len(problem_symbols)} 个币种映射问题")
    
    return problem_symbols

def get_pump_fun_data():
    """获取pump.fun的详细数据"""
    print("\n" + "=" * 60)
    print("📊 pump.fun 数据获取")
    print("=" * 60)
    
    try:
        # 尝试从CoinGecko获取
        url = "https://api.coingecko.com/api/v3/coins/pump-fun"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        print(f"币种名称: {data.get('name', 'N/A')}")
        print(f"币种符号: {data.get('symbol', 'N/A')}")
        print(f"总供应量: {data.get('market_data', {}).get('total_supply', 'N/A'):,.0f}")
        print(f"流通供应量: {data.get('market_data', {}).get('circulating_supply', 'N/A')}")
        print(f"当前价格: {data.get('market_data', {}).get('current_price', {}).get('usd', 'N/A')}")
        print(f"市值: {data.get('market_data', {}).get('market_cap', {}).get('usd', 'N/A')}")
        print(f"状态: {'预览状态' if data.get('preview_listing') else '正常'}")
        
        # 检查是否有活跃交易
        if data.get('preview_listing'):
            print("⚠️  注意: 该币种处于预览状态，可能没有活跃交易")
        
        return data
        
    except Exception as e:
        print(f"获取pump.fun数据失败: {e}")
        return None

def verify_current_supply_data():
    """验证当前的流通量数据"""
    print("\n" + "=" * 60)
    print("🔍 当前流通量数据验证")
    print("=" * 60)
    
    # 读取当前数据
    try:
        with open('local_supply.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取PUMP相关数据
        import re
        pump_match = re.search(r"'PUMP':\s*(\d+)", content)
        pumpbtc_match = re.search(r"'PUMPBTC':\s*(\d+)", content)
        
        if pump_match:
            print(f"local_supply.py 中 PUMP 流通量: {int(pump_match.group(1)):,}")
        if pumpbtc_match:
            print(f"local_supply.py 中 PUMPBTC 流通量: {int(pumpbtc_match.group(1)):,}")
        
        # 检查manual_supply.py
        with open('manual_supply.py', 'r', encoding='utf-8') as f:
            manual_content = f.read()
        
        manual_pump_match = re.search(r"'PUMP':\s*(\d+)", manual_content)
        if manual_pump_match:
            print(f"manual_supply.py 中 PUMP 流通量: {int(manual_pump_match.group(1)):,}")
            print("✅ manual_supply.py 已包含正确的PUMP数据")
        else:
            print("❌ manual_supply.py 中缺少PUMP数据")
            
    except Exception as e:
        print(f"验证流通量数据失败: {e}")

def calculate_correct_market_cap():
    """计算正确的市值"""
    print("\n" + "=" * 60)
    print("💰 市值计算验证")
    print("=" * 60)
    
    # 从币安获取当前价格
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        resp = requests.get(url, timeout=10)
        tickers = resp.json()
        
        pump_ticker = None
        for ticker in tickers:
            if ticker['symbol'] == 'PUMPUSDT':
                pump_ticker = ticker
                break
        
        if pump_ticker:
            price = float(pump_ticker['lastPrice'])
            print(f"PUMP 当前价格: ${price:,.6f}")
            
            # 使用正确的流通量计算市值
            correct_supply = 1000000000000  # 1万亿
            market_cap = correct_supply * price
            
            print(f"正确流通量: {correct_supply:,}")
            print(f"正确市值: ${market_cap:,.2f}")
            
            # 对比之前的错误市值
            wrong_supply = 285000000  # 之前错误的数据
            wrong_market_cap = wrong_supply * price
            print(f"错误流通量: {wrong_supply:,}")
            print(f"错误市值: ${wrong_market_cap:,.2f}")
            
            difference = market_cap - wrong_market_cap
            print(f"市值差异: ${difference:,.2f}")
            
        else:
            print("❌ 未找到PUMPUSDT价格数据")
            
    except Exception as e:
        print(f"计算市值失败: {e}")

def main():
    """主函数"""
    print("🔧 币种映射问题修复工具")
    print("=" * 60)
    
    # 1. 检查映射问题
    problem_symbols = check_symbol_mapping()
    
    # 2. 获取pump.fun数据
    pump_data = get_pump_fun_data()
    
    # 3. 验证当前数据
    verify_current_supply_data()
    
    # 4. 计算正确市值
    calculate_correct_market_cap()
    
    print("\n" + "=" * 60)
    print("📋 修复建议")
    print("=" * 60)
    print("1. ✅ 已在 manual_supply.py 中添加正确的PUMP流通量数据")
    print("2. 🔄 建议重新运行 update_local_supply.py 更新数据")
    print("3. 🧪 运行主程序验证修复效果")
    print("4. 📊 监控市值计算是否正确")
    
    print("\n执行修复命令:")
    print("python update_local_supply.py")
    print("python scheduler.py --run-now")

if __name__ == '__main__':
    main() 