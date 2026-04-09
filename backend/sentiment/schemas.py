from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class NewsItemIn(BaseModel):
    source: str
    title: str
    summary: Optional[str] = None
    url: str
    published_ts: Optional[datetime] = None

class NewsItemOut(NewsItemIn):
    id: int
    ingested_ts: datetime
    model_config = ConfigDict(from_attributes=True)

class NewsSentimentOut(BaseModel):
    news_id: int
    sentiment_score: float
    sentiment_label: str
    model_name: str
    created_ts: datetime
    model_config = ConfigDict(from_attributes=True)
