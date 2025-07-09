import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 币安API配置
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    
    # 是否使用测试网
    USE_TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
    
    # 数据收集配置
    TOP_VOLUME_LIMIT = 100  # 只分析成交量前100的币种
    USE_VOLUME_FILTER = True  # 是否启用成交量过滤
    USE_LOCAL_SYMBOLS = False  # True=只用本地币种，False=用API获取币种
    
    # API调用配置
    API_DELAY = 0.1  # API调用间隔（秒）
    MAX_RETRIES = 3  # 最大重试次数
    REQUEST_TIMEOUT = 30  # 请求超时时间（秒）
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    
    # 企业微信配置
    WECHAT_WEBHOOK_URL = os.getenv('WECHAT_WEBHOOK_URL', 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d0a09574-50c3-4067-957a-fbdb13125870')  # 企业微信webhook地址
    ENABLE_WECHAT_NOTIFICATION = os.getenv('ENABLE_WECHAT_NOTIFICATION', 'true').lower() == 'true'  # 是否启用企业微信通知
    
    # CoinMarketCap API 配置（用于补充流通量数据）
    COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', '46d7b96c-791c-4a9f-8b15-8380d9087509')  # CoinMarketCap API Key
    ENABLE_COINMARKETCAP = os.getenv('ENABLE_COINMARKETCAP', 'true').lower() == 'true'  # 是否启用 CoinMarketCap 作为备用数据源 