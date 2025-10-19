import os
from datetime import datetime

import requests
import orjson
from utils import save_json, get_timestamp


def get_market_watch_data():
    url = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&industrialGroup=&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9&showTraded=false&withBestLimits=true&hEven=0&RefID=0"

    response = requests.get(url, timeout=30)  # 30 second timeout
    # Use orjson for faster JSON parsing instead of response.json()
    data = orjson.loads(response.content)
    return data


def main():
    timestamp = get_timestamp()
    export_dir = "export/market_watch"
    data = get_market_watch_data()
    save_path = f"{export_dir}/market_watch_{timestamp}.json"
    save_json(data, save_path)


if __name__ == "__main__":
    main()
