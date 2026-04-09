import pytest
from unittest.mock import MagicMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, NewsItem, NewsSentiment
from backend.sentiment.service import SentimentService

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_score_unscored_news(db_session):
    # Seed unscored news
    item1 = NewsItem(source="Src", title="Bullish on Bitcoin", url="url1", ingested_ts=datetime.utcnow())
    item2 = NewsItem(source="Src", title="Bearish on Stocks", url="url2", ingested_ts=datetime.utcnow())
    db_session.add(item1)
    db_session.add(item2)
    db_session.commit()
    
    # Mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = [(0.9, "positive"), (-0.7, "negative")]
    mock_model.model_name = "MockModel"
    
    service = SentimentService(session_factory=lambda: db_session, model=mock_model)
    count = service.score_unscored_news()
    
    assert count == 2
    sentiments = db_session.query(NewsSentiment).all()
    assert len(sentiments) == 2
    assert sentiments[0].sentiment_label == "positive"
    assert sentiments[1].sentiment_score == -0.7

def test_re_scoring_leaves_no_new_rows(db_session):
    # Seed one item and score it
    item = NewsItem(source="Src", title="Neutral", url="urlN", ingested_ts=datetime.utcnow())
    db_session.add(item)
    db_session.commit()
    
    mock_model = MagicMock()
    mock_model.predict.return_value = [(0.0, "neutral")]
    mock_model.model_name = "MockModel"
    
    service = SentimentService(session_factory=lambda: db_session, model=mock_model)
    service.score_unscored_news()
    
    # Run again
    count = service.score_unscored_news()
    assert count == 0
    assert db_session.query(NewsSentiment).count() == 1
