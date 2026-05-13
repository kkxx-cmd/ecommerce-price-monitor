"""
配置管理 - 电商价格监控系统
"""

import os
from pathlib import Path

# ========== 基础路径 ==========
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "prices.db"

# ========== GitHub & Telegram ==========
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ========== 爬虫全局设置 ==========
# 请求间隔（秒），防止被封
REQUEST_DELAY_MIN = 2
REQUEST_DELAY_MAX = 5

# 价格变化阈值（%），超过才告警
PRICE_CHANGE_THRESHOLD = 5.0

# 最多重试次数
MAX_RETRIES = 3

# 请求头模拟浏览器
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ========== 监控商品配置 ==========
# 格式: {商品ID: {"platform": "jd|taobao|pdd", "url": "链接", "name": "名称"}}
# 用户需要在自己的 data/products.json 中配置，或者通过环境变量传入
PRODUCTS_CONFIG = os.getenv("PRODUCTS_CONFIG", "")

def load_products():
    """加载商品配置，支持多来源"""
    products_file = DATA_DIR / "products.json"
    if products_file.exists():
        import json
        with open(products_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}