"""
Utility functions for the stock-pulse project.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import orjson


def save_json(data: Any, filepath: str, indent: int = 2) -> None:
    """
    Save data to a JSON file using orjson for better performance.

    Args:
        data: The data to save (must be JSON serializable)
        filepath: Path to the file to save
        indent: Number of spaces for indentation (default: 2)
    """
    # Ensure directory exists if there's a directory in the path
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    # Use orjson for serialization
    json_bytes = orjson.dumps(data, option=orjson.OPT_INDENT_2 if indent else 0)

    with open(filepath, "wb") as f:
        f.write(json_bytes)


def load_json(filepath: str) -> Union[Dict, List, Any]:
    """
    Load data from a JSON file using orjson for better performance.

    Args:
        filepath: Path to the JSON file to load

    Returns:
        The loaded data (dict, list, or other JSON-serializable type)
    """
    with open(filepath, "rb") as f:
        return orjson.loads(f.read())


def json_dumps(data: Any, indent: int = 2) -> str:
    """
    Convert data to JSON string using orjson.

    Args:
        data: The data to serialize
        indent: Number of spaces for indentation (default: 2)

    Returns:
        JSON string
    """
    json_bytes = orjson.dumps(data, option=orjson.OPT_INDENT_2 if indent else 0)
    return json_bytes.decode("utf-8")


def json_loads(json_str: str) -> Union[Dict, List, Any]:
    """
    Parse JSON string using orjson.

    Args:
        json_str: The JSON string to parse

    Returns:
        The parsed data
    """
    return orjson.loads(json_str.encode("utf-8"))


def ensure_directory_exists(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory
    """
    os.makedirs(directory, exist_ok=True)


def get_timestamp() -> str:
    """
    Get current timestamp in YYYYMMDD_HHMMSS format.

    Returns:
        Formatted timestamp string
    """
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_iso_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO formatted timestamp string
    """
    from datetime import datetime

    return datetime.now().isoformat()


def is_market_open(check_time: Optional[datetime] = None) -> bool:
    """
    Check if market is currently open.

    Market is open:
    - On trading days (Saturday to Wednesday)
    - Between 9:00 AM and 12:30 PM Tehran time

    Args:
        check_time: Time to check (defaults to current Tehran time)

    Returns:
        True if market is open
    """
    from config import (MARKET_CLOSE_TIME, MARKET_OPEN_TIME, TEHRAN_TZ,
                        TRADING_DAYS)

    if check_time is None:
        check_time = datetime.now(TEHRAN_TZ)

    # Convert to Tehran timezone if needed
    if check_time.tzinfo is None:
        check_time = TEHRAN_TZ.localize(check_time)
    elif check_time.tzinfo != TEHRAN_TZ:
        check_time = check_time.astimezone(TEHRAN_TZ)

    # Check if it's a trading day
    if check_time.weekday() not in TRADING_DAYS:
        return False

    # Check if within trading hours
    current_time = check_time.time()

    market_open_flag = MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME
    return market_open_flag
