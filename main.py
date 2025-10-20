import asyncio
import json
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from typing import List

import orjson
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from config import (
    API_HOST,
    API_PORT,
    MARKET_CLOSE_TIME,
    TEHRAN_TZ,
    WEBSOCKET_UPDATE_INTERVAL,
    get_redis,
    DEBUG,
    REDIS_TTL_SECONDS,
)
from database import MarketWatchDB
from get_instrument_data import get_price
from get_market_watch_data import fetch_merged_data, fetch_additional_data
from schemas import MarketStatusResponse, MarketWatchResponse, PriceResponse, MarketWatchWithAdditionalDataResponse, ClientTypeItem
from utils import is_market_open


# WebSocket Connection Manager
class PriceConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


manager = PriceConnectionManager()


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
    redoc_url="/redoc",
)
db = MarketWatchDB()

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Stock Pulse", "status": "running"}


# Market Watch Endpoints
@app.get("/marketwatch", response_model=MarketWatchResponse)
async def get_market_watch():
    try:
        # Try Redis snapshot first (open/closed)
        r = await get_redis()
        if r is not None:
            try:
                blob = await r.get("mw:snapshot")
                if blob:
                    if DEBUG:
                        print("marketwatch redis")
                    return MarketWatchResponse(**json.loads(blob))
            except Exception:
                pass

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


@app.get("/market-status", response_model=MarketStatusResponse)
async def get_market_status():
    try:
        return MarketStatusResponse(is_market_open=is_market_open())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/marketwatch-with-additional-data", response_model=MarketWatchWithAdditionalDataResponse)
async def get_market_watch_with_additional_data():
    """Get market watch data with additional client type information."""
    try:
        # Initialize variables
        mw_resp = None
        additional_data = None
        mw_from_redis = False
        additional_from_redis = False
        
        # Try Redis for both market watch and additional data
        r = await get_redis()
        if r is not None:
            try:
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


# WebSocket Endpoints
@app.get("/ws-test", response_class=HTMLResponse, include_in_schema=False)
async def websocket_test_page():
    """Simple HTML page to test WebSocket price updates."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Price Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            input { padding: 8px; margin: 5px; width: 200px; }
            button { padding: 8px 16px; margin: 5px; }
            #output { 
                border: 1px solid #ccc; 
                padding: 10px; 
                height: 300px; 
                overflow-y: auto; 
                background: #f9f9f9;
                font-family: monospace;
            }
            .status { padding: 5px; margin: 5px 0; border-radius: 3px; }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket Price Test</h1>
            
            <div>
                <input type="text" id="insCode" placeholder="Enter insCode (e.g., 28854105556435129)" value="28854105556435129">
                <button onclick="connect()">Connect</button>
                <button onclick="disconnect()">Disconnect</button>
            </div>
            
            <div id="status" class="status disconnected">Disconnected</div>
            
            <div>
                <h3>Price Updates:</h3>
                <div id="output"></div>
            </div>
            
            <div>
                <h3>Instructions:</h3>
                <ul>
                    <li>Enter an instrument code (insCode) above</li>
                    <li>Click Connect to start receiving price updates</li>
                    <li>Updates will appear every 0.5 seconds</li>
                    <li>When market is open: shows price change percentage (pDrCotVal)</li>
                    <li>When market is closed: shows last price (pdv) from database</li>
                </ul>
            </div>
        </div>

        <script>
            let ws = null;
            let reconnectInterval = null;
            
            function connect() {
                const insCode = document.getElementById('insCode').value;
                if (!insCode) {
                    alert('Please enter an insCode');
                    return;
                }
                
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/price?ins_code=${insCode}`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    updateStatus('Connected', 'connected');
                    addOutput('Connected to WebSocket for insCode: ' + insCode);
                    clearInterval(reconnectInterval);
                };
                
                ws.onmessage = function(event) {
                    const price = parseFloat(event.data);
                    const timestamp = new Date().toLocaleTimeString();
                    addOutput(`[${timestamp}] Price: ${price}`);
                };
                
                ws.onclose = function(event) {
                    updateStatus('Disconnected', 'disconnected');
                    addOutput('WebSocket connection closed');
                };
                
                ws.onerror = function(error) {
                    updateStatus('Error', 'error');
                    addOutput('WebSocket error: ' + error);
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
                clearInterval(reconnectInterval);
            }
            
            function updateStatus(message, className) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = 'status ' + className;
            }
            
            function addOutput(message) {
                const output = document.getElementById('output');
                const div = document.createElement('div');
                div.textContent = message;
                output.appendChild(div);
                output.scrollTop = output.scrollHeight;
            }
            
            // Auto-connect on page load
            window.onload = function() {
                connect();
            };
        </script>
    </body>
    </html>
    """


