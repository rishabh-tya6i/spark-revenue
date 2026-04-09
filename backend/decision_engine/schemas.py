from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class FusedDecisionOut(BaseModel):
    id: Optional[int] = None
    symbol: str
    interval: str
    timestamp: datetime

    decision_label: str
    decision_score: float

    price_direction: Optional[str] = None
    price_confidence: Optional[float] = None

    rl_action: Optional[str] = None
    rl_confidence: Optional[float] = None

    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None

    options_signal_label: Optional[str] = None
    options_pcr: Optional[float] = None
    options_max_pain_strike: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class DecisionRequest(BaseModel):
    symbol: str
    interval: str = "5m"

class DecisionResponse(BaseModel):
    decision: FusedDecisionOut
    alert: Optional[dict] = None # Simplified alert for JSON response
