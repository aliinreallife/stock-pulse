from fastapi import APIRouter, HTTPException
from schemas import MarketWatchResponse, MarketStatusResponse
from utils import is_market_open
from get_market_watch_data import get_market_watch_data
from database import MarketWatchDB
from config import DEBUG, get_redis
from config import TEHRAN_TZ, MARKET_CLOSE_TIME, REDIS_TTL_SECONDS
import orjson
import json
import asyncio

router = APIRouter()
db = MarketWatchDB()


async def _backfill_snapshot_async(data_dict: dict, mw_resp: MarketWatchResponse) -> None:
    """Backfill Redis snapshot and pdv hot keys in the background."""
    try:
        r = await get_redis()
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
            data_dict = await asyncio.to_thread(get_market_watch_data)
            mw_resp = MarketWatchResponse(**data_dict)
            if DEBUG:
                print("marketwatch live")
        else:
            mw_resp = db.get_market_watch_from_db()
            data_dict = mw_resp.model_dump()
            if DEBUG:
                print("marketwatch db")

        # Fire-and-forget backfill after sending response
        asyncio.create_task(_backfill_snapshot_async(data_dict, mw_resp))
        return mw_resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/market-status", response_model=MarketStatusResponse)
async def get_market_status():
    try:
        return MarketStatusResponse(is_market_open=is_market_open())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


