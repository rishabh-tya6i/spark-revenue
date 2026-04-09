from pydantic import BaseModel, ConfigDict
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Optional

class OhlcBarIn(BaseModel):
    symbol: str
    exchange: str
    start_ts: datetime
    end_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class Tick(BaseModel):
    symbol: str
    ts: datetime
    price: float
    volume: float
    
    model_config = ConfigDict(from_attributes=True)

class BaseMarketDataClient(ABC):
    @abstractmethod
    def fetch_historical_ohlc(
        self, 
        symbol: str, 
        start: datetime, 
        end: datetime, 
        interval: str
    ) -> List[OhlcBarIn]:
        """
        Fetch historical OHLC data from the exchange.
        interval: e.g., '1m', '5m', 'day'
        """
        pass
