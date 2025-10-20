import asyncio
import aiohttp
import orjson
from utils import save_json, get_timestamp
from config import MARKETWATCH_URLS
from schemas import ClientTypeResponse


def _extract_items(data: dict):
    """Safely extract marketwatch list."""
    if not data:
        return []
    return data.get("marketwatch", [])


async def fetch_market_data(session: aiohttp.ClientSession, url: str, market_type: str) -> list:
    """Fetch market data from TSETMC API and tag with market type."""
    async with session.get(url, timeout=30) as resp:
        resp.raise_for_status()
        raw = await resp.read()
    data = orjson.loads(raw)
    items = _extract_items(data)
    # Tag each item with market type
    for item in items:
        item["market_type"] = market_type
    return items


async def fetch_client_type_data(session: aiohttp.ClientSession) -> dict:
    """Fetch client type data from TSETMC API."""
    url = "https://cdn.tsetmc.com/api/ClientType/GetClientTypeAll"
    async with session.get(url, timeout=30) as resp:
        resp.raise_for_status()
        raw = await resp.read()
    return orjson.loads(raw)


async def fetch_merged_data(urls_dict: dict = None):
    """Fetch market data from multiple sources concurrently and merge results."""
    if urls_dict is None:
        urls_dict = MARKETWATCH_URLS
    
    async with aiohttp.ClientSession() as session:
        # Create tasks for all URLs in the dict
        tasks = [
            fetch_market_data(session, url, market_type)
            for market_type, url in urls_dict.items()
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
    
    # Flatten all results into a single list
    all_items = []
    for items in results:
        all_items.extend(items)
    
    return {
        "marketwatch": all_items,
    }


async def fetch_additional_data():
    """Fetch additional data (client type) from TSETMC API."""
    async with aiohttp.ClientSession() as session:
        client_type_data = await fetch_client_type_data(session)
    
    # Parse and return as dict for easy storage
    client_type_response = ClientTypeResponse(**client_type_data)
    return {
        "additional_data": [item.model_dump() for item in client_type_response.clientTypeAllDto]
    }




async def main():
    timestamp = get_timestamp()
    export_dir = "export/market_watch"
    data = await fetch_merged_data()
    save_path = f"{export_dir}/market_watch_{timestamp}.json"
    save_json(data, save_path)


if __name__ == "__main__":
    asyncio.run(main())
