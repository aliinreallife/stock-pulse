from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from get_instrument_data import get_price
from utils import is_market_open
from database import MarketWatchDB
from config import get_redis
from config import WEBSOCKET_UPDATE_INTERVAL
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
            else:
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
                    value = 0.0

            await websocket.send_text(str(value))
            await asyncio.sleep(WEBSOCKET_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


