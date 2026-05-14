from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Literal, Optional

from ..db import get_db, SessionLocal
from ..config import settings
from ..settings.token_store import get_upstox_token
from ..ingestion.ohlc_ingestor import OhlcIngestor
from ..ingestion.upstox_client import UpstoxMarketDataClient
from ..ingestion.binance_client import BinanceClient

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _parse_ymd(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date '{value}'. Expected YYYY-MM-DD")


@router.post("/backfill")
def backfill_ohlc(
    source: Literal["upstox", "binance"] = Query(..., description="Data source"),
    symbol: str = Query(..., description="Symbol to backfill, e.g. NIFTY"),
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    interval: str = Query("5m", description="Interval, e.g. 1m, 5m, 1h, 1d"),
    db: Session = Depends(get_db),
):
    """
    UI-facing backfill endpoint.
    - Upstox requires instruments to be synced and UPSTOX_ACCESS_TOKEN configured.
    - Binance uses public market data.
    """
    start_dt = _parse_ymd(start)
    end_dt = _parse_ymd(end)

    if source == "upstox":
        if not get_upstox_token():
            raise HTTPException(status_code=400, detail="UPSTOX_ACCESS_TOKEN missing in server environment")
        client = UpstoxMarketDataClient(db_session=db)
    else:
        client = BinanceClient(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
        )

    try:
        ingestor = OhlcIngestor(client=client, session_factory=SessionLocal)
        ingestor.ingest_historical(symbol=symbol, start=start_dt, end=end_dt, interval=interval)
        return {"status": "ok", "source": source, "symbol": symbol, "interval": interval, "start": start, "end": end}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
