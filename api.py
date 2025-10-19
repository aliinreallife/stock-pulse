from fastapi import FastAPI, HTTPException
import requests
from get_instrument_data import get_price_change
from get_market_watch_data import get_market_watch_data
from schemas import PriceResponse, MarketWatchResponse

app = FastAPI(title="Stock Pulse API", description="Get instrument price data")


@app.get("/price/{ins_code}", response_model=PriceResponse) # TODO: we should use web socket for this
async def get_price_endpoint(ins_code: str):
    """Get price change percentage (pDrCotVal) for a given instrument code."""
    try:
        ins_code_int = int(ins_code)
        pDrCotVal = get_price_change(ins_code_int)
        return PriceResponse(pDrCotVal=pDrCotVal)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail="Invalid instrument code format")
    except KeyError:
        raise HTTPException(status_code=503, detail="Invalid response from TSE API")
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Cannot connect to TSE API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/marketwatch", response_model=MarketWatchResponse)
async def get_market_watch():
    """Get full market watch data."""
    try:
        data = get_market_watch_data()
        return MarketWatchResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
