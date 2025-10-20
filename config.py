"""
Configuration for the stock-pulse project.
"""

from datetime import time
import pytz
import os

# Tehran timezone
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

# Market configuration
MARKET_OPEN_TIME = time(9, 0)   # 9:00 AM
MARKET_CLOSE_TIME = time(12, 30)  # 12:30 PM

# Trading days: Saturday (5), Sunday (6), Monday (0), Tuesday (1), Wednesday (2)
# weekday() returns Monday=0, Sunday=6
TRADING_DAYS = {0, 1, 2, 5, 6}  # Mon, Tue, Wed, Sat, Sun

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/market_watch.db")

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Performance configuration
WEBSOCKET_UPDATE_INTERVAL = float(os.getenv("WEBSOCKET_UPDATE_INTERVAL", "0.5"))  # seconds
