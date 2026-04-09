from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict

class BacktestRequest(BaseModel):
    strategy_name: str = "rule_based"   # or "rl_policy"
    symbol: str
    interval: str = "5m"
    start_ts: datetime
    end_ts: datetime
    initial_capital: Optional[float] = None

class BacktestRunOut(BaseModel):
    id: int
    strategy_name: str
    symbol: str
    interval: str
    start_ts: datetime
    end_ts: datetime
    initial_capital: float
    final_capital: Optional[float]
    status: str
    created_ts: datetime
    completed_ts: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class BacktestMetricsOut(BaseModel):
    backtest_id: int
    metrics: Dict[str, float]
