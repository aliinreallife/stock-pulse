import asyncio
import json
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from typing import List

import orjson
import requests
from fastapi import (FastAPI, HTTPException, Query, WebSocket,
                     WebSocketDisconnect)
from fastapi.responses import HTMLResponse

from app.routers.marketwatch import router as market_router
from app.websocket.price import router as ws_router
from config import (API_HOST, API_PORT, MARKET_CLOSE_TIME, TEHRAN_TZ,
                    WEBSOCKET_UPDATE_INTERVAL, get_redis)
from database import MarketWatchDB
from get_instrument_data import get_price
from get_market_watch_data import fetch_merged_data
from schemas import MarketStatusResponse, MarketWatchResponse, PriceResponse
from utils import is_market_open


@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize shared state
    app.state._last_market_open = None
    app.state._last_snapshot_date = None
    app.state._watcher_task = asyncio.create_task(_market_close_watcher())
    try:
        yield
    finally:
        app.state._watcher_task.cancel()
        with suppress(asyncio.CancelledError):
            await app.state._watcher_task


app = FastAPI(
    title="Stock Pulse API", 
    description="Get instrument price data", 
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)
db = MarketWatchDB()

# Register routers
app.include_router(market_router, tags=["market"])
app.include_router(ws_router, tags=["websocket"])


async def _save_snapshot_if_valid():
    """Fetch market watch and persist to DB transactionally if non-empty."""
    try:
        print("Fetching market watch data...")
        data_dict = await fetch_merged_data()
        print(
            f"Market watch data fetched successfully, items: {len(data_dict.get('marketwatch', []))}"
        )

        mw = MarketWatchResponse(**data_dict)

        # Persist to DB
        db.save_market_watch_data(mw)
        print("Market watch data saved to database")

        # Cache in Redis with 2m TTL (best-effort)
        try:
            r = await get_redis()
            await r.set("mw:snapshot", orjson.dumps(data_dict), ex=120)
            print("Market watch snapshot saved to Redis")

            pipe = r.pipeline()
            for it in mw.marketwatch:
                # store numeric values as strings
                pipe.set(f"mw:inst:{it.insCode}:pdv", str(it.pdv), ex=120)
            await pipe.execute()

        except Exception as redis_err:
            print(f"Redis caching failed: {redis_err}")
    except asyncio.TimeoutError:
        print("Market watch data fetch timed out after 30s - skipping snapshot")
    except Exception as e:
        print(f"snapshot save failed: {e}")
        import traceback

        traceback.print_exc()


async def _market_close_watcher():
    """Save once at each 12:30 Tehran close; also save once if starting while closed."""
    # On startup, if closed, save once (non-blocking)
    try:
        app.state._last_market_open = is_market_open()
        print(f"Market open on startup: {app.state._last_market_open}")
        if not app.state._last_market_open:
            print("Market is closed on startup. Saving initial snapshot in background...")
            # Run in background to not block startup
            asyncio.create_task(_save_snapshot_if_valid())
    except Exception as e:
        print(f"initial market state check failed: {e}")

    while True:
        try:
            now_teh = datetime.now(TEHRAN_TZ)
            target_close = now_teh.replace(
                hour=MARKET_CLOSE_TIME.hour,
                minute=MARKET_CLOSE_TIME.minute,
                second=0,
                microsecond=0,
            )
            if now_teh >= target_close:
                target_close += timedelta(days=1)

            sleep_seconds = (target_close - now_teh).total_seconds()
            if sleep_seconds > 0:
                await asyncio.sleep(sleep_seconds)

            # At/after scheduled close → save once per day
            now_teh = datetime.now(TEHRAN_TZ)
            if app.state._last_snapshot_date != now_teh.date():
                print(f"Market close time reached. Saving snapshot...")
                await _save_snapshot_if_valid()
                app.state._last_snapshot_date = now_teh.date()
        except Exception as e:
            print(f"market watcher error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)
