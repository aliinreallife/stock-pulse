import json
import os
from datetime import datetime

import requests


def get_market_watch_data():
    url = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&industrialGroup=&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9&showTraded=false&withBestLimits=true&hEven=0&RefID=0"

    response = requests.get(url)
    data = response.json()
    return data





def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = "export/market_watch"
    os.makedirs(export_dir, exist_ok=True)
    data = get_market_watch_data()
    save_path = f"{export_dir}/market_watch_{timestamp}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()