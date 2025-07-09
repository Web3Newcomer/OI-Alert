#!/usr/bin/env python3
"""
快速测试 CoinMarketCap API 更新功能
"""
import requests
import time
from config import Config

# CoinMarketCap API 配置
COINMARKETCAP_API_KEY = Config.COINMARKETCAP_API_KEY
COINMARKETCAP_BASE_URL = 'https://pro-api.coinmarketcap.com/v1'

def get_supply_coinmarketcap(symbol):
    """获取单个币种流通量（CoinMarketCap）"""
    if not COINMARKETCAP_API_KEY:
        return None
    
    try:
        url = f'{COINMARKETCAP_BASE_URL}/cryptocurrency/quotes/latest'
        headers = {
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
            'Accept': 'application/json'
        }
        params = {
            'symbol': symbol,
            'convert': 'USD'
        }
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and symbol in data['data']:
                circ = data['data'][symbol].get('circulating_supply')
                return int(circ) if circ else None
        return None
    except Exception as e:
        print(f"CoinMarketCap 获取 {symbol} 异常: {e}")
        return None

def test_quick_update():
    """快速测试更新功能"""
    print("=" * 50)
    print("快速测试 CoinMarketCap API 更新")
    print("=" * 50)
    
    print(f"API Key: {COINMARKETCAP_API_KEY[:10]}...{COINMARKETCAP_API_KEY[-4:]}")
    
    # 测试几个币种
    test_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL']
    results = {}
    
    for symbol in test_symbols:
        print(f"获取 {symbol} 流通量...")
        supply = get_supply_coinmarketcap(symbol)
        if supply:
            print(f"✅ {symbol}: {supply:,}")
            results[symbol] = supply
        else:
            print(f"❌ {symbol}: 获取失败")
            results[symbol] = None
        time.sleep(0.5)
    
    # 写入测试文件
    with open('test_supply.py', 'w', encoding='utf-8') as f:
        f.write('TEST_SUPPLY = {\n')
        for symbol, supply in results.items():
            f.write(f"    '{symbol}': {supply if supply is not None else 'None'},\n")
        f.write('}\n')
    
    print(f"\n✅ 测试完成！结果已写入 test_supply.py")
    print(f"成功获取: {sum(1 for v in results.values() if v is not None)}/{len(results)} 个币种")

if __name__ == '__main__':
    test_quick_update() 