#!/usr/bin/env python3
"""
CoinMarketCap API 测试脚本
用于验证 API Key 和测试数据获取功能
"""
import requests
import time
import os
from config import Config

# CoinMarketCap API 配置
COINMARKETCAP_API_KEY = Config.COINMARKETCAP_API_KEY
COINMARKETCAP_BASE_URL = 'https://pro-api.coinmarketcap.com/v1'

def test_coinmarketcap_api():
    """测试 CoinMarketCap API 连接和功能"""
    print("=" * 60)
    print("CoinMarketCap API 测试")
    print("=" * 60)
    
    # 检查 API Key
    if not COINMARKETCAP_API_KEY:
        print("❌ 错误：未配置 CoinMarketCap API Key")
        print("请在 config.py 中设置 COINMARKETCAP_API_KEY")
        return False
    
    print(f"✅ API Key: {COINMARKETCAP_API_KEY[:10]}...{COINMARKETCAP_API_KEY[-4:]}")
    
    # 测试 API 连接
    print("\n🔍 测试 API 连接...")
    try:
        url = f'{COINMARKETCAP_BASE_URL}/cryptocurrency/quotes/latest'
        headers = {
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
            'Accept': 'application/json'
        }
        params = {
            'symbol': 'BTC',
            'convert': 'USD'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'BTC' in data['data']:
                btc_data = data['data']['BTC']
                print(f"✅ API 连接成功！")
                print(f"   BTC 价格: ${btc_data['quote']['USD']['price']:,.2f}")
                print(f"   BTC 流通量: {btc_data['circulating_supply']:,}")
                print(f"   BTC 市值: ${btc_data['quote']['USD']['market_cap']:,.0f}")
            else:
                print("❌ API 响应格式异常")
                return False
        elif response.status_code == 401:
            print("❌ API Key 无效或已过期")
            return False
        elif response.status_code == 429:
            print("❌ API 请求频率超限")
            return False
        else:
            print(f"❌ API 请求失败: {response.status_code}")
            print(f"   响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API 连接异常: {e}")
        return False
    
    # 测试多个币种
    test_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOT', 'AVAX', 'MATIC', 'LINK', 'UNI']
    print(f"\n🔍 测试多个币种流通量获取...")
    
    success_count = 0
    for symbol in test_symbols:
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
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and symbol in data['data']:
                    circ_supply = data['data'][symbol].get('circulating_supply')
                    if circ_supply:
                        print(f"✅ {symbol}: {circ_supply:,}")
                        success_count += 1
                    else:
                        print(f"❌ {symbol}: 无流通量数据")
                else:
                    print(f"❌ {symbol}: 币种未找到")
            else:
                print(f"❌ {symbol}: API 请求失败 ({response.status_code})")
            
            # 避免请求过快
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ {symbol}: 异常 - {e}")
    
    print(f"\n📊 测试结果: {success_count}/{len(test_symbols)} 个币种成功获取")
    
    if success_count >= len(test_symbols) * 0.8:  # 80% 成功率
        print("✅ CoinMarketCap API 测试通过！")
        return True
    else:
        print("❌ CoinMarketCap API 测试失败！")
        return False

def test_specific_symbols():
    """测试一些在 Coingecko 中获取失败的币种"""
    print("\n" + "=" * 60)
    print("测试特定币种（Coingecko 获取失败的币种）")
    print("=" * 60)
    
    # 这些币种在 Coingecko 中经常获取失败
    problematic_symbols = ['ACT', 'ACX', 'ADA', 'AERO', 'AEVO', 'AGIX', 'AGLD']
    
    success_count = 0
    for symbol in problematic_symbols:
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
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and symbol in data['data']:
                    circ_supply = data['data'][symbol].get('circulating_supply')
                    if circ_supply:
                        print(f"✅ {symbol}: {circ_supply:,}")
                        success_count += 1
                    else:
                        print(f"❌ {symbol}: 无流通量数据")
                else:
                    print(f"❌ {symbol}: 币种未找到")
            else:
                print(f"❌ {symbol}: API 请求失败 ({response.status_code})")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ {symbol}: 异常 - {e}")
    
    print(f"\n📊 特定币种测试结果: {success_count}/{len(problematic_symbols)} 个币种成功获取")
    
    if success_count > 0:
        print("✅ CoinMarketCap 可以获取部分 Coingecko 失败的币种！")
    else:
        print("❌ CoinMarketCap 也无法获取这些币种")

if __name__ == '__main__':
    print("开始 CoinMarketCap API 测试...")
    
    # 基础功能测试
    if test_coinmarketcap_api():
        # 特定币种测试
        test_specific_symbols()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60) 