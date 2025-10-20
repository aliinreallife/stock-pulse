import asyncio
import os
from datetime import datetime

import aiohttp
import orjson

from schemas import BestLimitsResponse, ClosingPriceResponse, TradeResponse
from utils import save_json, get_timestamp


async def fetch_instrument_data(session: aiohttp.ClientSession, url: str) -> dict:
    """Fetch instrument data from TSETMC API."""
    async with session.get(url, timeout=30) as resp:
        resp.raise_for_status()
        raw = await resp.read()
    return orjson.loads(raw)


async def get_closing_price_info(ins_code: int) -> dict:
    """Get closing price info for an instrument."""
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    async with aiohttp.ClientSession() as session:
        return await fetch_instrument_data(session, url)


async def get_best_limits(ins_code: int) -> dict:
    """Get best limits for an instrument."""
    url = f"https://cdn.tsetmc.com/api/BestLimits/{ins_code}"
    async with aiohttp.ClientSession() as session:
        return await fetch_instrument_data(session, url)


async def get_trade(ins_code: int) -> dict:
    """Get trade data for an instrument."""
    url = f"https://cdn.tsetmc.com/api/Trade/GetTrade/{ins_code}"
    async with aiohttp.ClientSession() as session:
        return await fetch_instrument_data(session, url)


async def get_price(ins_code: int) -> float:
    """Get price change percentage (pDrCotVal) for a given instrument code."""
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                raise ValueError(f"Instrument {ins_code} not found")
            raw = await resp.read()
    
    data = orjson.loads(raw)
    return data["closingPriceInfo"]["pDrCotVal"]


# Synchronous wrappers for backward compatibility
def get_closing_price_info_sync(ins_code: int) -> dict:
    """Synchronous wrapper for get_closing_price_info."""
    return asyncio.run(get_closing_price_info(ins_code))


def get_best_limits_sync(ins_code: int) -> dict:
    """Synchronous wrapper for get_best_limits."""
    return asyncio.run(get_best_limits(ins_code))


def get_trade_sync(ins_code: int) -> dict:
    """Synchronous wrapper for get_trade."""
    return asyncio.run(get_trade(ins_code))


def get_price_sync(ins_code: int) -> float:
    """Synchronous wrapper for get_price."""
    return asyncio.run(get_price(ins_code))


async def main():
    ins_code = 28854105556435129
    timestamp = get_timestamp()

    # Create directory structure: export/instrument/{ins_code}/
    instrument_code_dir = f"export/instrument/{ins_code}"
    os.makedirs(instrument_code_dir, exist_ok=True)

    # Get data from APIs concurrently
    async with aiohttp.ClientSession() as session:
        data_closing_price_info, data_best_limits, data_trade = await asyncio.gather(
            fetch_instrument_data(session, f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"),
            fetch_instrument_data(session, f"https://cdn.tsetmc.com/api/BestLimits/{ins_code}"),
            fetch_instrument_data(session, f"https://cdn.tsetmc.com/api/Trade/GetTrade/{ins_code}"),
        )

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
    asyncio.run(main())
