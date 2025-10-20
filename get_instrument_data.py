import os
from datetime import datetime

import requests
import orjson

from schemas import BestLimitsResponse, ClosingPriceResponse, TradeResponse
from utils import save_json, get_timestamp


def get_closing_price_info(ins_code):
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    response = requests.get(url)
    data = orjson.loads(response.content)
    return data


def get_best_limits(ins_code):
    url = f"https://cdn.tsetmc.com/api/BestLimits/{ins_code}"
    response = requests.get(url)
    data = orjson.loads(response.content)
    return data


def get_trade(ins_code):
    url = f"https://cdn.tsetmc.com/api/Trade/GetTrade/{ins_code}"
    response = requests.get(url)
    # Use orjson for faster JSON parsing instead of response.json()
    data = orjson.loads(response.content)
    return data


def get_price(ins_code):
    """Get price change percentage (pDrCotVal) for a given instrument code."""
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    response = requests.get(url, timeout=10)
    
    if response.status_code != 200:
        raise ValueError(f"Instrument {ins_code} not found")
    
    # Use orjson for faster JSON parsing instead of response.json()
    data = orjson.loads(response.content)
    return data["closingPriceInfo"]["pDrCotVal"]


def main():

    ins_code = 28854105556435129
    timestamp = get_timestamp()

    # Create directory structure: export/instrument/{ins_code}/
    instrument_code_dir = f"export/instrument/{ins_code}"
    os.makedirs(instrument_code_dir, exist_ok=True)

    # Get data from APIs
    data_closing_price_info = get_closing_price_info(ins_code)
    data_best_limits = get_best_limits(ins_code)
    data_trade = get_trade(ins_code)

    # Validate data with schemas
    try:
        closing_response = ClosingPriceResponse(**data_closing_price_info)
        best_limits_response = BestLimitsResponse(**data_best_limits)
        trade_response = TradeResponse(**data_trade)
    except Exception as e:
        print(f"Validation failed: {e}")
        exit(1)

    save_path_closing_price_info = (
        f"{instrument_code_dir}/closing_price_{timestamp}.json"
    )
    save_json(data_closing_price_info, save_path_closing_price_info)

    save_path_best_limits = f"{instrument_code_dir}/best_limits_{timestamp}.json"
    save_json(data_best_limits, save_path_best_limits)

    save_path_trade = f"{instrument_code_dir}/trade_{timestamp}.json"
    save_json(data_trade, save_path_trade)


if __name__ == "__main__":
    main()
