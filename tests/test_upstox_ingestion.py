import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, OhlcBar, InstrumentMaster
from backend.ingestion.upstox_client import UpstoxHistoricalClient, UpstoxMarketDataClient
from backend.ingestion.ohlc_ingestor import OhlcIngestor
from backend.ingestion.schemas import OhlcBarIn

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_upstox_interval_mapping():
    # Pass a dummy token
    client = UpstoxHistoricalClient(access_token="mock_token")
    assert client._map_interval("1m") == ("minutes", 1)
    assert client._map_interval("5m") == ("minutes", 5)
    assert client._map_interval("1h") == ("hours", 1)
    assert client._map_interval("1d") == ("days", 1)
    
    with pytest.raises(ValueError):
        client._map_interval("10m")

@patch("httpx.Client.get")
def test_upstox_client_normalization(mock_get):
    # Mock Upstox V3 response
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "status": "success",
            "data": {
                "candles": [
                    ["2024-05-10T09:15:00+05:30", 22000.0, 22100.0, 21900.0, 22050.0, 1000, 0],
                    ["2024-05-10T09:16:00+05:30", 22050.0, 22060.0, 22040.0, 22055.0, 500, 0]
                ]
            }
        },
        raise_for_status=lambda: None
    )
    
    client = UpstoxHistoricalClient(access_token="mock_token")
    candles = client.get_historical_candles(
        instrument_key="NSE_INDEX|NIFTY 50",
        interval="1m",
        start=datetime(2024, 5, 10),
        end=datetime(2024, 5, 10)
    )
    
    assert len(candles) == 2
    assert candles[0]["open"] == 22000.0
    assert candles[0]["start_ts"].hour == 9
    assert candles[0]["start_ts"].minute == 15

@patch("backend.ingestion.upstox_client.UpstoxHistoricalClient.get_historical_candles")
def test_upstox_ingestion_with_resolution(mock_get_candles, db_session):
    # Seed instrument_master
    db_session.add(InstrumentMaster(
        broker="upstox", instrument_key="NSE_INDEX|NIFTY 50", segment="NSE_INDEX", exchange="NSE",
        instrument_type="INDEX", trading_symbol="NIFTY 50", name="NIFTY 50", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db_session.commit()
    
    # Mock historical response
    mock_get_candles.return_value = [
        {
            "start_ts": datetime(2024, 5, 10, 9, 15),
            "open": 22000.0, "high": 22100.0, "low": 21900.0, "close": 22050.0, "volume": 1000
        }
    ]
    
    upstox_client = UpstoxMarketDataClient(db_session=db_session, access_token="mock_token")
    
    # OhlcIngestor uses self.session_factory() as a context manager.
    # We need to wrap db_session in a way that calling it returns something that can be used with 'with'.
    class SessionContext:
        def __init__(self, session): self.session = session
        def __enter__(self): return self.session
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    
    ingestor = OhlcIngestor(client=upstox_client, session_factory=lambda: SessionContext(db_session))
    
    ingestor.ingest_historical(
        symbol="NIFTY",
        start=datetime(2024, 5, 10),
        end=datetime(2024, 5, 10),
        interval="5m"
    )
    
    # Assert OhlcBar is created
    bars = db_session.query(OhlcBar).filter_by(symbol="NIFTY").all()
    assert len(bars) == 1
    assert bars[0].open == 22000.0
    assert bars[0].exchange == "NSE"
    assert bars[0].symbol == "NIFTY"

def test_sync_prerequisite_failure(db_session):
    # No instruments seeded
    upstox_client = UpstoxMarketDataClient(db_session=db_session, access_token="mock_token")
    
    class SessionContext:
        def __init__(self, session): self.session = session
        def __enter__(self): return self.session
        def __exit__(self, exc_type, exc_val, exc_tb): pass

    ingestor = OhlcIngestor(client=upstox_client, session_factory=lambda: SessionContext(db_session))
    
    with pytest.raises(ValueError, match="Symbol NIFTY not found in instrument_master"):
        ingestor.ingest_historical(
            symbol="NIFTY",
            start=datetime(2024, 5, 10),
            end=datetime(2024, 5, 10),
            interval="5m"
        )

@patch("backend.ingestion.upstox_client.UpstoxHistoricalClient.get_historical_candles")
def test_upstox_ingestion_idempotency(mock_get_candles, db_session):
    # Seed instrument_master
    db_session.add(InstrumentMaster(
        broker="upstox", instrument_key="NSE_INDEX|NIFTY 50", segment="NSE_INDEX", exchange="NSE",
        instrument_type="INDEX", trading_symbol="NIFTY 50", name="NIFTY 50", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db_session.commit()
    
    mock_get_candles.return_value = [
        {
            "start_ts": datetime(2024, 5, 10, 9, 15),
            "open": 22000.0, "high": 22100.0, "low": 21900.0, "close": 22050.0, "volume": 1000
        }
    ]
    
    upstox_client = UpstoxMarketDataClient(db_session=db_session, access_token="mock_token")
    
    class SessionContext:
        def __init__(self, session): self.session = session
        def __enter__(self): return self.session
        def __exit__(self, exc_type, exc_val, exc_tb): pass

    ingestor = OhlcIngestor(client=upstox_client, session_factory=lambda: SessionContext(db_session))
    
    # Run 1
    ingestor.ingest_historical("NIFTY", datetime(2024, 5, 10), datetime(2024, 5, 10), "5m")
    assert db_session.query(OhlcBar).count() == 1
    
    # Run 2
    ingestor.ingest_historical("NIFTY", datetime(2024, 5, 10), datetime(2024, 5, 10), "5m")
    assert db_session.query(OhlcBar).count() == 1

@patch("httpx.Client.get")
def test_upstox_url_encoding(mock_get):
    # Mock success response
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"status": "success", "data": {"candles": []}},
        raise_for_status=lambda: None
    )
    
    client = UpstoxHistoricalClient(access_token="mock_token")
    client.get_historical_candles(
        instrument_key="NSE_INDEX|NIFTY 50",
        interval="1m",
        start=datetime(2024, 5, 10),
        end=datetime(2024, 5, 10)
    )
    
    # Verify the URL passed to httpx contains encoded key
    # Raw: NSE_INDEX|NIFTY 50
    # Encoded: NSE_INDEX%7CNIFTY%2050
    args, kwargs = mock_get.call_args
    url = args[0]
    assert "NSE_INDEX%7CNIFTY%2050" in url
    assert "NSE_INDEX|NIFTY 50" not in url
