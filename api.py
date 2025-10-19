import asyncio
import requests
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List

from get_instrument_data import get_price_change
from get_market_watch_data import get_market_watch_data
from schemas import MarketWatchResponse, PriceResponse

app = FastAPI(title="Stock Pulse API", description="Get instrument price data")


@app.get("/marketwatch", response_model=MarketWatchResponse)
async def get_market_watch():
    """Get full market watch data."""
    try:
        # Run in thread pool to prevent blocking WebSocket
        data = await asyncio.to_thread(get_market_watch_data)

        return MarketWatchResponse(**data)
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
            # print(f"clients online: {len(manager.active_connections)}")
            price_change = get_price_change(ins_code_int)
            await websocket.send_text(str(price_change))
            await asyncio.sleep(0.5)
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
