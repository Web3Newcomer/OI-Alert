#!/usr/bin/env python3
"""
定时任务调度器
支持每天东八区上午8点自动运行主程序
"""
import schedule
import time
import logging
from datetime import datetime
import pytz
import pandas as pd
from trading_signal_analyzer import TradingSignalAnalyzer
from wechat_notifier import WeChatNotifier
from config import Config
from local_supply import COIN_SUPPLY
from manual_supply import MANUAL_SUPPLY
from oi_history_collector import OIHistoryCollector
import requests

# 设置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.FileHandler('scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BINANCE_FUTURES_TICKER_URL = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
BINANCE_FUTURES_OI_URL = 'https://fapi.binance.com/fapi/v1/openInterest'
BINANCE_FUTURES_FUNDING_URL = 'https://fapi.binance.com/fapi/v1/premiumIndex'

def get_final_supply():
    """manual_supply.py 有值优先，否则用 local_supply.py"""
    supply = COIN_SUPPLY.copy()
    for k, v in MANUAL_SUPPLY.items():
        if v is not None:
            supply[k] = v
    return supply

# 获取币安USDT合约币种行情数据
def get_binance_futures_data(symbols):
    resp = requests.get(BINANCE_FUTURES_TICKER_URL, timeout=10)
    tickers = resp.json() if resp.status_code == 200 else []
    ticker_map = {t['symbol']: t for t in tickers}
    # 获取所有币种资金费率
    funding_resp = requests.get(BINANCE_FUTURES_FUNDING_URL, timeout=10)
    funding_data = funding_resp.json() if funding_resp.status_code == 200 else []
    funding_map = {f['symbol']: float(f.get('lastFundingRate', 0)) for f in funding_data}
    # 先筛选有行情的币种
    market_rows = []
    for symbol in symbols:
        usdt_pair = symbol + 'USDT'
        t = ticker_map.get(usdt_pair)
        if not t:
            continue
        funding_rate = funding_map.get(usdt_pair, 0)
        price_change_percent = float(t.get('priceChangePercent', 0)) / 100
        market_rows.append({
            'symbol': symbol,
            'price': float(t['lastPrice']),
            'quote_volume_24h': float(t['quoteVolume']),
            'funding_rate': funding_rate,
            'price_change_percent_24h': price_change_percent,
        })
    market_df = pd.DataFrame(market_rows)
    # 按成交额降序取前100
    top_n = getattr(Config, 'TOP_VOLUME_LIMIT', 100)
    market_df = market_df.sort_values('quote_volume_24h', ascending=False).head(top_n)
    # 只对前100采集OI
    oi_list = []
    total = len(market_df)
    for idx, row in enumerate(market_df.itertuples(), 1):
        usdt_pair = row[1] + 'USDT'  # row[1] 是 symbol
        try:
            oi_resp = requests.get(BINANCE_FUTURES_OI_URL, params={'symbol': usdt_pair}, timeout=10)
            oi_val = float(oi_resp.json().get('openInterest', 0))
        except Exception as e:
            print(f"获取 {usdt_pair} open interest 失败: {e}")
            oi_val = 0
        oi_list.append(oi_val * row[2])  # row[2] 是 price
        if idx % 10 == 0 or idx == total:
            print(f"已处理OI {idx}/{total} 个币种...")
            time.sleep(1)
    market_df['open_interest_value'] = oi_list
    return market_df.to_dict(orient='records')

