import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, OhlcBar
from backend.ingestion.ohlc_ingestor import OhlcIngestor
from backend.ingestion.schemas import BaseMarketDataClient, OhlcBarIn

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

class FakeClient(BaseMarketDataClient):
    def fetch_historical_ohlc(self, symbol, start, end, interval):
        return [
            OhlcBarIn(
                symbol=symbol,
                exchange="TEST",
                start_ts=start,
                end_ts=start + timedelta(minutes=5),
                open=100.0,
                high=110.0,
                low=90.0,
                close=105.0,
                volume=1000.0
            )
        ]

def test_ingest_historical_success(db_session):
    client = FakeClient()
    # Simple lambda to return the session
    session_factory = lambda: db_session
    
    ingestor = OhlcIngestor(client=client, session_factory=session_factory)
    
    symbol = "TEST_SYM"
    start = datetime.utcnow()
    ingestor.ingest_historical(symbol, start, start + timedelta(hours=1), "5m")
    
    bars = db_session.query(OhlcBar).filter(OhlcBar.symbol == symbol).all()
    assert len(bars) == 1
    assert bars[0].open == 100.0

def test_ingest_historical_idempotency(db_session):
    client = FakeClient()
    session_factory = lambda: db_session
    
    ingestor = OhlcIngestor(client=client, session_factory=session_factory)
    
    symbol = "TEST_SYM"
    start = datetime(2024, 1, 1, 10, 0)
    
    # First ingestion
    ingestor.ingest_historical(symbol, start, start + timedelta(minutes=5), "5m")
    assert db_session.query(OhlcBar).count() == 1
    
    # Second ingestion with same data (should not create new row)
    ingestor.ingest_historical(symbol, start, start + timedelta(minutes=5), "5m")
    assert db_session.query(OhlcBar).count() == 1
