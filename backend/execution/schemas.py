from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

class AccountOut(BaseModel):
    id: int
    name: str
    base_currency: str
    initial_balance: float
    cash_balance: float
    model_config = ConfigDict(from_attributes=True)

class PositionOut(BaseModel):
    symbol: str
    quantity: float
    avg_price: float
    market_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)

class OrderOut(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    price: float
    created_ts: datetime
    model_config = ConfigDict(from_attributes=True)

class AccountSnapshotOut(BaseModel):
    account: AccountOut
    positions: List[PositionOut]
    equity: float
    unrealized_pnl_total: float
    realized_pnl_total: float
