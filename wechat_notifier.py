#!/usr/bin/env python3
"""
企业微信通知模块
用于发送交易信号分析结果到企业微信群
"""
import requests
import logging
from datetime import datetime
import pytz
from config import Config

logger = logging.getLogger(__name__)

class WeChatNotifier:
    def __init__(self):
        self.webhook_url = Config.WECHAT_WEBHOOK_URL
        self.enabled = Config.ENABLE_WECHAT_NOTIFICATION

        if not self.enabled:
            logger.info("企业微信通知已禁用")
            return

        if not self.webhook_url:
            logger.warning("企业微信webhook地址未配置，通知功能将不可用")
            return

        logger.info("企业微信通知器初始化完成")

    def send_text_message(self, content: str) -> bool:
        if not self.enabled or not self.webhook_url:
            return False

        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info("企业微信消息发送成功")
                    return True
                else:
                    logger.error(f"企业微信消息发送失败: {result}")
                    return False
            else:
                logger.error(f"企业微信API请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"发送企业微信消息异常: {e}")
            return False

    def send_markdown_message(self, content: str) -> bool:
        if not self.enabled or not self.webhook_url:
            return False

        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info("企业微信markdown消息发送成功")
                    return True
                else:
                    logger.error(f"企业微信markdown消息发送失败: {result}")
                    return False
            else:
                logger.error(f"企业微信API请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"发送企业微信markdown消息异常: {e}")
            return False

    def format_trading_signals_message(self, signals_df, summary_stats):
        if signals_df is None or signals_df.empty:
            return "【交易信号分析报告】\n\n本次分析未发现任何交易信号"

        buy_signals = signals_df[signals_df['buy_signal']].copy()
        beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))

        message = (
            f"【币安永续合约交易信号分析报告】\n"
            f"分析时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')} (东八区)\n"
            f"分析币种: {summary_stats.get('total_symbols', 0)}\n"
            f"OI/市值警报: {summary_stats.get('buy_signals', 0)}\n"
            f"卖出信号: {summary_stats.get('sell_signals', 0)}\n"
            f"强信号: {summary_stats.get('strong_signals', 0)}\n"
            f"平均信号强度: {summary_stats.get('average_signal_strength', 0):.1f}\n"
            f"平均风险评分: {summary_stats.get('average_risk_score', 0):.1f}\n"
            f"平均OI/市值比: {summary_stats.get('summary_stats', {}).get('avg_oi_market_cap_ratio', 0):.3f}\n"
            f"平均资金费率: {summary_stats.get('summary_stats', {}).get('avg_funding_rate', 0)*100:.3f}%\n"
            f"平均价格变化: {summary_stats.get('summary_stats', {}).get('avg_price_change', 0)*100:.2f}%\n"
        )
        
        # 添加新警报信号统计
        if 'alert_signals' in summary_stats:
            message += f"🚨 OI异常警报: {summary_stats.get('alert_signals', 0)}\n"
            if 'avg_oi_surge_ratio' in summary_stats.get('summary_stats', {}):
                message += f"平均OI激增比率: {summary_stats['summary_stats']['avg_oi_surge_ratio']:.2f}\n"
            if 'avg_funding_rate_abs' in summary_stats.get('summary_stats', {}):
                message += f"平均资金费率绝对值: {summary_stats['summary_stats']['avg_funding_rate_abs']*100:.3f}%\n"
        else:
            message += f"🚨 OI异常警报: 0\n"
        
        if not buy_signals.empty:
            message += "\n【OI/市值警报信号】\n"
            top_signals = buy_signals.nlargest(5, 'signal_strength')
            for idx, (_, signal) in enumerate(top_signals.iterrows(), 1):
                symbol = signal['symbol']
                price = signal['price']
                signal_strength = signal['signal_strength']
                risk_score = signal['risk_score']
                oi_ratio = signal['oi_market_cap_ratio']
                funding_rate = signal['funding_rate'] * 100
                price_change = signal['price_change_percent_24h'] * 100
                market_cap = signal.get('market_cap_estimate', 0)
                if market_cap is None or market_cap <= 0:
                    market_cap_str = "N/A"
                elif market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap/1e3:.0f}K"
                message += (
                    f"{idx}. {symbol}  价格: ${price:,.4f}  市值: {market_cap_str}  信号强度: {signal_strength:.1f}/100  "
                    f"风险: {risk_score:.1f}/100  OI/市值: {oi_ratio:.3f}  "
                    f"资金费率: {funding_rate:.3f}%  24h涨跌: {price_change:+.2f}%\n"
                )
        else:
            message += "\n暂无OI/市值警报信号\n"

        # 新警报信号
        if 'top_alert_signals' in summary_stats and summary_stats['top_alert_signals']:
            message += "\n🚨【OI异常警报信号】\n"
            for idx, signal in enumerate(summary_stats['top_alert_signals'][:3], 1):
                symbol = signal['symbol']
                price = signal['price']
                funding_rate = signal['funding_rate'] * 100
                oi_surge_ratio = signal.get('oi_surge_ratio', 1.0)
                price_change = signal['price_change_percent_24h'] * 100
                market_cap = signal.get('market_cap_estimate', 0)
                if market_cap is None or market_cap <= 0:
                    market_cap_str = "N/A"
                elif market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap/1e3:.0f}K"
                message += (
                    f"{idx}. {symbol}  价格: ${price:,.4f}  市值: {market_cap_str}  "
                    f"资金费率: {funding_rate:.3f}%  OI激增: {oi_surge_ratio:.2f}x  "
                    f"24h涨跌: {price_change:+.2f}%\n"
                )
        else:
            message += "\n暂无OI异常警报信号\n"

        # 推荐卖出信号
        sell_signals = signals_df[signals_df['sell_signal']].copy()
        if not sell_signals.empty:
            message += "\n【推荐卖出信号】\n"
            top_sell_signals = sell_signals.nsmallest(3, 'signal_strength')
            for idx, (_, signal) in enumerate(top_sell_signals.iterrows(), 1):
                symbol = signal['symbol']
                price = signal['price']
                signal_strength = signal['signal_strength']
                risk_score = signal['risk_score']
                oi_ratio = signal['oi_market_cap_ratio']
                funding_rate = signal['funding_rate'] * 100
                price_change = signal['price_change_percent_24h'] * 100
                market_cap = signal.get('market_cap_estimate', 0)
                if market_cap is None or market_cap <= 0:
                    market_cap_str = "N/A"
                elif market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap/1e3:.0f}K"
                message += (
                    f"{idx}. {symbol}  价格: ${price:,.4f}  市值: {market_cap_str}  信号强度: {signal_strength:.1f}/100  "
                    f"风险: {risk_score:.1f}/100  OI/市值: {oi_ratio:.3f}  "
                    f"资金费率: {funding_rate:.3f}%  24h涨跌: {price_change:+.2f}%\n"
                )

        # 高风险交易对
        high_risk = signals_df[signals_df['risk_score'] > 70].sort_values('risk_score', ascending=False)
        if not high_risk.empty:
            message += "\n⚠️  高风险交易对:\n"
            for _, row in high_risk.head(3).iterrows():
                market_cap = row['market_cap_estimate']
                if market_cap is None or market_cap <= 0:
                    market_cap_str = "N/A"
                elif market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap/1e3:.0f}K"
                message += (
                    f"🚨 {row['symbol']:>10} | 风险评分: {row['risk_score']:>5.1f} | 市值: {market_cap_str:>8} | 价格: ${row['price']:>10,.2f} | 24h变化: {row['price_change_percent_24h']:>6.2f}%\n"
                )

        message += (
            "\n【风险提示】\n"
            "本分析仅供参考，不构成投资建议。请结合市场情况和个人风险承受能力。投资有风险，入市需谨慎。\n"
            "（由系统自动生成）"
        )
        return message

    def send_trading_signals_report(self, signals_df, summary_stats):
        if not self.enabled:
            logger.info("企业微信通知已禁用，跳过发送")
            return False
        try:
            message = self.format_trading_signals_message(signals_df, summary_stats)
            return self.send_markdown_message(message)
        except Exception as e:
            logger.error(f"发送交易信号报告失败: {e}")
            return False

    def send_simple_notification(self, title: str, content: str) -> bool:
        if not self.enabled:
            return False
        message = f"""🔔 **{title}**

{content}

---
*{datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}*"""
        return self.send_markdown_message(message)

    def send_notification_auto(self, content: str) -> bool:
        """始终使用纯文本格式发送，兼容企业微信和微信端"""
        return self.send_text_message(content)