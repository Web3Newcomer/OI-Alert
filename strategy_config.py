"""
币安永续合约交易信号策略配置文件
所有策略参数都可以在这里调整
"""

class StrategyConfig:
    """交易信号策略配置"""
    
    # ==================== 核心策略参数 ====================
    
    # OI/市值比率阈值
    OI_MARKET_CAP_RATIO_THRESHOLD = 0.5  # OI/市值 > 0.5 时认为信号强
    
    # 最小OI价值 (USDT)
    MIN_OI_VALUE = 5_000_000  # 最小OI价值 5M USDT
    
    # 成交量/市值比率阈值
    VOLUME_MARKET_CAP_RATIO_THRESHOLD = 0.1  # 成交量/市值 > 0.1
    
    # 信号强度阈值
    SIGNAL_STRENGTH_THRESHOLD = 60  # 信号强度 > 60 才生成买入信号
    
    # ==================== 市值估算参数 ====================
    
    # 注意：现在使用 local_supply.py 中的真实流通量数据
    # 以下配置仅作为备用方案，当本地数据不可用时使用
    
    # 其他币种流通量估算（备用方案）
    OTHER_COINS_CIRCULATION = 1_000_000_000  # 其他币种默认10亿流通量
    
    # ==================== 信号强度计算权重 ====================
    
    # OI/市值比率得分权重 (总分40分)
    OI_RATIO_WEIGHT = 40
    
    # OI价值得分权重 (总分20分)
    OI_VALUE_WEIGHT = 20
    
    # 成交量得分权重 (总分20分)
    VOLUME_WEIGHT = 20
    
    # 资金费率得分权重 (总分10分)
    FUNDING_RATE_WEIGHT = 10
    
    # 价格动量得分权重 (总分10分)
    MOMENTUM_WEIGHT = 10
    
    # ==================== 风险评分参数 ====================
    
    # 价格波动风险权重 (总分30分)
    VOLATILITY_RISK_WEIGHT = 30
    
    # 资金费率风险权重 (总分20分)
    FUNDING_RISK_WEIGHT = 20
    
    # 流动性风险权重 (总分30分)
    LIQUIDITY_RISK_WEIGHT = 30
    
    # 市值风险权重 (总分20分)
    MARKET_CAP_RISK_WEIGHT = 20
    
    # 风险阈值
    MAX_RISK_SCORE = 70  # 最大风险评分阈值
    
    # ==================== 过滤条件 ====================
    
    # 最小市值过滤 (USDT)
    MIN_MARKET_CAP = 100_000_000  # 最小市值1亿
    
    # 最小价格过滤 (USDT)
    MIN_PRICE = 0.1  # 最小价格0.1美元
    
    # 最小24小时成交量过滤 (USDT)
    MIN_24H_VOLUME = 10_000_000  # 最小24小时成交量1000万
    
    # 资金费率过滤
    MAX_FUNDING_RATE = 0.001  # 最大资金费率0.1%
    MIN_FUNDING_RATE = -0.001  # 最小资金费率-0.1%
    
    # 价格波动过滤
    MAX_PRICE_CHANGE_24H = 0.1  # 最大24小时价格变化10%
    
    # ==================== 卖出信号参数 ====================
    
    # 卖出信号条件
    SELL_OI_MARKET_CAP_RATIO = 0.2  # OI/市值 < 0.2
    SELL_SIGNAL_STRENGTH = 30  # 信号强度 < 30
    SELL_FUNDING_RATE = -0.0001  # 负资金费率
    
    # ==================== 策略预设 ====================
    
    @classmethod
    def get_conservative_config(cls):
        """保守策略配置"""
        config = cls()
        config.OI_MARKET_CAP_RATIO_THRESHOLD = 0.8
        config.MIN_OI_VALUE = 10_000_000
        config.VOLUME_MARKET_CAP_RATIO_THRESHOLD = 0.15
        config.SIGNAL_STRENGTH_THRESHOLD = 75
        config.MAX_RISK_SCORE = 50
        return config
    
    @classmethod
    def get_aggressive_config(cls):
        """激进策略配置"""
        config = cls()
        config.OI_MARKET_CAP_RATIO_THRESHOLD = 0.3
        config.MIN_OI_VALUE = 2_000_000
        config.VOLUME_MARKET_CAP_RATIO_THRESHOLD = 0.05
        config.SIGNAL_STRENGTH_THRESHOLD = 50
        config.MAX_RISK_SCORE = 80
        return config
    
    @classmethod
    def get_balanced_config(cls):
        """平衡策略配置"""
        config = cls()
        config.OI_MARKET_CAP_RATIO_THRESHOLD = 0.5
        config.MIN_OI_VALUE = 5_000_000
        config.VOLUME_MARKET_CAP_RATIO_THRESHOLD = 0.1
        config.SIGNAL_STRENGTH_THRESHOLD = 60
        config.MAX_RISK_SCORE = 70
        return config

 