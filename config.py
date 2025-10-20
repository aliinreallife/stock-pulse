"""
Configuration for the stock-pulse project.
"""

import os
from datetime import time

import pytz
import redis.asyncio as redis

# Tehran timezone
TEHRAN_TZ = pytz.timezone("Asia/Tehran")

# Market configuration
MARKET_OPEN_TIME = time(9, 0)  # 9:00 AM
MARKET_CLOSE_TIME = time(12, 30)  # 12:30 PM

# Trading days: Saturday (5), Sunday (6), Monday (0), Tuesday (1), Wednesday (2)
# weekday() returns Monday=0, Sunday=6
TRADING_DAYS = {0, 1, 2, 5, 6}  # Mon, Tue, Wed, Sat, Sun

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/market_watch.db")

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TTL_SECONDS = int(os.getenv("REDIS_TTL_SECONDS", "120"))

# Redis client (async) - shared accessor
_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = await redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Performance configuration
WEBSOCKET_UPDATE_INTERVAL = float(
    os.getenv("WEBSOCKET_UPDATE_INTERVAL", "0.5")
)  # seconds

DEBUG = os.getenv("DEBUG", "true") == "true"

# TSETMC MarketWatch base
TSETMC_BASE = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch"

# Prebuilt MarketWatch URLs (hEven=0; caller may override if needed)
MARKETWATCH_URLS = {
    # Stock market (paperTypes=1)
    "stock_market": (
        f"{TSETMC_BASE}?market=0&industrialGroup=&paperTypes%5B0%5D=1"
        f"&showTraded=false&withBestLimits=true&hEven=0&RefID=0"
    ),
    # Base market (paperTypes=2)
    "base_market": (
        f"{TSETMC_BASE}?market=0&industrialGroup=&paperTypes%5B0%5D=2"
        f"&showTraded=false&withBestLimits=true&hEven=0&RefID=0"
    ),
}

STOCK_BASE_COMBINED = f"{TSETMC_BASE}?market=0&industrialGroup=&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&showTraded=false&withBestLimits=true&hEven=0&RefID=0"
