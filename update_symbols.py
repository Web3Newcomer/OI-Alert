#!/usr/bin/env python3
"""
币种列表更新工具
用于动态检查和更新有效的币种列表
"""
import json
import logging
from datetime import datetime
from oi_history_collector import OIHistoryCollector
from local_supply import COIN_SUPPLY
from manual_supply import MANUAL_SUPPLY

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_final_supply():
    """manual_supply.py 有值优先，否则用 local_supply.py"""
    supply = COIN_SUPPLY.copy()
    for k, v in MANUAL_SUPPLY.items():
        if v is not None:
            supply[k] = v
    return supply

def update_symbols_list():
    """更新币种列表和流通量数据"""
    try:
        logger.info("开始更新币种列表和流通量数据...")
        
        # 获取当前币种列表
        current_supply = get_final_supply()
        current_symbols = list(current_supply.keys())
        
        logger.info(f"当前币种列表包含 {len(current_symbols)} 个币种")
        
        # 创建OI收集器
        oi_collector = OIHistoryCollector()
        
        # 更新币种列表
        updated_symbols = oi_collector.update_symbols_list(current_symbols)
        
        # 生成更新报告
        removed_symbols = [s for s in current_symbols if s not in updated_symbols]
        added_symbols = [s for s in updated_symbols if s not in current_symbols]
        
        # 保存更新后的币种列表（保留原有流通量数据）
        updated_supply = {symbol: current_supply.get(symbol) for symbol in updated_symbols}
        
        # 保存到文件
        with open('updated_supply.json', 'w', encoding='utf-8') as f:
            json.dump(updated_supply, f, ensure_ascii=False, indent=2)
        
        # 生成local_supply.py格式的更新文件
        generate_local_supply_update(updated_supply, removed_symbols, added_symbols)
        
        # 输出报告
        logger.info("=" * 50)
        logger.info("币种列表更新报告")
        logger.info("=" * 50)
        logger.info(f"更新前币种数量: {len(current_symbols)}")
        logger.info(f"更新后币种数量: {len(updated_symbols)}")
        
        if removed_symbols:
            logger.info(f"移除的币种 ({len(removed_symbols)}): {removed_symbols}")
        
        if added_symbols:
            logger.info(f"新增的币种 ({len(added_symbols)}): {added_symbols}")
        
        if not removed_symbols and not added_symbols:
            logger.info("币种列表无需更新")
        
        logger.info(f"更新后的币种列表已保存到 updated_supply.json")
        logger.info(f"local_supply.py 更新建议已保存到 local_supply_update.py")
        logger.info("=" * 50)
        
        return updated_symbols, removed_symbols, added_symbols
        
    except Exception as e:
        logger.error(f"更新币种列表失败: {e}")
        return [], [], []

def generate_local_supply_update(updated_supply, removed_symbols, added_symbols):
    """生成local_supply.py格式的更新文件"""
    try:
        # 读取当前的local_supply.py内容
        with open('local_supply.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 生成更新后的COIN_SUPPLY字典
        updated_content = "COIN_SUPPLY = {\n"
        for symbol, supply in updated_supply.items():
            if supply is None:
                updated_content += f"    '{symbol}': None,\n"
            else:
                updated_content += f"    '{symbol}': {supply},\n"
        updated_content += "}\n"
        
        # 添加更新说明
        update_info = f'''# 自动生成的币种列表更新
# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 移除的币种: {removed_symbols}
# 新增的币种: {added_symbols}
# 总币种数: {len(updated_supply)}

'''
        
        # 保存更新文件
        with open('local_supply_update.py', 'w', encoding='utf-8') as f:
            f.write(update_info + updated_content)
        
        logger.info("已生成 local_supply_update.py 文件")
        
    except Exception as e:
        logger.error(f"生成local_supply更新文件失败: {e}")

def get_valid_symbols_only():
    """只获取有效的币种列表，不更新现有列表"""
    try:
        logger.info("获取有效币种列表...")
        
        oi_collector = OIHistoryCollector()
        valid_symbols = oi_collector.get_valid_symbols(force_refresh=True)
        
        logger.info(f"获取到 {len(valid_symbols)} 个有效币种")
        
        # 保存到文件
        with open('valid_symbols_only.json', 'w', encoding='utf-8') as f:
            json.dump(valid_symbols, f, ensure_ascii=False, indent=2)
        
        logger.info("有效币种列表已保存到 valid_symbols_only.json")
        
        return valid_symbols
        
    except Exception as e:
        logger.error(f"获取有效币种列表失败: {e}")
        return []

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='币种列表更新工具')
    parser.add_argument('--update', action='store_true', help='更新币种列表')
    parser.add_argument('--get-valid', action='store_true', help='只获取有效币种列表')
    parser.add_argument('--force-refresh', action='store_true', help='强制刷新缓存')
    
    args = parser.parse_args()
    
    if args.update:
        update_symbols_list()
    elif args.get_valid:
        get_valid_symbols_only()
    else:
        parser.print_help()
        print("\n使用示例:")
        print("  python update_symbols.py --update          # 更新币种列表")
        print("  python update_symbols.py --get-valid       # 获取有效币种列表")

if __name__ == "__main__":
    main() 