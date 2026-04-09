import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime
from backend.db import Base, engine, NewsItem, NewsSentiment, SessionLocal

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    from backend.sentiment.app import app
    return TestClient(app)

def test_get_latest_sentiment(client):
    now = datetime.utcnow()
    # Insert real data into sqlite
    with SessionLocal() as session:
        item = NewsItem(source="Src", title="Real News", url="http://real.com", ingested_ts=now)
        session.add(item)
        session.commit()
        
        sentiment = NewsSentiment(
            news_id=item.id, sentiment_score=0.5, sentiment_label="positive", 
            model_name="M1", created_ts=now
        )
        session.add(sentiment)
        session.commit()

    response = client.get("/sentiment/latest?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sentiment_label"] == "positive"
    assert data[0]["news_id"] is not None

def test_trigger_scoring_endpoint(client):
    # This just mocks the service method to avoid full integration test complexity here
    with patch('backend.sentiment.service.SentimentService.score_unscored_news', return_value=5):
        response = client.post("/sentiment/score")
        assert response.status_code == 200
        assert response.json() == {"scored": 5}
