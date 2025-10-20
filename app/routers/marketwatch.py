from fastapi import APIRouter, HTTPException
from schemas import MarketWatchResponse, MarketStatusResponse, MarketWatchWithAdditionalDataResponse, ClientTypeItem
from utils import is_market_open
from get_market_watch_data import fetch_merged_data, fetch_additional_data
from database import MarketWatchDB
from config import DEBUG, get_redis
from config import TEHRAN_TZ, MARKET_CLOSE_TIME, REDIS_TTL_SECONDS
import orjson
import json
import asyncio

router = APIRouter()
db = MarketWatchDB()


async def _backfill_snapshot_async(mw_resp: MarketWatchResponse) -> None:
    """Backfill Redis snapshot and pdv hot keys in the background."""
    try:
        r = await get_redis()
        # Use the Pydantic model's dict() method for consistency
        data_dict = mw_resp.model_dump()
        await r.set("mw:snapshot", orjson.dumps(data_dict), ex=REDIS_TTL_SECONDS)
        pipe = r.pipeline()
        for it in mw_resp.marketwatch:
            pipe.set(f"mw:inst:{it.insCode}:pdv", str(it.pdv), ex=REDIS_TTL_SECONDS)
        await pipe.execute()
    except Exception:
        # best-effort cache write; ignore errors
        pass

@router.get("/marketwatch", response_model=MarketWatchResponse)
async def get_market_watch():
    try:
        # Try Redis snapshot first (open/closed)
        r = None
        try:
            r = await get_redis()
            blob = await r.get("mw:snapshot")
            if blob:
                if DEBUG:
                    print("marketwatch redis")
                return MarketWatchResponse(**json.loads(blob))
        except Exception:
            r = None

        # Cache miss → fetch from source
        if is_market_open():
            data_dict = await fetch_merged_data()
            mw_resp = MarketWatchResponse(**data_dict)
            if DEBUG:
                print("marketwatch live")
        else:
            mw_resp = await asyncio.to_thread(db.get_market_watch_from_db)
            if DEBUG:
                print("marketwatch db")

        asyncio.create_task(_backfill_snapshot_async(mw_resp))
        return mw_resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/market-status", response_model=MarketStatusResponse)
async def get_market_status():
    try:
        return MarketStatusResponse(is_market_open=is_market_open())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/marketwatch-with-additional-data", response_model=MarketWatchWithAdditionalDataResponse)
async def get_market_watch_with_additional_data():
    """Get market watch data with additional client type information."""
    try:
        # Initialize variables
        mw_resp = None
        additional_data = None
        mw_from_redis = False
        additional_from_redis = False
        
        # Try Redis for both market watch and additional data
        try:
            r = await get_redis()
            mw_blob = await r.get("mw:snapshot")
            additional_blob = await r.get("mw:additional_data")
            
            if mw_blob:
                mw_resp = MarketWatchResponse(**json.loads(mw_blob))
                mw_from_redis = True
                if DEBUG:
                    print("marketwatch from redis")
            
            if additional_blob:
                additional_data = json.loads(additional_blob)
                additional_from_redis = True
                if DEBUG:
                    print("additional data from redis")
                    
        except Exception:
            pass
        
        # Fetch missing data based on what we have
        if mw_resp is None:
            if is_market_open():
                data_dict = await fetch_merged_data()
                mw_resp = MarketWatchResponse(**data_dict)
                if DEBUG:
                    print("marketwatch from live")
            else:
                mw_resp = await asyncio.to_thread(db.get_market_watch_from_db)
                if DEBUG:
                    print("marketwatch from db")
            
            # Backfill Redis for market watch
            asyncio.create_task(_backfill_market_watch_async(mw_resp))
        
        if additional_data is None:
            if is_market_open():
                additional_data = await fetch_additional_data()
                if DEBUG:
                    print("additional data from live")
            else:
                additional_data_list = await asyncio.to_thread(db.get_additional_data_from_db)
                additional_data = {"additional_data": additional_data_list}
                if DEBUG:
                    print("additional data from db")
            
            # Backfill Redis for additional data
            asyncio.create_task(_backfill_additional_data_async(additional_data))
        
        # Merge market watch with additional data
        additional_map = {item["insCode"]: item for item in additional_data.get("additional_data", [])}

        merged_items = []
        for market_item in mw_resp.marketwatch:
            item_dict = market_item.model_dump()
            item_dict["additional_data"] = additional_map.get(market_item.insCode)
            merged_items.append(item_dict)

        return MarketWatchWithAdditionalDataResponse(marketwatch=merged_items)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


async def _backfill_market_watch_async(mw_resp: MarketWatchResponse) -> None:
    """Backfill Redis with market watch data in the background."""
    try:
        r = await get_redis()
        await r.set("mw:snapshot", orjson.dumps(mw_resp.model_dump()), ex=REDIS_TTL_SECONDS)
        if DEBUG:
            print("Market watch data backfilled to Redis")
    except Exception as e:
        if DEBUG:
            print(f"Failed to backfill market watch data to Redis: {e}")


async def _backfill_additional_data_async(additional_data: dict) -> None:
    """Backfill Redis with additional data in the background."""
    try:
        r = await get_redis()
        await r.set("mw:additional_data", orjson.dumps(additional_data), ex=REDIS_TTL_SECONDS)
    except Exception:
        # best-effort cache write; ignore errors
        pass


async def _fetch_and_cache_additional_data() -> None:
    """Fetch and cache additional data in the background."""
    try:
        additional_data = await fetch_additional_data()
        await _backfill_additional_data_async(additional_data)
    except Exception:
        # best-effort; ignore errors
        pass


