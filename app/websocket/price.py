from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from get_instrument_data import get_price
from utils import is_market_open
from database import MarketWatchDB
from config import get_redis
from config import DEBUG, WEBSOCKET_UPDATE_INTERVAL, REDIS_TTL_SECONDS
import asyncio

router = APIRouter()
db = MarketWatchDB()


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


@router.get("/ws-test", response_class=HTMLResponse)
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


@router.websocket("/ws/price")
async def price_websocket(websocket: WebSocket, ins_code: str):
    await manager.connect(websocket)
    try:
        ins_code_int = int(ins_code)
        while True:
            if is_market_open():
                value = None
                from_redis = False
                try:
                    r = await get_redis()
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
                    try:
                        r = await get_redis()
                        if DEBUG:
                            print(f"price to redis: {ins_code}")
                        await r.set(f"mw:inst:{ins_code}:price", str(value), ex=REDIS_TTL_SECONDS)
                    except Exception:
                        pass
            else:
                value = None
                from_redis = False
                try:
                    r = await get_redis()
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
                    try:
                        if value is not None:
                            r = await get_redis()
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


