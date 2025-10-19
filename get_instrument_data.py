import json
import os
from datetime import datetime

import requests

from schemas import BestLimitsResponse, ClosingPriceResponse, TradeResponse


def get_closing_price_info(ins_code):
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    response = requests.get(url)
    data = response.json()
    return data


def get_best_limits(ins_code):
    url = f"https://cdn.tsetmc.com/api/BestLimits/{ins_code}"
    response = requests.get(url)
    data = response.json()
    return data


def get_trade(ins_code):
    url = f"https://cdn.tsetmc.com/api/Trade/GetTrade/{ins_code}"
    response = requests.get(url)
    data = response.json()
    return data


def get_price(ins_code):
    """Get price percentage (pDrCotVal) for a given instrument code."""
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    response = requests.get(url, timeout=10)
    
    if response.status_code != 200:
        raise ValueError(f"Instrument {ins_code} not found")
    
    data = response.json()
    return data["closingPriceInfo"]["pDrCotVal"]


def main():

    ins_code = 28854105556435129
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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
    with open(save_path_closing_price_info, "w", encoding="utf-8") as f:
        json.dump(data_closing_price_info, f, indent=2, ensure_ascii=False)

    save_path_best_limits = f"{instrument_code_dir}/best_limits_{timestamp}.json"
    with open(save_path_best_limits, "w", encoding="utf-8") as f:
        json.dump(data_best_limits, f, indent=2, ensure_ascii=False)

    save_path_trade = f"{instrument_code_dir}/trade_{timestamp}.json"
    with open(save_path_trade, "w", encoding="utf-8") as f:
        json.dump(data_trade, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
