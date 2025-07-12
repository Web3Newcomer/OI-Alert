import pandas as pd
import numpy as np
import logging
from strategy_config import StrategyConfig
from oi_history_collector import OIHistoryCollector

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradingSignalAnalyzer:
    def __init__(self, config=None):
        """初始化交易信号分析器"""
        # 使用传入的配置或默认配置
        self.config = config if config else StrategyConfig.get_balanced_config()
        
        # 从配置中获取策略参数
        self.oi_market_cap_ratio_threshold = self.config.OI_MARKET_CAP_RATIO_THRESHOLD
        self.min_oi_value = self.config.MIN_OI_VALUE
        self.volume_threshold = self.config.VOLUME_MARKET_CAP_RATIO_THRESHOLD
        self.funding_rate_threshold = 0.0001  # 资金费率阈值
        self.price_change_threshold = 0.02  # 24h价格变化阈值 2%
        
        # 新警报条件参数
        self.funding_rate_abs_threshold = getattr(self.config, 'FUNDING_RATE_ABS_THRESHOLD', 0.001)
        self.oi_surge_ratio_threshold = getattr(self.config, 'OI_SURGE_RATIO_THRESHOLD', 2.0)
        self.enable_new_alert_conditions = getattr(self.config, 'ENABLE_NEW_ALERT_CONDITIONS', True)
        
        # 初始化OI历史收集器
        self.oi_collector = OIHistoryCollector()
        
    def calculate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算交易信号"""
        if data.empty:
            logger.warning("输入数据为空")
            return pd.DataFrame()
        
        # 复制数据避免修改原始数据
        df = data.copy()
        
        # 计算关键指标
        df['oi_market_cap_ratio'] = df['open_interest_value'] / df['market_cap_estimate']
        df['volume_market_cap_ratio'] = df['quote_volume_24h'] / df['market_cap_estimate']
        df['oi_volume_ratio'] = df['open_interest_value'] / df['quote_volume_24h']
        
        # 计算新警报条件指标
        if self.enable_new_alert_conditions:
            df = self._calculate_new_alert_indicators(df)
        
        # 计算信号强度
        df['signal_strength'] = self._calculate_signal_strength(df)
        
        # 生成交易信号
        df['buy_signal'] = self._generate_buy_signals(df)
        df['sell_signal'] = self._generate_sell_signals(df)
        
        # 生成新警报信号
        if self.enable_new_alert_conditions:
            df['alert_signal'] = self._generate_alert_signals(df)
        
        # 添加信号描述
        df['signal_description'] = df.apply(self._get_signal_description, axis=1)
        
        # 计算风险评分
        df['risk_score'] = self._calculate_risk_score(df)
        
        return df
    
    def _calculate_new_alert_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算新警报条件指标"""
        try:
            # 获取所有币种
            symbols = df['symbol'].tolist()
            
            # 更新历史数据
            logger.info("开始更新OI历史数据...")
            self.oi_collector.update_history_data(symbols)
            
            # 获取OI比率数据
            logger.info("开始获取OI比率数据...")
            oi_ratios = self.oi_collector.get_oi_ratios(symbols)
            
            # 添加OI比率到数据框
            df['oi_surge_ratio'] = df['symbol'].map(lambda x: oi_ratios.get(x, 1.0))
            
            # 计算资金费率绝对值
            df['funding_rate_abs'] = abs(df['funding_rate'])
            
            logger.info(f"成功计算 {len(df)} 个币种的新警报指标")
            
        except Exception as e:
            logger.error(f"计算新警报指标异常: {e}")
            # 设置默认值
            df['oi_surge_ratio'] = 1.0
            df['funding_rate_abs'] = abs(df['funding_rate'])
        
        return df
    
    def _calculate_signal_strength(self, df: pd.DataFrame) -> pd.Series:
        """计算信号强度 (0-100)"""
        strength = pd.Series(0, index=df.index)
        
        # OI/市值比率得分 (40分)
        oi_ratio_score = np.clip(df['oi_market_cap_ratio'] * 100, 0, 40)
        strength += oi_ratio_score
        
        # OI价值得分 (20分)
        oi_value_score = np.clip(df['open_interest_value'] / 10_000_000 * 20, 0, 20)
        strength += oi_value_score
        
        # 成交量得分 (20分)
        volume_score = np.clip(df['volume_market_cap_ratio'] * 100, 0, 20)
        strength += volume_score
        
        # 资金费率得分 (10分)
        funding_score = np.where(
            abs(df['funding_rate']) > self.funding_rate_threshold,
            10, 5
        )
        strength += funding_score
        
        # 价格动量得分 (10分)
        momentum_score = np.where(
            abs(df['price_change_percent_24h']) > self.price_change_threshold,
            10, 5
        )
        strength += momentum_score
        
        return strength
    
    def _generate_buy_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成买入信号"""
        buy_conditions = (
            (df['oi_market_cap_ratio'] > self.oi_market_cap_ratio_threshold) &  # OI/市值 > 0.5
            (df['open_interest_value'] > self.min_oi_value) &  # OI > 5M
            (df['volume_market_cap_ratio'] > self.volume_threshold) &  # 成交量/市值 > 0.1
            (df['signal_strength'] > 60)  # 信号强度 > 60
        )
        
        return buy_conditions
    
    def _generate_sell_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成卖出信号"""
        sell_conditions = (
            (df['oi_market_cap_ratio'] < 0.2) &  # OI/市值 < 0.2
            (df['signal_strength'] < 30) &  # 信号强度 < 30
            (df['funding_rate'] < -0.0001)  # 负资金费率
        )
        
        return sell_conditions
    
    def _generate_alert_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成新警报信号"""
        if not self.enable_new_alert_conditions:
            return pd.Series(False, index=df.index)
        
        # 使用历史OI比率进行警报检测
        # 当资金费率绝对值较大且OI短期激增时触发警报
        alert_conditions = (
            (df['funding_rate_abs'].fillna(0) > self.funding_rate_abs_threshold) &  # 资金费率绝对值 > 0.1%
            (df['oi_surge_ratio'].fillna(1.0) > self.oi_surge_ratio_threshold)  # OI短期激增 > 2
        )
        
        return alert_conditions
    
    def _get_signal_description(self, row: pd.Series) -> str:
        """获取信号描述"""
        descriptions = []
        
        if bool(row['buy_signal']):
            descriptions.append("OI/市值警报")
        elif bool(row['sell_signal']):
            descriptions.append("考虑卖出")
        else:
            descriptions.append("观望")
        
        # 添加新警报信号描述
        if self.enable_new_alert_conditions and row.get('alert_signal', False):
            descriptions.append("🚨OI异常警报")
        
        # 添加具体指标说明
        if row['oi_market_cap_ratio'] > self.oi_market_cap_ratio_threshold:
            descriptions.append(f"OI/市值比高({row['oi_market_cap_ratio']:.2f})")
        
        if row['open_interest_value'] > self.min_oi_value:
            descriptions.append(f"OI充足({row['open_interest_value']/1e6:.1f}M)")
        
        if abs(row['funding_rate']) > self.funding_rate_threshold:
            descriptions.append(f"资金费率{row['funding_rate']*100:.3f}%")
        
        # 添加新警报指标说明
        if self.enable_new_alert_conditions:
            funding_rate_abs = row.get('funding_rate_abs', 0)
            if funding_rate_abs is not None and funding_rate_abs > self.funding_rate_abs_threshold:
                descriptions.append(f"资金费率异常({row['funding_rate']*100:.3f}%)")
            
            oi_surge_ratio = row.get('oi_surge_ratio', 1.0)
            if oi_surge_ratio is not None and oi_surge_ratio > self.oi_surge_ratio_threshold:
                descriptions.append(f"OI激增({oi_surge_ratio:.2f}x)")
        
        return " | ".join(descriptions)
    
    def _calculate_risk_score(self, df: pd.DataFrame) -> pd.Series:
        """计算风险评分 (0-100, 越高越危险)"""
        risk = pd.Series(0, index=df.index)
        
        # 价格波动风险 (30分)
        volatility_risk = np.clip(abs(df['price_change_percent_24h']) * 10, 0, 30)
        risk += volatility_risk
        
        # 资金费率风险 (20分)
        funding_risk = np.clip(abs(df['funding_rate']) * 100000, 0, 20)
        risk += funding_risk
        
        # 流动性风险 (30分)
        liquidity_risk = np.where(
            df['volume_market_cap_ratio'] < 0.05,
            30,
            np.clip((0.1 - df['volume_market_cap_ratio']) * 300, 0, 30)
        )
        risk += liquidity_risk
        
        # 市值风险 (20分)
        market_cap_risk = np.where(
            df['market_cap_estimate'] < 100_000_000,  # 小于1亿市值
            20, 10
        )
        risk += market_cap_risk
        
        return risk
    
    def get_top_signals(self, df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """获取最强的交易信号"""
        if df.empty:
            return pd.DataFrame()
        
        # 筛选买入信号
        buy_signals = df[df['buy_signal']].copy()
        
        if buy_signals.empty:
            logger.info("没有找到买入信号")
            return pd.DataFrame()
        
        # 按信号强度排序
        buy_signals = buy_signals.sort_values(by='signal_strength', ascending=False)
        
        return buy_signals.head(top_n)
    
    def get_alert_signals(self, df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """获取警报信号"""
        if df.empty or not self.enable_new_alert_conditions:
            return pd.DataFrame()
        
        # 筛选警报信号
        alert_signals = df[df.get('alert_signal', False)].copy()
        
        if alert_signals.empty:
            logger.info("没有找到警报信号")
            return pd.DataFrame()
        
        # 按资金费率绝对值排序
        alert_signals = alert_signals.sort_values(by='funding_rate_abs', ascending=False)
        
        return alert_signals.head(top_n)
    
    def generate_report(self, df: pd.DataFrame) -> dict:
        """生成分析报告"""
        if df.empty:
            return {"error": "没有数据"}
        
        report = {
            "total_symbols": len(df),
            "buy_signals": len(df[df['buy_signal']]),
            "sell_signals": len(df[df['sell_signal']]),
            "strong_signals": len(df[df['signal_strength'] > 80]),
            "average_signal_strength": df['signal_strength'].mean(),
            "average_risk_score": df['risk_score'].mean(),
            "top_signals": self.get_top_signals(df, 5).to_dict('records'),
            "summary_stats": {
                "avg_oi_market_cap_ratio": df['oi_market_cap_ratio'].mean(),
                "avg_funding_rate": df['funding_rate'].mean(),
                "avg_price_change": df['price_change_percent_24h'].mean()
            }
        }
        
        # 添加新警报信号统计
        if self.enable_new_alert_conditions:
            alert_signals = self.get_alert_signals(df, 5)
            report["alert_signals"] = len(df[df.get('alert_signal', False)])
            report["top_alert_signals"] = alert_signals.to_dict('records')
            
            # 添加新指标统计
            if 'oi_surge_ratio' in df.columns:
                report["summary_stats"]["avg_oi_surge_ratio"] = df['oi_surge_ratio'].mean()
            if 'funding_rate_abs' in df.columns:
                report["summary_stats"]["avg_funding_rate_abs"] = df['funding_rate_abs'].mean()
        
        return report
    
    def print_analysis(self, df: pd.DataFrame):
        """打印分析结果"""
        if df.empty:
            print("没有数据可供分析")
            return
        
        print("=" * 80)
        print("📊 币安永续合约交易信号分析报告")
        print("=" * 80)
        
        # 基本统计信息
        total_symbols = len(df)
        buy_signals = len(df[df['buy_signal']])
        sell_signals = len(df[df['sell_signal']])
        strong_signals = len(df[df['signal_strength'] > 80])
        
        print(f"📈 分析币种: {total_symbols}")
        print(f"🔥 买入信号: {buy_signals}")
        print(f"🚨 卖出信号: {sell_signals}")
        print(f"💪 强信号: {strong_signals}")
        print(f"📊 平均信号强度: {df['signal_strength'].mean():.1f}")
        print(f"⚠️  平均风险评分: {df['risk_score'].mean():.1f}")
        
        # 新警报信号统计
        if self.enable_new_alert_conditions:
            alert_signals = len(df[df.get('alert_signal', False)])
            print(f"🚨 OI异常警报: {alert_signals}")
            
            if 'oi_surge_ratio' in df.columns:
                print(f"📈 平均OI激增比率: {df['oi_surge_ratio'].mean():.2f}")
            if 'funding_rate_abs' in df.columns:
                print(f"💰 平均资金费率绝对值: {df['funding_rate_abs'].mean()*100:.3f}%")
        
        print()
        
        # 推荐买入信号
        buy_signals_df = df[df['buy_signal']].copy()
        if not buy_signals_df.empty:
            print("\n🔥 推荐买入信号:")
            print("-" * 80)
            for _, row in buy_signals_df.head(5).iterrows():
                # 格式化市值显示
                market_cap = row['market_cap_estimate']
                if market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap/1e3:.0f}K"
                
                print(f"📈 {row['symbol']:>10} | "
                      f"信号强度: {row['signal_strength']:>5.1f} | "
                      f"风险评分: {row['risk_score']:>5.1f} | "
                      f"OI/市值: {row['oi_market_cap_ratio']:>5.2f} | "
                      f"市值: {market_cap_str:>8} | "
                      f"价格: ${row['price']:>10,.2f} | "
                      f"24h变化: {row['price_change_percent_24h']:>6.2f}%")
                print(f"   描述: {row['signal_description']}")
                print()
        else:
            print("\n暂无推荐买入信号\n")
        
        # 新警报信号
        if self.enable_new_alert_conditions:
            alert_signals_df = self.get_alert_signals(df, 5)
            if not alert_signals_df.empty:
                print("\n🚨 OI异常警报信号:")
                print("-" * 80)
                for _, row in alert_signals_df.iterrows():
                    # 格式化市值显示
                    market_cap = row['market_cap_estimate']
                    if market_cap >= 1e9:
                        market_cap_str = f"${market_cap/1e9:.2f}B"
                    elif market_cap >= 1e6:
                        market_cap_str = f"${market_cap/1e6:.1f}M"
                    else:
                        market_cap_str = f"${market_cap/1e3:.0f}K"
                    
                    print(f"🚨 {row['symbol']:>10} | "
                          f"资金费率: {row['funding_rate']*100:>6.3f}% | "
                          f"OI激增: {row['oi_surge_ratio']:>5.2f}x | "
                          f"市值: {market_cap_str:>8} | "
                          f"价格: ${row['price']:>10,.2f} | "
                          f"24h变化: {row['price_change_percent_24h']:>6.2f}%")
                    print(f"   描述: {row['signal_description']}")
                    print()
            else:
                print("\n暂无OI异常警报信号\n")
        
        # 推荐卖出信号
        sell_signals_df = df[df['sell_signal']].copy()
        if not sell_signals_df.empty:
            print("\n🚨 推荐卖出信号:")
            print("-" * 80)
            for _, row in sell_signals_df.head(5).iterrows():
                # 格式化市值显示
                market_cap = row['market_cap_estimate']
                if market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap/1e3:.0f}K"
                
                print(f"🚨 {row['symbol']:>10} | "
                      f"风险评分: {row['risk_score']:>5.1f} | "
                      f"市值: {market_cap_str:>8} | "
                      f"价格: ${row['price']:>10,.2f} | "
                      f"24h变化: {row['price_change_percent_24h']:>6.2f}%")
                print(f"   描述: {row['signal_description']}")
                print()
        
        # 高风险交易对
        high_risk = df[df['risk_score'] > 70].copy()
        if not high_risk.empty:
            print("\n⚠️  高风险交易对:")
            print("-" * 80)
            for _, row in high_risk.head(3).iterrows():
                # 格式化市值显示
                market_cap = row['market_cap_estimate']
                if market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap/1e3:.0f}K"
                
                print(f"🚨 {row['symbol']:>10} | "
                      f"风险评分: {row['risk_score']:>5.1f} | "
                      f"市值: {market_cap_str:>8} | "
                      f"价格: ${row['price']:>10,.2f} | "
                      f"24h变化: {row['price_change_percent_24h']:>6.2f}%")
        
        print("\n" + "="*80) 