#!/usr/bin/env python3
"""
限制数量的流通量更新测试
只处理前20个币种，快速验证完整流程
"""
import requests
import time
import random
from config import Config

BINANCE_FUTURES_URL = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
BATCH_SIZE = 5
BASE_SLEEP = 1
MAX_RETRIES = 3

# CoinMarketCap API 配置
COINMARKETCAP_API_KEY = Config.COINMARKETCAP_API_KEY
COINMARKETCAP_BASE_URL = 'https://pro-api.coinmarketcap.com/v1'

def get_binance_usdt_symbols():
    """获取币安USDT合约币种列表（限制数量）"""
    try:
        resp = requests.get(BINANCE_FUTURES_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        symbols = set()
        for s in data['symbols']:
            if s['quoteAsset'] == 'USDT' and s['contractType'] == 'PERPETUAL':
                base_asset = s['baseAsset']
                # 跳过1000开头的特殊币种
                if not base_asset.startswith('1000'):
                    symbols.add(base_asset)
        # 只取前20个币种
        return sorted(list(symbols))[:20]
    except Exception as e:
        print(f"获取币安合约币种失败: {e}")
        return []

def get_supply_coinmarketcap(symbol):
    """获取单个币种流通量（CoinMarketCap）"""
    if not COINMARKETCAP_API_KEY:
        return None
    
    for attempt in range(MAX_RETRIES):
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
                else:
                    return None
            elif resp.status_code == 429:
                delay = 30 + random.uniform(0, 10)
                print(f"CoinMarketCap 限流，等待{delay:.1f}s后重试 {symbol}")
                time.sleep(delay)
            else:
                print(f"CoinMarketCap 获取 {symbol} 流通量失败: {resp.status_code}")
                return None
        except Exception as e:
            delay = BASE_SLEEP * (2 ** attempt) + random.uniform(0, 1)
            print(f"CoinMarketCap 获取 {symbol} 流通量异常: {e}，等待{delay:.1f}s重试")
            time.sleep(delay)
    return None

def get_supply_single(symbol):
    """获取单个币种流通量（优先 CoinMarketCap）"""
    # 首先尝试 CoinMarketCap
    if COINMARKETCAP_API_KEY:
        print(f"优先使用 CoinMarketCap 获取 {symbol} 流通量...")
        coinmarketcap_supply = get_supply_coinmarketcap(symbol)
        if coinmarketcap_supply:
            print(f"CoinMarketCap 成功获取 {symbol} 流通量: {coinmarketcap_supply}")
            return coinmarketcap_supply
        else:
            print(f"CoinMarketCap 获取 {symbol} 失败")
    
    print(f"所有数据源都无法获取 {symbol} 流通量")
    return None

def get_circulating_supply(symbols):
    """分批获取流通量数据"""
    supply = {}
    total = len(symbols)
    batch_idx = 0
    while batch_idx * BATCH_SIZE < total:
        batch = symbols[batch_idx*BATCH_SIZE:(batch_idx+1)*BATCH_SIZE]
        print(f"处理第{batch_idx+1}批，共{len(batch)}个币种...")
        for symbol in batch:
            try:
                supply[symbol] = get_supply_single(symbol)
                time.sleep(0.5)
            except Exception as e:
                print(f"处理 {symbol} 时出错: {e}")
                supply[symbol] = None
        batch_idx += 1
        if batch_idx * BATCH_SIZE < total:
            print(f"批次间隔 10.0s...")
            time.sleep(10)
    return supply

def write_local_supply(supply):
    """写入local_supply.py"""
    with open('local_supply_test.py', 'w', encoding='utf-8') as f:
        f.write('COIN_SUPPLY = {\n')
        for k, v in supply.items():
            f.write(f"    '{k}': {v if v is not None else 'None'},\n")
        f.write('}\n')

if __name__ == '__main__':
    print('=' * 60)
    print('限制数量流通量更新测试（前20个币种）')
    print('=' * 60)
    
    print(f'CoinMarketCap API Key: {COINMARKETCAP_API_KEY[:10]}...{COINMARKETCAP_API_KEY[-4:] if COINMARKETCAP_API_KEY else "未配置"}')
    print(f'优先使用 CoinMarketCap: {"是" if COINMARKETCAP_API_KEY else "否"}')
    print()
    
    print('获取币安USDT合约币种列表...')
    symbols = get_binance_usdt_symbols()
    print(f'共获取 {len(symbols)} 个币种（前20个，已跳过1000开头的特殊币种）')
    print('分批获取流通量数据...')
    auto_supply = get_circulating_supply(symbols)
    print('写入local_supply_test.py...')
    write_local_supply(auto_supply)
    print('✅ 测试完成！结果已写入 local_supply_test.py')
    
    # 统计结果
    success_count = sum(1 for v in auto_supply.values() if v is not None)
    print(f'成功获取: {success_count}/{len(symbols)} 个币种') 