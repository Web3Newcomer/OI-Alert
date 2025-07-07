import requests
import time
import random
from manual_supply import MANUAL_SUPPLY

BINANCE_FUTURES_URL = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
BATCH_SIZE = 10
BASE_SLEEP = 3
MAX_RETRIES = 5

# 获取币安USDT合约币种列表
def get_binance_usdt_symbols():
    try:
        resp = requests.get(BINANCE_FUTURES_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        symbols = set()
        for s in data['symbols']:
            if s['quoteAsset'] == 'USDT' and s['contractType'] == 'PERPETUAL':
                symbols.add(s['baseAsset'])
        return sorted(list(symbols))
    except Exception as e:
        print(f"获取币安合约币种失败: {e}")
        return []

# 获取单个币种流通量，带重试
def get_supply_single(symbol):
    for attempt in range(MAX_RETRIES):
        try:
            url = f'https://api.coingecko.com/api/v3/coins/{symbol.lower()}'
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                circ = data.get('market_data', {}).get('circulating_supply')
                return int(circ) if circ else None
            elif resp.status_code == 429:
                # 单币种限流，直接抛出信号让批次处理
                raise RuntimeError('RATE_LIMIT')
            elif resp.status_code >= 500:
                delay = BASE_SLEEP * (2 ** attempt) + random.uniform(0, 2)
                print(f"5xx错误，等待{delay:.1f}s后重试 {symbol}")
                time.sleep(delay)
            else:
                print(f"获取 {symbol} 流通量失败: {resp.status_code}")
                return None
        except RuntimeError as e:
            if str(e) == 'RATE_LIMIT':
                raise  # 让外层批次处理
            delay = BASE_SLEEP * (2 ** attempt) + random.uniform(0, 2)
            print(f"获取 {symbol} 流通量异常: {e}，等待{delay:.1f}s重试")
            time.sleep(delay)
        except Exception as e:
            delay = BASE_SLEEP * (2 ** attempt) + random.uniform(0, 2)
            print(f"获取 {symbol} 流通量异常: {e}，等待{delay:.1f}s重试")
            time.sleep(delay)
    return None

# 分批获取Coingecko流通量
def get_circulating_supply(symbols):
    supply = {}
    total = len(symbols)
    batch_idx = 0
    while batch_idx * BATCH_SIZE < total:
        batch = symbols[batch_idx*BATCH_SIZE:(batch_idx+1)*BATCH_SIZE]
        print(f"处理第{batch_idx+1}批，共{len(batch)}个币种...")
        rate_limited = False
        for symbol in batch:
            try:
                supply[symbol] = get_supply_single(symbol)
                time.sleep(1.5)
            except RuntimeError as e:
                if str(e) == 'RATE_LIMIT':
                    print(f"批次遇到429限流，等待60秒后继续...")
                    rate_limited = True
                    break
        if rate_limited:
            time.sleep(60)
            continue  # 重新处理本批
        batch_idx += 1
        if batch_idx * BATCH_SIZE < total:
            print(f"批次间隔 60.0s...")
            time.sleep(60)
    return supply

# 合并manual_supply优先
def merge_manual_supply(auto_supply):
    merged = auto_supply.copy()
    for k, v in MANUAL_SUPPLY.items():
        if v is not None:
            merged[k] = v
    return merged

# 写入local_supply.py
def write_local_supply(supply):
    with open('local_supply.py', 'w', encoding='utf-8') as f:
        f.write('COIN_SUPPLY = {\n')
        for k, v in supply.items():
            f.write(f"    '{k}': {v if v is not None else 'None'},\n")
        f.write('}\n')

if __name__ == '__main__':
    print('获取币安USDT合约币种列表...')
    symbols = get_binance_usdt_symbols()
    print(f'共获取 {len(symbols)} 个币种')
    print('分批获取Coingecko流通量...')
    auto_supply = get_circulating_supply(symbols)
    print('合并manual_supply优先...')
    merged_supply = merge_manual_supply(auto_supply)
    print('写入local_supply.py...')
    write_local_supply(merged_supply)
    print('✅ 更新完成！') 