def run_main_program():
    """运行主程序"""
    try:
        logger.info("=" * 50)
        logger.info(f"开始执行定时任务 - {datetime.now(pytz.timezone('Asia/Shanghai'))}")
        logger.info("=" * 50)
        
        # 创建企业微信通知器
        wechat_notifier = WeChatNotifier()
        
        # 合并流通量数据，manual_supply 优先
        supply_dict = get_final_supply()
        current_symbols = list(supply_dict.keys())
        
        # 动态更新币种列表
        oi_collector = OIHistoryCollector()
        updated_symbols = oi_collector.update_symbols_list(current_symbols)
        
        # 如果币种列表有更新，记录日志
        if len(updated_symbols) != len(current_symbols):
            logger.info(f"币种列表已更新: {len(current_symbols)} -> {len(updated_symbols)}")
            # 这里可以添加币种列表持久化逻辑，如果需要的话
        
        # 获取币安行情数据（只采集前100 OI）
        market_data = get_binance_futures_data(updated_symbols)
        df = pd.DataFrame(market_data)
        # 合并流通量
        df['supply'] = df['symbol'].apply(lambda s: supply_dict.get(s))
        # 修复：supply为None或0时，市值为None
        def calc_market_cap(row):
            supply = row['supply']
            price = row['price']
            if supply is None or supply == 0 or price is None or price == 0:
                return None
            return supply * price
        df['market_cap_estimate'] = df.apply(calc_market_cap, axis=1)
        # 此时df已是成交量前100币种，无需再过滤

        if df is None or df.empty:
            logger.error("数据收集失败，跳过本次分析")
            return
        
        logger.info(f"成功收集 {len(df)} 个币种的行情和流通量数据")
        
        # 分析交易信号
        analyzer = TradingSignalAnalyzer()
        signals_df = analyzer.calculate_signals(df)
        
        if not signals_df.empty:
            summary_stats = analyzer.generate_report(signals_df)
            message = wechat_notifier.format_trading_signals_message(signals_df, summary_stats)
            
            # 检查是否有警报信号
            alert_signals_count = summary_stats.get('alert_signals', 0)
            if alert_signals_count > 0:
                logger.info(f"发现 {alert_signals_count} 个警报信号")
                # 可以在这里添加特殊的警报处理逻辑
                
            if wechat_notifier.send_notification_auto(message):
                logger.info("企业微信通知发送成功")
            else:
                logger.warning("企业微信通知发送失败")
            analyzer.print_analysis(signals_df)
        else:
            logger.warning("未生成任何交易信号")
            wechat_notifier.send_simple_notification(
                "交易信号分析完成",
                "本次分析未发现任何交易信号，建议观望。"
            )
        
        logger.info("=" * 50)
        logger.info(f"定时任务执行完成 - {datetime.now(pytz.timezone('Asia/Shanghai'))}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)

def setup_schedule(every_hours=None, funding_rate_mode=False):
    """设置定时任务
    
    Args:
        every_hours: 每隔N小时运行一次
        funding_rate_mode: 是否按资金费率结算时间运行（每8小时一次）
    """
    if funding_rate_mode:
        # 按币安资金费率结算时间运行（UTC时间 00:00、08:00、16:00）
        # 转换为东八区时间：08:00、16:00、00:00（次日）
        schedule.every().day.at("08:00").do(run_main_program)  # UTC 00:00
        schedule.every().day.at("16:00").do(run_main_program)  # UTC 08:00
        schedule.every().day.at("00:00").do(run_main_program)  # UTC 16:00 (次日)
        logger.info("定时任务已设置：按币安资金费率结算时间运行（东八区 00:00、08:00、16:00）")
    elif every_hours is not None:
        schedule.every(every_hours).hours.do(run_main_program)
        logger.info(f"定时任务已设置：每{every_hours}小时运行一次主程序")
    else:
        # 每天东八区上午8点运行（默认）
        schedule.every().day.at("08:00").do(run_main_program)
        logger.info("定时任务已设置：每天东八区上午8点运行主程序")
    logger.info("按 Ctrl+C 停止定时任务")

def run_scheduler(every_hours=None, funding_rate_mode=False):
    """运行调度器"""
    setup_schedule(every_hours, funding_rate_mode)
    
    # 显示下次运行时间
    show_next_run()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在退出...")
    except Exception as e:
        logger.error(f"调度器运行异常: {e}", exc_info=True)

def run_once():
    """立即运行一次主程序"""
    logger.info("立即运行主程序...")
    run_main_program()

def show_next_run():
    """显示下次运行时间"""
    next_run = schedule.next_run()
    if next_run:
        logger.info(f"下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (本地时间)")
    else:
        logger.info("没有设置定时任务")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='币安交易信号分析定时任务')
    parser.add_argument('--run-now', action='store_true', help='立即运行一次主程序')
    parser.add_argument('--show-next', action='store_true', help='显示下次运行时间')
    parser.add_argument('--daemon', action='store_true', help='以守护进程模式运行定时任务')
    parser.add_argument('--every-hours', type=int, default=None, help='每隔N小时运行一次（如1或2）')
    parser.add_argument('--funding-rate', action='store_true', help='按币安资金费率结算时间运行（每8小时一次）')
    
    args = parser.parse_args()
    
    if args.run_now:
        run_once()
    elif args.show_next:
        setup_schedule(args.every_hours, args.funding_rate)
        show_next_run()
    elif args.daemon:
        run_scheduler(args.every_hours, args.funding_rate)
    else:
        parser.print_help()
        print("\n使用示例:")
        print("  python scheduler.py --run-now                    # 立即运行一次")
        print("  python scheduler.py --show-next                  # 显示下次运行时间")
        print("  python scheduler.py --daemon                     # 启动定时任务守护进程")
        print("  python scheduler.py --daemon --every-hours 1     # 每1小时运行一次")
        print("  python scheduler.py --daemon --every-hours 2     # 每2小时运行一次")
        print("  python scheduler.py --daemon --funding-rate      # 按资金费率结算时间运行")
