from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.db import get_db
from backend.instruments.service import InstrumentService
from backend.instruments.schemas import InstrumentRecordOut, InstrumentResolveResult

router = APIRouter(prefix="/instruments", tags=["instruments"])

@router.post("/sync")
def sync_instruments(
    segments: Optional[str] = Query(None, description="Comma-separated segments to sync"),
    db: Session = Depends(get_db)
):
    service = InstrumentService(db)
    seg_list = segments.split(",") if segments else None
    count = service.sync_upstox_instruments(segments=seg_list)
    return {"processed_count": count}

@router.get("/", response_model=List[InstrumentRecordOut])
def list_instruments(
    segment: Optional[str] = None,
    instrument_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = InstrumentService(db)
    return service.list_instruments(segment=segment, instrument_type=instrument_type, limit=limit)

@router.get("/resolve", response_model=InstrumentResolveResult)
def resolve_symbol(
    symbol: str = Query(..., description="Symbol to resolve, e.g. NIFTY"),
    db: Session = Depends(get_db)
):
    service = InstrumentService(db)
    result = service.resolve_symbol(symbol)
    if not result:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return result
