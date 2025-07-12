#!/usr/bin/env python3
"""
OI历史数据收集器
定期收集币安永续合约的当前OI数据并保存，用于历史数据分析
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
    """OI历史数据收集器"""
    
    def __init__(self):
        self.base_url = "https://fapi.binance.com/fapi/v1"
        self.history_data_dir = "oi_history_data"
        self.cache_duration_hours = 1  # 缓存1小时
        self.max_history_days = 10  # 最多保留10天的历史数据
        self.valid_symbols_cache_file = "valid_symbols_cache.json"
        self.symbols_cache_duration = 24  # 币种列表缓存24小时
        
        # 确保数据目录存在
        if not os.path.exists(self.history_data_dir):
            os.makedirs(self.history_data_dir)
    
    def get_all_futures_symbols(self) -> list:
        """获取所有永续合约交易对"""
        try:
            url = f"{self.base_url}/exchangeInfo"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                symbols = []
                
                for symbol_info in data.get('symbols', []):
                    # 只获取永续合约且状态为TRADING的USDT交易对
                    if (symbol_info.get('status') == 'TRADING' and 
                        symbol_info.get('contractType') == 'PERPETUAL' and
                        symbol_info.get('quoteAsset') == 'USDT'):
                        symbols.append(symbol_info['symbol'])
                
                logger.info(f"成功获取 {len(symbols)} 个有效永续合约交易对")
                return symbols
            else:
                logger.error(f"获取交易对信息失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"获取交易对信息异常: {e}")
            return []
    
    def check_symbol_validity(self, symbol: str) -> bool:
        """检查单个币种是否有效"""
        try:
            # 尝试获取该币种的OI数据
            oi_data = self.get_current_oi(symbol)
            return oi_data is not None
        except Exception as e:
            logger.debug(f"检查币种 {symbol} 有效性失败: {e}")
            return False
    
    def get_valid_symbols(self, force_refresh: bool = False) -> list:
        """获取有效的币种列表"""
        # 检查缓存
        if not force_refresh and os.path.exists(self.valid_symbols_cache_file):
            try:
                with open(self.valid_symbols_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 检查缓存是否过期
                cache_time = datetime.fromisoformat(cache_data.get('cache_time', '2000-01-01'))
                if datetime.now() - cache_time < timedelta(hours=self.symbols_cache_duration):
                    logger.info(f"使用缓存的币种列表，共 {len(cache_data.get('symbols', []))} 个币种")
                    return cache_data.get('symbols', [])
                    
            except Exception as e:
                logger.warning(f"读取币种缓存失败: {e}")
        
        # 获取所有永续合约交易对
        all_symbols = self.get_all_futures_symbols()
        if not all_symbols:
            logger.error("无法获取交易对列表，使用默认列表")
            return []
        
        # 检查每个币种的有效性
        valid_symbols = []
        total = len(all_symbols)
        
        logger.info(f"开始检查 {total} 个币种的有效性...")
        
        for idx, symbol in enumerate(all_symbols, 1):
            try:
                # 移除USDT后缀进行检查
                base_symbol = symbol.replace('USDT', '')
                
                if self.check_symbol_validity(symbol):
                    valid_symbols.append(base_symbol)
                
                if idx % 20 == 0 or idx == total:
                    logger.info(f"已检查币种有效性 {idx}/{total}，有效币种: {len(valid_symbols)}")
                
                # 避免API速率限制
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"检查币种 {symbol} 异常: {e}")
        
        # 保存到缓存
        cache_data = {
            'symbols': valid_symbols,
            'cache_time': datetime.now().isoformat(),
            'total_checked': total,
            'valid_count': len(valid_symbols)
        }
        
        try:
            with open(self.valid_symbols_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"币种列表已缓存，有效币种: {len(valid_symbols)}/{total}")
        except Exception as e:
            logger.error(f"保存币种缓存失败: {e}")
        
        return valid_symbols
    
    def update_symbols_list(self, current_symbols: list) -> list:
        """更新币种列表，移除无效币种，添加新币种"""
        logger.info("开始更新币种列表...")
        
        # 获取当前有效的币种列表
        valid_symbols = self.get_valid_symbols()
        
        if not valid_symbols:
            logger.warning("无法获取有效币种列表，保持当前列表不变")
            return current_symbols
        
        # 找出需要移除的币种（当前列表中存在但已无效的）
        invalid_symbols = [s for s in current_symbols if s not in valid_symbols]
        
        # 找出需要添加的币种（有效列表中存在但当前列表中没有的）
        new_symbols = [s for s in valid_symbols if s not in current_symbols]
        
        # 更新列表
        updated_symbols = [s for s in current_symbols if s in valid_symbols] + new_symbols
        
        # 记录变更
        if invalid_symbols:
            logger.info(f"移除无效币种: {invalid_symbols}")
        
        if new_symbols:
            logger.info(f"添加新币种: {new_symbols}")
        
        if not invalid_symbols and not new_symbols:
            logger.info("币种列表无需更新")
        else:
            logger.info(f"币种列表已更新: {len(current_symbols)} -> {len(updated_symbols)}")
        
        return updated_symbols
    
    def get_current_oi(self, symbol: str) -> dict | None:
        """获取指定币种的当前OI数据"""
        try:
            url = f"{self.base_url}/openInterest"
            params = {'symbol': symbol}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol,
                    'openInterest': float(data.get('openInterest', 0)),
                    'timestamp': data.get('time', int(time.time() * 1000)),
                    'collect_time': datetime.now().isoformat()
                }
            else:
                logger.warning(f"获取 {symbol} 当前OI数据失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取 {symbol} 当前OI数据异常: {e}")
            return None
    
    def get_today_filename(self) -> str:
        """获取今天的文件名"""
        today = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.history_data_dir, f"oi_data_{today}.json")
    
    def load_today_data(self) -> dict:
        """加载今天的数据"""
        filename = self.get_today_filename()
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载今天数据失败: {e}")
        return {}
    
    def save_today_data(self, data: dict):
        """保存今天的数据"""
        filename = self.get_today_filename()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"OI历史数据已保存到 {filename}")
            
            # 清理过期数据
            self.cleanup_old_data()
        except Exception as e:
            logger.error(f"保存今天数据失败: {e}")
    
    def cleanup_old_data(self):
        """清理超过最大保留天数的历史数据"""
        try:
            # 获取所有历史数据文件
            if not os.path.exists(self.history_data_dir):
                return
            files = [f for f in os.listdir(self.history_data_dir) if f.startswith('oi_data_') and f.endswith('.json')]
            # 计算截止日期（保留最近10天）
            cutoff_date = datetime.now() - timedelta(days=self.max_history_days)
            deleted_count = 0
            for filename in files:
                try:
                    # 从文件名提取日期
                    date_str = filename.replace('oi_data_', '').replace('.json', '')
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    # 如果文件日期早于截止日期，则删除
                    if file_date < cutoff_date:
                        file_path = os.path.join(self.history_data_dir, filename)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"删除过期历史数据文件: {filename}")
                except Exception as e:
                    logger.warning(f"处理文件 {filename} 时出错: {e}")
            if deleted_count > 0:
                logger.info(f"清理完成，删除了 {deleted_count} 个过期历史数据文件，仅保留最近{self.max_history_days}天数据")
            else:
                logger.info(f"历史数据文件数量正常，无需清理，当前保留{len(files)}个文件")
        except Exception as e:
            logger.error(f"清理历史数据失败: {e}")
    
    def collect_oi_data(self, symbols: list) -> dict:
        """收集多个币种的OI数据"""
        collected_data = {}
        total = len(symbols)
        
        logger.info(f"开始收集 {total} 个币种的OI数据...")
        
        for idx, symbol in enumerate(symbols, 1):
            try:
                # 添加USDT后缀
                usdt_symbol = symbol + 'USDT'
                oi_data = self.get_current_oi(usdt_symbol)
                
                if oi_data:
                    collected_data[symbol] = oi_data
                
                if idx % 10 == 0 or idx == total:
                    logger.info(f"已收集OI数据 {idx}/{total} 个币种...")
                
                # 避免API速率限制
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"收集 {symbol} OI数据异常: {e}")
        
        return collected_data
    
    def update_history_data(self, symbols: list):
        """更新历史数据"""
        # 加载今天的数据
        today_data = self.load_today_data()
        
        # 收集当前数据
        current_data = self.collect_oi_data(symbols)
        
        # 合并数据
        for symbol, data in current_data.items():
            if symbol not in today_data:
                today_data[symbol] = []
            today_data[symbol].append(data)
        
        # 保存数据
        self.save_today_data(today_data)
        
        logger.info(f"成功更新 {len(current_data)} 个币种的OI历史数据")
    
    def get_symbol_history(self, symbol: str, days: int = 7) -> list:
        """获取指定币种的历史数据"""
        history_data = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            filename = os.path.join(self.history_data_dir, f"oi_data_{date.strftime('%Y-%m-%d')}.json")
            
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        day_data = json.load(f)
                        if symbol in day_data:
                            history_data.extend(day_data[symbol])
                except Exception as e:
                    logger.error(f"加载 {filename} 失败: {e}")
        
        # 按时间排序
        history_data.sort(key=lambda x: x.get('timestamp', 0))
        return history_data
    
    def calculate_oi_ratio(self, symbol: str, recent_count: int = 3, total_count: int = 10) -> float:
        """计算OI比率：最近N次均值 / 最近M次均值"""
        try:
            # 获取历史数据
            history_data = self.get_symbol_history(symbol, days=7)
            if len(history_data) < total_count:
                logger.info(f"{symbol} OI历史数据不足{total_count}条，当前只有{len(history_data)}条")
                return 1.0  # 返回1.0表示无变化
            # 提取最近的OI值
            recent_data = history_data[-total_count:]
            oi_values = [item['openInterest'] for item in recent_data]
            # 计算最近N次均值
            recent_avg = sum(oi_values[:recent_count]) / recent_count
            # 计算最近M次均值
            total_avg = sum(oi_values) / total_count
            # 避免除零错误
            if total_avg == 0:
                return 1.0
            ratio = recent_avg / total_avg
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
                ratio = self.calculate_oi_ratio(symbol)
                results[symbol] = ratio
                
                if idx % 10 == 0 or idx == total:
                    logger.info(f"已处理OI比率 {idx}/{total} 个币种...")
                
                # 避免过度计算
                time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"处理 {symbol} OI比率异常: {e}")
                results[symbol] = 1.0
        
        return results
    
    def get_oi_ratios(self, symbols: list) -> dict:
        """获取OI比率"""
        logger.info(f"开始计算 {len(symbols)} 个币种的OI比率...")
        ratios = self.batch_calculate_oi_ratios(symbols)
        return ratios

def main():
    """测试函数"""
    collector = OIHistoryCollector()
    
    # 测试币种
    test_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'DOT']
    
    print("测试OI历史数据收集...")
    
    # 更新历史数据
    collector.update_history_data(test_symbols)
    
    # 计算OI比率
    print("\n计算OI比率...")
    ratios = collector.get_oi_ratios(test_symbols)
    
    print("\nOI比率结果:")
    for symbol, ratio in ratios.items():
        print(f"{symbol}: {ratio:.3f}")

if __name__ == "__main__":
    main() 