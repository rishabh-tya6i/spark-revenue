from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class InstrumentRecordIn(BaseModel):
    broker: str = "upstox"
    instrument_key: str
    segment: str
    exchange: str
    instrument_type: str
    trading_symbol: Optional[str] = None
    name: Optional[str] = None
    short_name: Optional[str] = None
    underlying_symbol: Optional[str] = None
    underlying_key: Optional[str] = None
    expiry: Optional[datetime] = None
    strike_price: Optional[float] = None
    tick_size: Optional[float] = None
    lot_size: Optional[float] = None
    raw_json: Optional[str] = None
    is_active: int = 1

class InstrumentRecordOut(BaseModel):
    id: int
    broker: str
    instrument_key: str
    segment: str
    exchange: str
    instrument_type: str
    trading_symbol: Optional[str] = None
    name: Optional[str] = None
    short_name: Optional[str] = None
    underlying_symbol: Optional[str] = None
    underlying_key: Optional[str] = None
    expiry: Optional[datetime] = None
    strike_price: Optional[float] = None
    tick_size: Optional[float] = None
    lot_size: Optional[float] = None
    is_active: int

    model_config = ConfigDict(from_attributes=True)

class InstrumentResolveResult(BaseModel):
    symbol: str
    instrument_key: str
    segment: str
    exchange: str
    instrument_type: str
    trading_symbol: Optional[str] = None
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
