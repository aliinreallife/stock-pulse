"""
Configuration for the stock-pulse project.
"""

from datetime import time
import pytz

# Tehran timezone
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

# Market configuration
MARKET_OPEN_TIME = time(9, 0)   # 9:00 AM
MARKET_CLOSE_TIME = time(12, 30)  # 12:30 PM

# Trading days: Saturday (5), Sunday (6), Monday (0), Tuesday (1), Wednesday (2)
# weekday() returns Monday=0, Sunday=6
TRADING_DAYS = {0, 1, 2, 5, 6}  # Mon, Tue, Wed, Sat, Sun
