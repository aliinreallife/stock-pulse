import asyncio
import aiohttp
import orjson
from utils import save_json, get_timestamp
from config import MARKETWATCH_URLS


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
            fetch_json(session, MARKETWATCH_URLS["stock_market"], "stock_market"),
            fetch_json(session, MARKETWATCH_URLS["base_market"], "base_market"),
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
