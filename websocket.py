from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import random
from datetime import datetime

app = FastAPI()

# Store active connections
active_connections: list[WebSocket] = []


# Simple HTML page to test WebSocket
@app.get("/")
async def get():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>WebSocket Test</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                #messages { 
                    border: 1px solid #ccc; 
                    padding: 10px; 
                    height: 300px; 
                    overflow-y: auto;
                    margin: 10px 0;
                }
                .price-update {
                    padding: 5px;
                    margin: 5px 0;
                    background: #f0f0f0;
                    border-radius: 3px;
                }
            </style>
        </head>
        <body>
            <h2>📈 Stock Price WebSocket Demo</h2>
            <div>
                <button onclick="connect()">Connect</button>
                <button onclick="disconnect()">Disconnect</button>
            </div>
            <div id="status">Status: Disconnected</div>
            <div id="messages"></div>
            
            <script>
                let ws = null;
                
                function connect() {
                    ws = new WebSocket("ws://localhost:8000/ws/stock/AAPL");
                    
                    ws.onopen = function(event) {
                        document.getElementById("status").innerHTML = "✅ Status: Connected";
                        addMessage("Connected to stock price feed!");
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        addMessage(`${data.symbol}: $${data.price} (${data.change > 0 ? '+' : ''}${data.change}%)`);
                    };
                    
                    ws.onclose = function(event) {
                        document.getElementById("status").innerHTML = "❌ Status: Disconnected";
                        addMessage("Connection closed");
                    };
                    
                    ws.onerror = function(error) {
                        addMessage("Error: " + error.message);
                    };
                }
                
                function disconnect() {
                    if (ws) {
                        ws.close();
                    }
                }
                
                function addMessage(message) {
                    const messagesDiv = document.getElementById("messages");
                    const messageElement = document.createElement("div");
                    messageElement.className = "price-update";
                    messageElement.innerHTML = `[${new Date().toLocaleTimeString()}] ${message}`;
                    messagesDiv.appendChild(messageElement);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# WebSocket endpoint for real-time stock prices
@app.websocket("/ws/stock/{symbol}")
async def websocket_stock_price(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint that sends real-time stock prices
    
    URL: ws://localhost:8000/ws/stock/AAPL
    """
    # Accept the connection
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial message
        await websocket.send_json({
            "message": f"Connected! Streaming prices for {symbol}",
            "symbol": symbol
        })
        
        # Simulate real-time price updates
        base_price = 150.0
        
        while True:
            # Simulate price change (random walk)
            change = random.uniform(-0.5, 0.5)
            base_price += change
            change_percent = round((change / base_price) * 100, 2)
            
            # Send price update to client
            price_data = {
                "symbol": symbol,
                "price": round(base_price, 2),
                "change": change_percent,
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_json(price_data)
            
            # Wait 1 second before next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        # Client disconnected
        active_connections.remove(websocket)
        print(f"Client disconnected from {symbol}")
    except Exception as e:
        print(f"Error: {e}")
        active_connections.remove(websocket)


# REST API endpoint for comparison
@app.get("/api/stock/{symbol}")
async def get_stock_price(symbol: str):
    """
    Regular REST API endpoint (for comparison)
    
    URL: http://localhost:8000/api/stock/AAPL
    """
    return {
        "symbol": symbol,
        "price": round(random.uniform(100, 200), 2),
        "timestamp": datetime.now().isoformat()
    }


# Endpoint to see active connections
@app.get("/connections")
async def get_connections():
    return {
        "active_connections": len(active_connections)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)