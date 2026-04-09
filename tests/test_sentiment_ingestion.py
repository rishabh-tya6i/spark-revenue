import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, NewsItem
from backend.sentiment.ingestion import NewsIngestor

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

def test_ingest_from_feeds(db_session):
    mock_feed_data = MagicMock()
    mock_feed_data.feed = {'title': 'Mock News Source'}
    mock_feed_data.entries = [
        {
            'title': 'Test Article 1',
            'summary': 'Summary 1',
            'link': 'http://example.com/1',
            'published_parsed': None
        },
        {
            'title': 'Test Article 2',
            'summary': 'Summary 2',
            'link': 'http://example.com/2',
            'published_parsed': None
        }
    ]
    
    with patch('feedparser.parse', return_value=mock_feed_data):
        ingestor = NewsIngestor(session_factory=lambda: db_session, rss_feeds=["http://mock-feed.com"])
        count = ingestor.ingest_from_feeds()
        
        assert count == 2
        items = db_session.query(NewsItem).all()
        assert len(items) == 2
        assert items[0].url == 'http://example.com/1'

def test_ingest_idempotency(db_session):
    mock_feed_data = MagicMock()
    mock_feed_data.feed = {'title': 'Mock News Source'}
    mock_feed_data.entries = [
        {'title': 'Duo Article', 'url': 'http://example.com/duo', 'link': 'http://example.com/duo'}
    ]
    
    with patch('feedparser.parse', return_value=mock_feed_data):
        ingestor = NewsIngestor(session_factory=lambda: db_session, rss_feeds=["http://mock-feed.com"])
        ingestor.ingest_from_feeds()
        count = ingestor.ingest_from_feeds() # Run again
        
        assert count == 0 # No new items
        assert db_session.query(NewsItem).count() == 1
