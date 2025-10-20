import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager, suppress
import json
import requests
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List

from get_instrument_data import get_price
from get_market_watch_data import get_market_watch_data
from schemas import MarketWatchResponse, PriceResponse, MarketStatusResponse
from utils import is_market_open
from config import TEHRAN_TZ, MARKET_CLOSE_TIME
from redis_client import get_redis
import orjson
from database import MarketWatchDB
from config import API_HOST, API_PORT, WEBSOCKET_UPDATE_INTERVAL


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
    title="Stock Pulse API", description="Get instrument price data", lifespan=lifespan
)
db = MarketWatchDB()


async def _save_snapshot_if_valid():
    """Fetch market watch and persist to DB transactionally if non-empty."""
    try:
        print("Fetching market watch data...")
        data_dict = await asyncio.to_thread(get_market_watch_data)
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
    except Exception as e:
        print(f"snapshot save failed: {e}")
        import traceback

        traceback.print_exc()


async def _market_close_watcher():
    """Save once at each 12:30 Tehran close; also save once if starting while closed."""
    # On startup, if closed, save once
    try:
        app.state._last_market_open = is_market_open()
        print(f"Market open on startup: {app.state._last_market_open}")
        if not app.state._last_market_open:
            print("Market is closed on startup. Saving initial snapshot...")
            await _save_snapshot_if_valid()
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


## Startup handled via lifespan above


@app.get("/marketwatch", response_model=MarketWatchResponse)
async def get_market_watch():
    """Get full market watch data.
    - Market open: fetch live
    - Market closed: serve from DB
    """
    try:
        if is_market_open():
            data = await asyncio.to_thread(get_market_watch_data)
            print("marketwatch live")
            # refresh redis live snapshot best-effort with 2-minute TTL
            try:
                r = await get_redis()
                await r.set("mw:snapshot", orjson.dumps(data), ex=120)
            except Exception:
                pass
            return MarketWatchResponse(**data)
        # Closed → from DB
        else:
            # try redis snapshot first
            try:
                r = await get_redis()
                blob = await r.get("mw:snapshot")
                if blob:
                    print("marketwatch redis")
                    # decode-responses=True returns str; use json.loads
                    return MarketWatchResponse(**json.loads(blob))
                else:
                    print("Redis key 'mw:snapshot' not found")
            except Exception as redis_err:
                print(f"Redis read failed: {redis_err}")

            # fallback to DB, then backfill Redis (2m TTL)
            print("Fetching from database...")
            mw = db.get_market_watch_from_db()
            try:
                r = await get_redis()
                await r.set("mw:snapshot", orjson.dumps(mw.model_dump()), ex=120)
                pipe = r.pipeline()
                for it in mw.marketwatch:
                    pipe.set(f"mw:inst:{it.insCode}:pdv", str(it.pdv), ex=120)
                await pipe.execute()
                print("Backfilled Redis from database")
            except Exception:
                pass
            return mw
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/market-status", response_model=MarketStatusResponse)
async def get_market_status():
    """Return current market open/closed status."""
    try:
        return MarketStatusResponse(is_market_open=is_market_open())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/debug/market-open")
async def debug_market_open():
    """Debug market open status."""
    now_teh = datetime.now(TEHRAN_TZ)
    return {
        "current_time_tehran": now_teh.isoformat(),
        "market_close_time": MARKET_CLOSE_TIME.isoformat(),
        "is_market_open": is_market_open(),
        "timezone": str(TEHRAN_TZ),
    }


@app.post("/debug/warm-cache")
async def warm_cache():
    """Manually warm up the Redis cache from database."""
    try:
        print("Manually warming up cache...")
        await _save_snapshot_if_valid()
        return {"status": "Cache warmed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache warm failed: {str(e)}")


@app.get("/debug/redis-check")
async def check_redis():
    """Check Redis connection and cached data."""
    try:
        r = await get_redis()

        # Try to get the snapshot
        blob = await r.get("mw:snapshot")

        # Count individual instrument caches
        keys = await r.keys("mw:inst:*:pdv")

        return {
            "redis_connected": True,
            "snapshot_exists": blob is not None,
            "snapshot_size_bytes": len(blob) if blob else 0,
            "cached_instruments": len(keys) if keys else 0,
        }
    except Exception as e:
        return {
            "redis_connected": False,
            "error": str(e),
        }


class PriceConnectionManager:
    """Manages WebSocket connections for price updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


manager = PriceConnectionManager()


@app.websocket("/ws/price")
async def price_websocket(websocket: WebSocket, ins_code: str):
    """
    Stream price change percentage (pDrCotVal) for a specific instrument.
    Usage:
        ws://localhost:8000/ws/price?ins_code=28854105556435129
    """
    await manager.connect(websocket)
    try:
        ins_code_int = int(ins_code)
        while True:
            # Closed → read pdv from DB; Open → live pDrCotVal
            if is_market_open():
                # Open hours: cache and use get_price (actual price) under a dedicated key
                value = None
                from_redis = False
                try:
                    r = await get_redis()
                    v = await r.get(f"mw:inst:{ins_code}:price")
                    if v is not None:
                        value = float(v)
                        from_redis = True
                except Exception:
                    pass

                if value is None:
                    value = get_price(ins_code_int)
                    try:
                        r = await get_redis()
                        await r.set(f"mw:inst:{ins_code}:price", str(value), ex=120)
                    except Exception:
                        pass

                print("price from redis" if from_redis else "price from live")
            else:
                # closed: try redis hot field, fallback to db; set 2-minute TTL on writes
                value = None
                from_redis = False
                try:
                    r = await get_redis()
                    v = await r.get(f"mw:inst:{ins_code}:pdv")
                    if v is not None:
                        value = float(v)
                        from_redis = True
                except Exception:
                    pass

                if value is None:
                    value = db.get_pdv_by_ins_code(ins_code)
                    try:
                        if value is not None:
                            r = await get_redis()
                            await r.set(f"mw:inst:{ins_code}:pdv", str(value), ex=120)
                    except Exception:
                        pass

                if value is None:
                    # fallback minimal
                    value = 0.0

                print("price from redis" if from_redis else "price from db")

            await websocket.send_text(str(value))
            await asyncio.sleep(WEBSOCKET_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        manager.disconnect(websocket)


@app.get("/ws-price-test", response_class=HTMLResponse, include_in_schema=False)
async def price_websocket_test():
    """Simple test page for price WebSocket."""
    html_content = """
    <html>
    <body>
        <h3>Price WebSocket Test</h3>
        <input id="ins_code" value="28854105556435129" />
        <button onclick="connect()">Connect</button>
        <div id="log"></div>

        <script>
            let ws;
            function connect() {
                const insCode = document.getElementById('ins_code').value;
                const log = document.getElementById('log');
                log.innerHTML = `Connecting to ${insCode}...<br>`;
                ws = new WebSocket(`ws://${location.host}/ws/price?ins_code=${insCode}`);
                ws.onopen = () => log.innerHTML += "Connected<br>";
                ws.onmessage = (e) => {
                    log.innerHTML += e.data + "<br>";
                };
                ws.onclose = () => log.innerHTML += "Disconnected<br>";
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)
