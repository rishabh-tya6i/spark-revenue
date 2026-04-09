from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Literal, Optional

class OptionSnapshotIn(BaseModel):
    symbol: str
    expiry: datetime
    strike: float
    option_type: Literal["CE", "PE"]
    open_interest: float
    change_in_oi: Optional[float] = None
    volume: Optional[float] = None
    last_traded_price: Optional[float] = None
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class OptionSignalOut(BaseModel):
    id: int
    symbol: str
    expiry: datetime
    timestamp: datetime
    pcr: Optional[float] = None
    max_pain_strike: Optional[float] = None
    call_oi_total: Optional[float] = None
    put_oi_total: Optional[float] = None
    signal_label: Optional[str] = None
    signal_strength: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)
