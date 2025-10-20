import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager, suppress
import requests
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List

from get_instrument_data import get_price_change
from get_market_watch_data import get_market_watch_data
from schemas import MarketWatchResponse, PriceResponse, MarketStatusResponse
from utils import is_market_open
from config import TEHRAN_TZ, MARKET_CLOSE_TIME
from database import MarketWatchDB
from config import API_HOST, API_PORT, WEBSOCKET_UPDATE_INTERVAL


@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize shared state
    app.state._last_market_open = None
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
        data_dict = await asyncio.to_thread(get_market_watch_data)
        mw = MarketWatchResponse(**data_dict)
        # market_closed_at is informational here
        db.save_market_watch_data(mw)
    except Exception as e:
        # Swallow to keep task alive; logs could be added here
        print(f"snapshot save failed: {e}")


async def _market_close_watcher():
    """Save once at each 12:30 Tehran close; also save once if starting while closed."""
    # On startup, if closed, save once
    try:
        app.state._last_market_open = is_market_open()
        if not app.state._last_market_open:
            await _save_snapshot_if_valid()
    except Exception as e:
        print(f"initial market state check failed: {e}")

    while True:
        try:
            now_teh = datetime.now(TEHRAN_TZ)
            target_close = now_teh.replace(hour=MARKET_CLOSE_TIME.hour,
                                           minute=MARKET_CLOSE_TIME.minute,
                                           second=0, microsecond=0)
            if now_teh >= target_close:
                target_close += timedelta(days=1)

            sleep_seconds = (target_close - now_teh).total_seconds()
            if sleep_seconds > 0:
                await asyncio.sleep(sleep_seconds)

            # At/after scheduled close → save once per day
            now_teh = datetime.now(TEHRAN_TZ)
            if app.state._last_snapshot_date != now_teh.date():
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
            print('marketwatch live')
            return MarketWatchResponse(**data)
        # Closed → from DB
        else:
            print('marketwatch db')
            return db.get_market_watch_from_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/market-status", response_model=MarketStatusResponse)
async def get_market_status():
    """Return current market open/closed status."""
    try:
        return MarketStatusResponse(is_market_open=is_market_open())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


class PriceConnectionManager:  # this part was new for me i started some digging
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


# websocket donst accept response model and dont aprear on swagger ui
@app.websocket(
    "/ws/price"
)  # TODO we are only sending the number not object a liitle bit more efficient in data usage and speed but its so little
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
                value = get_price_change(ins_code_int)
                print('price from live')
            else:
                value = db.get_pdv_by_ins_code(ins_code)
                print('price from db')
                if value is None:
                    # fallback minimal
                    value = 0.0
            await websocket.send_text(str(value))
            await asyncio.sleep(WEBSOCKET_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        manager.disconnect(websocket)


@app.get(
    "/ws-price-test", response_class=HTMLResponse, include_in_schema=False
)  # just to see what is happening in the websocket for myself # TODO: remove this later
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

    uvicorn.run(app, host="0.0.0.0", port=8000)
