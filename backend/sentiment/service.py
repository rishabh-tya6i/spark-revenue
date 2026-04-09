import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException

from ..db import NewsItem, NewsSentiment, SessionLocal
from ..config import settings
from .model import SentimentModel
from .schemas import NewsSentimentOut

logger = logging.getLogger(__name__)

class SentimentService:
    def __init__(self, session_factory=SessionLocal, model: Optional[SentimentModel] = None):
        self.session_factory = session_factory
        self.model = model or SentimentModel(model_name=settings.SENTIMENT_MODEL_NAME)

    def score_unscored_news(self, batch_size: Optional[int] = None) -> int:
        """
        Queries news_items with no sentiment record and computes scores.
        """
        limit = batch_size or settings.SENTIMENT_BATCH_SIZE
        
        with self.session_factory() as session:
            # Query items that don't have a sentiment entry
            # select news_items where id not in (select news_id from news_sentiment)
            subq = select(NewsSentiment.news_id)
            query = session.query(NewsItem).filter(~NewsItem.id.in_(subq)).limit(limit)
            
            items = query.all()
            if not items:
                return 0
            
            logger.info(f"Scoring {len(items)} news items")
            
            # Prepare texts (title + summary if available)
            texts = [f"{item.title} {item.summary or ''}" for item in items]
            
            # Predict
            predictions = self.model.predict(texts)
            
            # Store results
            now = datetime.utcnow()
            scored_count = 0
            for item, (score, label) in zip(items, predictions):
                sentiment = NewsSentiment(
                    news_id=item.id,
                    sentiment_score=score,
                    sentiment_label=label,
                    model_name=self.model.model_name,
                    created_ts=now
                )
                session.add(sentiment)
                scored_count += 1
            
            session.commit()
            return scored_count

    def get_latest_sentiment(self, limit: int = 20) -> List[NewsSentimentOut]:
        """
        Retrieves recent sentiment results.
        """
        with self.session_factory() as session:
            results = session.query(NewsSentiment).order_by(NewsSentiment.created_ts.desc()).limit(limit).all()
            return [NewsSentimentOut.model_validate(r) for r in results]

# FastAPI Router
router = APIRouter()

@router.get("/sentiment/latest", response_model=List[NewsSentimentOut])
async def get_latest_sentiment(limit: int = 20):
    service = SentimentService()
    return service.get_latest_sentiment(limit)

@router.post("/sentiment/score")
async def trigger_sentiment_scoring(batch_size: Optional[int] = None):
    service = SentimentService()
    count = service.score_unscored_news(batch_size=batch_size)
    return {"scored": count}

@router.get("/news/recent")
async def get_recent_news(limit: int = 20):
    with SessionLocal() as session:
        items = session.query(NewsItem).order_by(NewsItem.ingested_ts.desc()).limit(limit).all()
        return items
