"""
Configuration for the stock-pulse project.
"""

import os
from datetime import time

import pytz
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

# Tehran timezone
TEHRAN_TZ = pytz.timezone("Asia/Tehran")

# Market configuration
MARKET_OPEN_TIME = time(9, 0)  # 9:00 AM
MARKET_CLOSE_TIME = time(12, 30)  # 12:30 PM

# Trading days: Saturday (5), Sunday (6), Monday (0), Tuesday (1), Wednesday (2)
# weekday() returns Monday=0, Sunday=6
TRADING_DAYS = {0, 1, 2, 5, 6}  # Mon, Tue, Wed, Sat, Sun

# Database configuration
DATA_DIR = os.getenv("DATA_DIR", "data")
DATABASE_PATH = os.path.join(DATA_DIR, "market_watch.db")

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TTL_SECONDS = int(os.getenv("REDIS_TTL_SECONDS", "120"))
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# Redis client (async) - shared accessor
_redis = None
_redis_available = None


async def get_redis():
    """Get Redis client if available, return None if Redis is disabled or unavailable."""
    global _redis, _redis_available

    if not REDIS_ENABLED:
        return None

    if _redis_available is False:
        return None

    if _redis is None:
        try:
            _redis = await redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            await _redis.ping()
            _redis_available = True
        except Exception as e:
            if _redis_available is None:  # Only show warning on first failure
                print(f"Warning: Redis connection failed: {e}")
            _redis_available = False
            _redis = None
            return None

    return _redis


# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Performance configuration
WEBSOCKET_UPDATE_INTERVAL = float(
    os.getenv("WEBSOCKET_UPDATE_INTERVAL", "0.5")
)  # seconds

DEBUG = os.getenv("DEBUG", "false") == "true"

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
