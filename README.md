# Stock Pulse

Real-time stock market data from TSETMC, because their API documentation doesn't exist.

## Features

-  **Real-time market data** from TSETMC API
-  **Redis caching** for fast responses (optional)
-  **SQLite persistence** for when the market is closed
-  **WebSocket support** for live price updates
-  **Docker ready** easy as it gets :D
-  **Market status aware** (open/closed hours)

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd stock-pulse
   cp env.example .env
   ```

2. **Start services:**
   ```bash
   # With Redis (default)
   docker-compose up
   ```

3. **Access API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - WebSocket Test: http://localhost:8000/ws-test

### Using Python

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Run application:**
   ```bash
   python api.py
   ```

## API Endpoints

- `GET /marketwatch` - Get market watch data
- `GET /marketwatch-with-additional-data` - Market data + client type info
- `GET /market-status` - Check if market is open
- `WS /ws/price?ins_code={code}` - WebSocket for live prices

