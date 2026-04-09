from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class PriceFeatureIn(BaseModel):
    symbol: str
    ts: datetime
    interval: str
    rsi_14: Optional[float] = None
    vwap: Optional[float] = None
    ema_short: Optional[float] = None
    ema_long: Optional[float] = None

class PriceFeatureOut(PriceFeatureIn):
    model_config = ConfigDict(from_attributes=True)
