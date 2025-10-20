import asyncio
import aiohttp
import orjson
from utils import save_json, get_timestamp


URL_T1 = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&industrialGroup=&paperTypes%5B0%5D=1&showTraded=false&withBestLimits=true&hEven=0&RefID=0"
URL_T2 = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&industrialGroup=&paperTypes%5B0%5D=2&showTraded=false&withBestLimits=true&hEven=0&RefID=0"


def _extract_items(data: dict):
    """Safely extract marketwatch list."""
    if not data:
        return []
    return data.get("marketwatch", [])


async def fetch_json(session, url, market_type):
    """Fetch and tag data with market type."""
    async with session.get(url, timeout=30) as resp:
        resp.raise_for_status()
        raw = await resp.read()
    data = orjson.loads(raw)
    items = _extract_items(data)
    for it in items:
        it["market_type"] = market_type
    return items


async def fetch_merged_data():
    """Fetch paperType=1 and paperType=2 concurrently and merge results."""
    async with aiohttp.ClientSession() as session:
        stock_items, base_items = await asyncio.gather(
            fetch_json(session, URL_T1, "stock_market"),
            fetch_json(session, URL_T2, "base_market"),
        )

    return {
        "marketwatch": stock_items + base_items,
    }


def get_market_watch_data():
    """Synchronous wrapper for async fetch."""
    return asyncio.run(fetch_merged_data())


def main():
    timestamp = get_timestamp()
    export_dir = "export/market_watch"
    data = get_market_watch_data()
    save_path = f"{export_dir}/market_watch_{timestamp}.json"
    save_json(data, save_path)


if __name__ == "__main__":
    main()
