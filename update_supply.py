#!/usr/bin/env python3
"""
流通量数据更新工具
支持从CoinMarketCap获取最新流通量数据并更新本地文件
包含等待和重试机制，提高成功率
"""
import requests
import json
import logging
import time
import random
from datetime import datetime
from config import Config
from local_supply import COIN_SUPPLY
from manual_supply import MANUAL_SUPPLY

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SupplyUpdater:
    """流通量数据更新器"""
    
    def __init__(self):
        self.coinmarketcap_api_key = getattr(Config, 'COINMARKETCAP_API_KEY', None)
        self.enable_coinmarketcap = getattr(Config, 'ENABLE_COINMARKETCAP', True)
        self.symbol_mapping = self.load_symbol_mapping()
        
        # 重试和等待配置
        self.max_retries = 3  # 最大重试次数
        self.base_delay = 2   # 基础延迟时间（秒）
        self.max_delay = 60   # 最大延迟时间（秒）
        self.batch_size = 10  # 批处理大小
        self.batch_delay = 5  # 批次间延迟（秒）
        
        # API限制计数器
        self.cmc_request_count = 0
        self.coingecko_request_count = 0
        self.last_cmc_request = 0
        self.last_coingecko_request = 0
        
        # API限制阈值
        self.cmc_rate_limit = 30  # CoinMarketCap每分钟请求限制
        self.coingecko_rate_limit = 50  # CoinGecko每分钟请求限制
    
    def load_symbol_mapping(self):
        """加载币种名称映射"""
        try:
            with open('symbol_mapping.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def get_mapped_symbol(self, symbol):
        """获取映射后的币种名称"""
        if symbol in self.symbol_mapping:
            source, mapped_id = self.symbol_mapping[symbol]
            return mapped_id
        return symbol
    
    def exponential_backoff(self, attempt):
        """指数退避算法"""
        delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 1), self.max_delay)
        return delay
    
    def check_rate_limit(self, api_type):
        """检查API速率限制"""
        current_time = time.time()
        
        if api_type == 'cmc':
            # 检查CoinMarketCap速率限制
            if current_time - self.last_cmc_request < 60:  # 1分钟内
                if self.cmc_request_count >= self.cmc_rate_limit:
                    wait_time = 60 - (current_time - self.last_cmc_request)
                    logger.warning(f"CoinMarketCap API速率限制，等待 {wait_time:.1f} 秒")
                    time.sleep(wait_time)
                    self.cmc_request_count = 0
                    self.last_cmc_request = time.time()
            else:
                # 重置计数器
                self.cmc_request_count = 0
                self.last_cmc_request = current_time
            
            self.cmc_request_count += 1
            
        elif api_type == 'coingecko':
            # 检查CoinGecko速率限制
            if current_time - self.last_coingecko_request < 60:  # 1分钟内
                if self.coingecko_request_count >= self.coingecko_rate_limit:
                    wait_time = 60 - (current_time - self.last_coingecko_request)
                    logger.warning(f"CoinGecko API速率限制，等待 {wait_time:.1f} 秒")
                    time.sleep(wait_time)
                    self.coingecko_request_count = 0
                    self.last_coingecko_request = time.time()
            else:
                # 重置计数器
                self.coingecko_request_count = 0
                self.last_coingecko_request = current_time
            
            self.coingecko_request_count += 1
    
    def make_request_with_retry(self, url, headers=None, params=None, api_type='cmc', timeout=15):
        """带重试机制的请求"""
        for attempt in range(self.max_retries + 1):
            try:
                # 检查速率限制
                self.check_rate_limit(api_type)
                
                # 发送请求
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
                
                # 检查响应状态
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # 速率限制
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"{api_type.upper()} API速率限制，等待 {retry_after} 秒")
                    time.sleep(retry_after)
                    continue
                elif response.status_code == 404:  # 未找到
                    logger.warning(f"{api_type.upper()} API返回404，币种可能不存在")
                    return None
                else:
                    logger.warning(f"{api_type.upper()} API返回状态码 {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"{api_type.upper()} API请求超时，尝试 {attempt + 1}/{self.max_retries + 1}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"{api_type.upper()} API请求异常: {e}，尝试 {attempt + 1}/{self.max_retries + 1}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.max_retries:
                delay = self.exponential_backoff(attempt)
                logger.info(f"等待 {delay:.1f} 秒后重试...")
                time.sleep(delay)
        
        logger.error(f"{api_type.upper()} API请求失败，已达到最大重试次数")
        return None
        
    def get_coinmarketcap_supply(self, symbol):
        """从CoinMarketCap获取币种流通量"""
        if not self.coinmarketcap_api_key or not self.enable_coinmarketcap:
            logger.warning("CoinMarketCap API未配置或未启用")
            return None
            
        try:
            # 使用映射后的币种名称
            mapped_symbol = self.get_mapped_symbol(symbol)
            
            # CoinMarketCap API v2
            url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
            headers = {
                'X-CMC_PRO_API_KEY': self.coinmarketcap_api_key,
                'Accept': 'application/json'
            }
            params = {
                'symbol': mapped_symbol,
                'convert': 'USD'
            }
            
            response = self.make_request_with_retry(url, headers=headers, params=params, api_type='cmc')
            
            if response and response.status_code == 200:
                data = response.json()
                if 'data' in data and mapped_symbol in data['data']:
                    coin_data = data['data'][mapped_symbol][0]
                    circulating_supply = coin_data.get('circulating_supply')
                    if circulating_supply:
                        return int(circulating_supply)
            
            logger.warning(f"无法从CoinMarketCap获取 {symbol} (映射: {mapped_symbol}) 的流通量数据")
            return None
            
        except Exception as e:
            logger.error(f"获取 {symbol} 流通量失败: {e}")
            return None
    
    def get_coingecko_supply(self, symbol):
        """从CoinGecko获取币种流通量（备用方案）"""
        try:
            # 使用映射后的币种名称
            mapped_symbol = self.get_mapped_symbol(symbol)
            
            # 获取币种ID
            search_url = f"https://api.coingecko.com/api/v3/search?query={mapped_symbol}"
            search_response = self.make_request_with_retry(search_url, api_type='coingecko')
            
            if search_response and search_response.status_code == 200:
                data = search_response.json()
                if 'coins' in data and data['coins']:
                    coin_id = data['coins'][0]['id']
                    
                    # 获取币种详情
                    detail_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                    detail_response = self.make_request_with_retry(detail_url, api_type='coingecko')
                    
                    if detail_response and detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        circulating_supply = detail_data.get('market_data', {}).get('circulating_supply')
                        if circulating_supply:
                            return int(circulating_supply)
            
            logger.warning(f"无法从CoinGecko获取 {symbol} (映射: {mapped_symbol}) 的流通量数据")
            return None
            
        except Exception as e:
            logger.error(f"从CoinGecko获取 {symbol} 流通量失败: {e}")
            return None
    
    def update_supply_for_symbols(self, symbols, force_update=False):
        """更新指定币种的流通量（分批处理）"""
        updated_supply = {}
        success_count = 0
        failed_count = 0
        
        logger.info(f"开始更新 {len(symbols)} 个币种的流通量数据...")
        logger.info(f"批处理大小: {self.batch_size}，批次间延迟: {self.batch_delay}秒")
        
        # 分批处理
        for batch_start in range(0, len(symbols), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(symbols))
            batch_symbols = symbols[batch_start:batch_end]
            
            logger.info(f"处理批次 {batch_start//self.batch_size + 1}/{(len(symbols) + self.batch_size - 1)//self.batch_size}: {batch_symbols}")
            
            for symbol in batch_symbols:
                logger.info(f"处理: {symbol}")
                
                # 检查是否需要更新
                current_supply = MANUAL_SUPPLY.get(symbol) or COIN_SUPPLY.get(symbol)
                if current_supply and not force_update:
                    logger.info(f"{symbol} 已有流通量数据，跳过更新")
                    updated_supply[symbol] = current_supply
                    continue
                
                # 尝试从CoinMarketCap获取
                supply = self.get_coinmarketcap_supply(symbol)
                
                # 如果CoinMarketCap失败，尝试CoinGecko
                if supply is None:
                    logger.info(f"尝试从CoinGecko获取 {symbol} 流通量...")
                    supply = self.get_coingecko_supply(symbol)
                
                if supply:
                    updated_supply[symbol] = supply
                    success_count += 1
                    logger.info(f"{symbol} 流通量更新成功: {supply:,}")
                else:
                    updated_supply[symbol] = None  # 保存失败状态
                    failed_count += 1
                    logger.warning(f"{symbol} 流通量获取失败")
                
                # 币种间延迟
                time.sleep(1)
            
            # 批次间延迟
            if batch_end < len(symbols):
                logger.info(f"批次完成，等待 {self.batch_delay} 秒后处理下一批次...")
                time.sleep(self.batch_delay)
        
        logger.info(f"流通量更新完成: 成功 {success_count} 个，失败 {failed_count} 个")
        logger.info(f"成功率: {success_count/(success_count+failed_count)*100:.1f}%")
        return updated_supply
    
    def update_all_supply(self, force_update=False):
        """更新所有币种的流通量"""
        # 获取所有币种
        all_symbols = list(set(list(COIN_SUPPLY.keys()) + list(MANUAL_SUPPLY.keys())))
        
        return self.update_supply_for_symbols(all_symbols, force_update)
    
    def update_new_symbols(self, force_update=False):
        """只更新新币种的流通量"""
        if force_update:
            # 强制更新所有币种
            all_symbols = list(COIN_SUPPLY.keys())
            logger.info(f"强制更新所有 {len(all_symbols)} 个币种的流通量")
            return self.update_supply_for_symbols(all_symbols, force_update=True)
        else:
            # 只更新没有流通量数据的币种
            new_symbols = []
            for symbol in COIN_SUPPLY.keys():
                if symbol not in MANUAL_SUPPLY or MANUAL_SUPPLY[symbol] is None:
                    new_symbols.append(symbol)
            
            if not new_symbols:
                logger.info("没有需要更新的新币种")
                return {}
            
            logger.info(f"发现 {len(new_symbols)} 个新币种需要更新流通量")
            return self.update_supply_for_symbols(new_symbols)
    
    def save_to_manual_supply(self, updated_supply):
        """保存到manual_supply.py文件"""
        try:
            # 读取现有的manual_supply.py
            with open('manual_supply.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 生成新的MANUAL_SUPPLY字典
            new_supply_content = "MANUAL_SUPPLY = {\n"
            for symbol, supply in updated_supply.items():
                if supply is None:
                    new_supply_content += f"    '{symbol}': None,\n"
                else:
                    new_supply_content += f"    '{symbol}': {supply},\n"
            new_supply_content += "}\n"
            
            # 备份原文件
            backup_filename = f"manual_supply_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 更新文件
            with open('manual_supply.py', 'w', encoding='utf-8') as f:
                f.write(new_supply_content)
            
            logger.info(f"流通量数据已保存到 manual_supply.py")
            logger.info(f"原文件已备份为 {backup_filename}")
            
        except Exception as e:
            logger.error(f"保存流通量数据失败: {e}")
    
    def generate_update_report(self, updated_supply):
        """生成更新报告"""
        report = {
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_symbols": len(updated_supply),
            "updated_symbols": [],
            "failed_symbols": [],
            "success_rate": 0.0
        }
        
        success_count = 0
        for symbol, supply in updated_supply.items():
            if supply is not None:
                report["updated_symbols"].append({
                    "symbol": symbol,
                    "supply": supply
                })
                success_count += 1
            else:
                report["failed_symbols"].append(symbol)
        
        report["success_rate"] = success_count / len(updated_supply) * 100 if updated_supply else 0
        
        # 保存报告
        with open('supply_update_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info("更新报告已保存到 supply_update_report.json")
        logger.info(f"成功率: {report['success_rate']:.1f}%")
        return report

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='流通量数据更新工具（带重试机制）')
    parser.add_argument('--all', action='store_true', help='更新所有币种的流通量')
    parser.add_argument('--new', action='store_true', help='只更新新币种的流通量')
    parser.add_argument('--force-all', action='store_true', help='强制更新所有币种的流通量（包括已有数据的）')
    parser.add_argument('--symbols', nargs='+', help='指定要更新的币种列表')
    parser.add_argument('--force', action='store_true', help='强制更新，覆盖现有数据')
    parser.add_argument('--save', action='store_true', help='保存到manual_supply.py文件')
    parser.add_argument('--batch-size', type=int, default=10, help='批处理大小（默认10）')
    parser.add_argument('--batch-delay', type=int, default=5, help='批次间延迟秒数（默认5）')
    parser.add_argument('--max-retries', type=int, default=3, help='最大重试次数（默认3）')
    
    args = parser.parse_args()
    
    updater = SupplyUpdater()
    
    # 更新配置
    if args.batch_size:
        updater.batch_size = args.batch_size
    if args.batch_delay:
        updater.batch_delay = args.batch_delay
    if args.max_retries:
        updater.max_retries = args.max_retries
    
    logger.info(f"配置: 批处理大小={updater.batch_size}, 批次延迟={updater.batch_delay}秒, 最大重试={updater.max_retries}")
    
    if args.symbols:
        # 更新指定币种
        updated_supply = updater.update_supply_for_symbols(args.symbols, args.force)
    elif args.force_all:
        # 强制更新所有币种
        updated_supply = updater.update_new_symbols(force_update=True)
    elif args.all:
        # 更新所有币种
        updated_supply = updater.update_all_supply(args.force)
    elif args.new:
        # 只更新新币种
        updated_supply = updater.update_new_symbols()
    else:
        parser.print_help()
        print("\n使用示例:")
        print("  python update_supply.py --new --save                    # 更新新币种并保存")
        print("  python update_supply.py --force-all --save              # 强制更新所有币种流通量")
        print("  python update_supply.py --all --force --save            # 强制更新所有币种")
        print("  python update_supply.py --symbols BTC ETH               # 更新指定币种")
        print("  python update_supply.py --new --save --batch-size 5     # 小批次处理")
        print("  python update_supply.py --new --save --max-retries 5    # 增加重试次数")
        return
    
    if args.save and updated_supply:
        updater.save_to_manual_supply(updated_supply)
        updater.generate_update_report(updated_supply)

if __name__ == "__main__":
    main() 