#!/usr/bin/env python3
"""
历史OI数据收集器
用于收集币安永续合约的历史未平仓合约数据，计算OI均值比率
"""
import requests
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
import json
import os
from config import Config

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OIHistoryCollector:
    """历史OI数据收集器"""
    
    def __init__(self):
        self.base_url = "https://fapi.binance.com/fapi/v1"
        self.oi_history_cache_file = "oi_history_cache.json"
        self.cache_duration_hours = 1  # 缓存1小时
        
    def get_oi_history(self, symbol: str, limit: int = 10) -> list:
        """获取指定币种的历史OI数据"""
        try:
            # 币安永续合约OI历史数据API
            url = f"{self.base_url}/openInterestHist"
            params = {
                'symbol': symbol,
                'period': '4h',  # 4小时周期
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.warning(f"获取 {symbol} OI历史数据失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"获取 {symbol} OI历史数据异常: {e}")
            return []
    
    def calculate_oi_ratio(self, symbol: str) -> float:
        """计算OI比率：最近3次4小时均值 / 最近10次4小时均值"""
        try:
            # 获取最近10次OI数据
            oi_history = self.get_oi_history(symbol, limit=10)
            
            if len(oi_history) < 10:
                logger.warning(f"{symbol} OI历史数据不足10条，无法计算比率")
                return 1.0  # 返回1.0表示无变化
            
            # 提取OI值
            oi_values = [float(item['sumOpenInterest']) for item in oi_history]
            
            # 计算最近3次4小时均值
            recent_3_avg = sum(oi_values[:3]) / 3
            
            # 计算最近10次4小时均值
            recent_10_avg = sum(oi_values) / 10
            
            # 避免除零错误
            if recent_10_avg == 0:
                return 1.0
            
            ratio = recent_3_avg / recent_10_avg
            return ratio
            
        except Exception as e:
            logger.error(f"计算 {symbol} OI比率异常: {e}")
            return 1.0
    
    def batch_calculate_oi_ratios(self, symbols: list) -> dict:
        """批量计算多个币种的OI比率"""
        results = {}
        total = len(symbols)
        
        for idx, symbol in enumerate(symbols, 1):
            try:
                # 添加USDT后缀
                usdt_symbol = symbol + 'USDT'
                ratio = self.calculate_oi_ratio(usdt_symbol)
                results[symbol] = ratio
                
                if idx % 10 == 0 or idx == total:
                    logger.info(f"已处理OI比率 {idx}/{total} 个币种...")
                
                # 避免API速率限制
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"处理 {symbol} OI比率异常: {e}")
                results[symbol] = 1.0
        
        return results
    
    def save_oi_ratios_cache(self, ratios: dict):
        """保存OI比率缓存"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'ratios': ratios
            }
            
            with open(self.oi_history_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"OI比率缓存已保存，包含 {len(ratios)} 个币种")
            
        except Exception as e:
            logger.error(f"保存OI比率缓存失败: {e}")
    
    def load_oi_ratios_cache(self) -> dict:
        """加载OI比率缓存"""
        try:
            if not os.path.exists(self.oi_history_cache_file):
                return {}
            
            with open(self.oi_history_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > timedelta(hours=self.cache_duration_hours):
                logger.info("OI比率缓存已过期")
                return {}
            
            logger.info(f"加载OI比率缓存，包含 {len(cache_data['ratios'])} 个币种")
            return cache_data['ratios']
            
        except Exception as e:
            logger.error(f"加载OI比率缓存失败: {e}")
            return {}
    
    def get_oi_ratios(self, symbols: list, use_cache: bool = True) -> dict:
        """获取OI比率，优先使用缓存"""
        if use_cache:
            cached_ratios = self.load_oi_ratios_cache()
            if cached_ratios:
                # 只返回需要的币种
                return {symbol: cached_ratios.get(symbol, 1.0) for symbol in symbols}
        
        # 重新计算
        logger.info(f"开始计算 {len(symbols)} 个币种的OI比率...")
        ratios = self.batch_calculate_oi_ratios(symbols)
        
        # 保存缓存
        self.save_oi_ratios_cache(ratios)
        
        return ratios

def main():
    """测试函数"""
    collector = OIHistoryCollector()
    
    # 测试币种
    test_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'DOT']
    
    print("测试OI历史数据收集...")
    ratios = collector.get_oi_ratios(test_symbols, use_cache=False)
    
    print("\nOI比率结果:")
    for symbol, ratio in ratios.items():
        print(f"{symbol}: {ratio:.3f}")

if __name__ == "__main__":
    main() 