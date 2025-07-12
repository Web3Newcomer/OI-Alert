#!/usr/bin/env python3
"""
流通量数据更新工具
支持从CoinMarketCap获取最新流通量数据并更新本地文件
"""
import requests
import json
import logging
import time
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
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
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
            url = f"https://api.coingecko.com/api/v3/search?query={mapped_symbol}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'coins' in data and data['coins']:
                    coin_id = data['coins'][0]['id']
                    
                    # 获取币种详情
                    detail_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                    detail_response = requests.get(detail_url, timeout=10)
                    
                    if detail_response.status_code == 200:
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
        """更新指定币种的流通量"""
        updated_supply = {}
        success_count = 0
        failed_count = 0
        
        logger.info(f"开始更新 {len(symbols)} 个币种的流通量数据...")
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"处理 {i}/{len(symbols)}: {symbol}")
            
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
            
            # 避免API限制
            time.sleep(1)
        
        logger.info(f"流通量更新完成: 成功 {success_count} 个，失败 {failed_count} 个")
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
            "failed_symbols": []
        }
        
        for symbol, supply in updated_supply.items():
            if supply is not None:
                report["updated_symbols"].append({
                    "symbol": symbol,
                    "supply": supply
                })
            else:
                report["failed_symbols"].append(symbol)
        
        # 保存报告
        with open('supply_update_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info("更新报告已保存到 supply_update_report.json")
        return report

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='流通量数据更新工具')
    parser.add_argument('--all', action='store_true', help='更新所有币种的流通量')
    parser.add_argument('--new', action='store_true', help='只更新新币种的流通量')
    parser.add_argument('--force-all', action='store_true', help='强制更新所有币种的流通量（包括已有数据的）')
    parser.add_argument('--symbols', nargs='+', help='指定要更新的币种列表')
    parser.add_argument('--force', action='store_true', help='强制更新，覆盖现有数据')
    parser.add_argument('--save', action='store_true', help='保存到manual_supply.py文件')
    
    args = parser.parse_args()
    
    updater = SupplyUpdater()
    
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
        print("  python update_supply.py --new --save              # 更新新币种并保存")
        print("  python update_supply.py --force-all --save        # 强制更新所有币种流通量")
        print("  python update_supply.py --all --force --save      # 强制更新所有币种")
        print("  python update_supply.py --symbols BTC ETH         # 更新指定币种")
        return
    
    if args.save and updated_supply:
        updater.save_to_manual_supply(updated_supply)
        updater.generate_update_report(updated_supply)

if __name__ == "__main__":
    main() 