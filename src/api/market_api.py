from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from loguru import logger

from ..data.global_price_provider import get_provider
from ..database.db_manager import TradingDBManager
from ..user_management.auth_routes import AuthService


router = APIRouter(prefix="/api/market", tags=["Market Data"])
auth_service = AuthService()
db_manager = TradingDBManager()


class ImportRequest(BaseModel):
    provider: str = "yahoo"
    symbols: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@router.post("/import-daily")
async def import_daily_prices(req: ImportRequest, current_user = Depends(auth_service.get_current_user)):
    """Import daily OHLC prices for given symbols from a global provider and store in DB.

    Notes:
    - Stores into market_data table with timeframe '1d'.
    - Symbol naming must match your convention (e.g., 'AAPL', 'EURUSD=X').
    """
    try:
        provider = get_provider(req.provider)
        inserted = 0
        for symbol in req.symbols:
            df = provider.fetch_daily(symbol, start=req.start_date, end=req.end_date)
            if df.empty:
                logger.warning(f"No data for {symbol}")
                continue
            # Save to DB using existing schema
            candles = []
            for ts, row in df.iterrows():
                candles.append({
                    'timestamp': ts,
                    'open': float(row['open']) if row['open'] == row['open'] else None,  # NaN-safe
                    'high': float(row['high']) if row['high'] == row['high'] else None,
                    'low': float(row['low']) if row['low'] == row['low'] else None,
                    'close': float(row['close']) if row['close'] == row['close'] else None,
                    'volume': float(row['volume']) if row['volume'] == row['volume'] else 0.0,
                })
            if db_manager.save_market_data(symbol, '1d', candles):
                inserted += len(candles)
        return {"message": "Import completed", "inserted": inserted}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "INVALID_REQUEST", "message": str(e)})
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"code": "IMPORT_ERROR", "message": "Failed to import prices"})

