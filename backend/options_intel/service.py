import logging
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException

from ..db import OptionSnapshot, OptionSignal, SessionLocal
from ..config import settings
from .schemas import OptionSnapshotIn, OptionSignalOut
from .computations import compute_pcr, compute_max_pain_strike, derive_option_signal
from .ingestion import OptionsIngestor

logger = logging.getLogger(__name__)

class OptionsIntelService:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def compute_and_store_signals(self, symbol: str, expiry: datetime, timestamp: Optional[datetime] = None) -> Optional[OptionSignalOut]:
        """
        Loads snapshots, computes derivatives metrics, and stores/returns a signal.
        """
        with self.session_factory() as session:
            # 1. Fetch relevant snapshots
            query = session.query(OptionSnapshot).filter(
                OptionSnapshot.symbol == symbol,
                OptionSnapshot.expiry == expiry
            )
            
            if timestamp:
                query = query.filter(OptionSnapshot.timestamp == timestamp)
            else:
                # Get latest timestamp available
                latest_ts = session.query(OptionSnapshot.timestamp).filter(
                    OptionSnapshot.symbol == symbol,
                    OptionSnapshot.expiry == expiry
                ).order_by(OptionSnapshot.timestamp.desc()).first()
                if not latest_ts:
                    return None
                timestamp = latest_ts[0]
                query = query.filter(OptionSnapshot.timestamp == timestamp)

            rows = query.all()
            if not rows:
                return None
            
            snapshots_in = [OptionSnapshotIn.model_validate(r) for r in rows]
            
            # 2. Computations
            pcr, call_oi, put_oi = compute_pcr(snapshots_in)
            max_pain = compute_max_pain_strike(snapshots_in)
            label, strength = derive_option_signal(pcr, call_oi, put_oi)
            
            # 3. Store Signal
            signal = OptionSignal(
                symbol=symbol,
                expiry=expiry,
                timestamp=timestamp,
                pcr=pcr,
                max_pain_strike=max_pain,
                call_oi_total=call_oi,
                put_oi_total=put_oi,
                signal_label=label,
                signal_strength=strength
            )
            session.add(signal)
            session.commit()
            
            return OptionSignalOut.model_validate(signal)

    def get_latest_signal(self, symbol: str, expiry: Optional[datetime] = None) -> Optional[OptionSignalOut]:
        with self.session_factory() as session:
            query = session.query(OptionSignal).filter(OptionSignal.symbol == symbol)
            if expiry:
                query = query.filter(OptionSignal.expiry == expiry)
            
            result = query.order_by(OptionSignal.timestamp.desc()).first()
            if not result:
                return None
            return OptionSignalOut.model_validate(result)

# FastAPI Router
router = APIRouter()

class OptionsSnapshotRequest(BaseModel):
    symbol: str
    expiry: datetime

@router.post("/options/refresh-snapshot", response_model=OptionSignalOut)
async def refresh_options_snapshot(request: OptionsSnapshotRequest):
    ingestor = OptionsIngestor()
    service = OptionsIntelService()
    
    # 1. Fetch new data
    timestamp = datetime.utcnow()
    count = ingestor.ingest_snapshot(request.symbol, request.expiry, timestamp=timestamp)
    if count == 0:
        raise HTTPException(status_code=400, detail="Failed to fetch options data")
        
    # 2. Compute signals
    signal = service.compute_and_store_signals(request.symbol, request.expiry, timestamp=timestamp)
    if not signal:
        raise HTTPException(status_code=500, detail="Failed to compute options signal")
        
    return signal

@router.get("/options/signal", response_model=OptionSignalOut)
async def get_latest_options_signal(symbol: str, expiry: Optional[datetime] = None):
    service = OptionsIntelService()
    signal = service.get_latest_signal(symbol, expiry)
    if not signal:
        raise HTTPException(status_code=404, detail="No options signal found for symbol")
    return signal