@app.websocket("/ws/price")
async def price_websocket(websocket: WebSocket, ins_code: str):
    await manager.connect(websocket)
    try:
        ins_code_int = int(ins_code)
        while True:
            if is_market_open():
                value = None
                from_redis = False
                r = await get_redis()
                if r is not None:
                    try:
                        if DEBUG:
                            print(f"price from redis: {ins_code}")
                        v = await r.get(f"mw:inst:{ins_code}:price")
                        if v is not None:
                            value = float(v)
                            from_redis = True
                    except Exception:
                        pass
                if value is None:
                    value = await get_price(ins_code_int)
                    if DEBUG:
                        print(f"price from api: {ins_code}")
                    r = await get_redis()
                    if r is not None:
                        try:
                            if DEBUG:
                                print(f"price to redis: {ins_code}")
                            await r.set(f"mw:inst:{ins_code}:price", str(value), ex=REDIS_TTL_SECONDS)
                        except Exception:
                            pass
            else:
                value = None
                from_redis = False
                r = await get_redis()
                if r is not None:
                    try:
                        v = await r.get(f"mw:inst:{ins_code}:pdv")
                        if v is not None:
                            value = float(v)
                            from_redis = True
                            if DEBUG:
                                print(f"pdv from redis: {ins_code}")
                    except Exception:
                        pass
                if value is None:
                    value = await asyncio.to_thread(db.get_pdv_by_ins_code, ins_code)
                    if DEBUG:
                        print(f"pdv from db: {ins_code}")
                    if value is not None:
                        r = await get_redis()
                        if r is not None:
                            try:
                                await r.set(f"mw:inst:{ins_code}:pdv", str(value), ex=REDIS_TTL_SECONDS)
                            except Exception:
                                pass
                if value is None:
                    value = 0.0

            await websocket.send_text(str(value))
            await asyncio.sleep(WEBSOCKET_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# Helper functions for caching
async def _backfill_snapshot_async(mw_resp: MarketWatchResponse) -> None:
    """Backfill Redis snapshot and pdv hot keys in the background."""
    try:
        r = await get_redis()
        if r is None:
            return  # Redis not available
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
        if r is None:
            return  # Redis not available
        await r.set("mw:additional_data", orjson.dumps(additional_data), ex=REDIS_TTL_SECONDS)
    except Exception:
        # best-effort cache write; ignore errors
        pass


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
        r = await get_redis()
        if r is not None:
            try:
                await r.set("mw:snapshot", orjson.dumps(data_dict), ex=120)
                print("Market watch snapshot saved to Redis")

                pipe = r.pipeline()
                for it in mw.marketwatch:
                    # store numeric values as strings
                    pipe.set(f"mw:inst:{it.insCode}:pdv", str(it.pdv), ex=120)
                await pipe.execute()

            except Exception as redis_err:
                print(f"Warning: Redis caching failed: {redis_err}")
    except asyncio.TimeoutError:
        print("Market watch data fetch timed out after 30s - skipping snapshot")
    except Exception as e:
        print(f"snapshot save failed: {e}")
        import traceback

        traceback.print_exc()


async def _save_additional_data_if_valid():
    """Fetch additional data and save to Redis and DB if valid."""
    try:
        print("Fetching additional data...")
        # Add timeout to prevent hanging on slow API
        additional_data = await asyncio.wait_for(fetch_additional_data(), timeout=30.0)
        additional_list = additional_data.get('additional_data', [])
        print(f"Additional data fetched successfully, items: {len(additional_list)}")

        if additional_list:
            # Save to database
            try:
                await asyncio.to_thread(db.save_additional_data, additional_list)
                print("Additional data saved to database")
            except Exception as db_err:
                print(f"Database save failed: {db_err}")

            # Cache in Redis with 2m TTL (best-effort)
            r = await get_redis()
            if r is not None:
                try:
                    await r.set("mw:additional_data", orjson.dumps(additional_data), ex=120)
                    print("Additional data saved to Redis")
                except Exception as redis_err:
                    print(f"Warning: Redis caching failed: {redis_err}")
        else:
            print("No additional data to save")
    except asyncio.TimeoutError:
        print("Additional data fetch timed out after 30s - skipping")
    except Exception as e:
        print(f"Additional data save failed: {e}")
        import traceback
        traceback.print_exc()


async def _market_close_watcher():
    """Save once at each 12:30 Tehran close; also save once if starting while closed."""
    # On startup, if closed, save once (non-blocking)
    try:
        app.state._last_market_open = is_market_open()
        print(f"Market open on startup: {app.state._last_market_open}")
        if not app.state._last_market_open:
            print(
                "Market is closed on startup. Saving initial snapshot and additional data in background..."
            )
            # Run in background to not block startup
            asyncio.create_task(_save_snapshot_if_valid())
            asyncio.create_task(_save_additional_data_if_valid())
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
                print(f"Market close time reached. Saving snapshot and additional data...")
                await _save_snapshot_if_valid()
                await _save_additional_data_if_valid()
                app.state._last_snapshot_date = now_teh.date()
        except Exception as e:
            print(f"market watcher error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)
