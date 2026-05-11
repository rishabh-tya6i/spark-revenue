import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, InstrumentMaster
from backend.instruments.service import InstrumentService
from backend.instruments.schemas import InstrumentRecordIn

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

def test_parse_upstox_instruments():
    raw_items = [
        {
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "segment": "NSE_INDEX",
            "exchange": "NSE",
            "instrument_type": "INDEX",
            "trading_symbol": "NIFTY 50",
            "name": "NIFTY 50",
            "expiry": "2024-05-30",
            "strike": 0.0,
            "tick_size": 0.05,
            "lot_size": 50
        }
    ]
    
    service = InstrumentService(MagicMock())
    parsed = service.parse_upstox_instruments(raw_items)
    
    assert len(parsed) == 1
    assert parsed[0].instrument_key == "NSE_INDEX|NIFTY 50"
    assert parsed[0].segment == "NSE_INDEX"
    assert parsed[0].trading_symbol == "NIFTY 50"
    assert parsed[0].expiry.year == 2024
    assert parsed[0].expiry.month == 5

@patch("backend.instruments.service.UpstoxInstrumentsClient.fetch_instruments")
def test_sync_upstox_instruments(mock_fetch, db_session):
    mock_fetch.return_value = [
        {
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "segment": "NSE_INDEX",
            "exchange": "NSE",
            "instrument_type": "INDEX",
            "trading_symbol": "NIFTY 50",
            "name": "NIFTY 50",
            "strike": 0,
            "tick_size": 0.05,
            "lot_size": 50
        },
        {
            "instrument_key": "BSE_INDEX|SENSEX",
            "segment": "BSE_INDEX",
            "exchange": "BSE",
            "instrument_type": "INDEX",
            "trading_symbol": "SENSEX",
            "name": "SENSEX",
            "strike": 0,
            "tick_size": 0.01,
            "lot_size": 10
        },
        {
            "instrument_key": "NSE_EQ|RELIANCE",
            "segment": "NSE_EQ",
            "exchange": "NSE",
            "instrument_type": "EQ",
            "trading_symbol": "RELIANCE",
            "name": "RELIANCE INDUSTRIES LTD",
            "strike": 0,
            "tick_size": 0.05,
            "lot_size": 1
        }
    ]
    
    service = InstrumentService(db_session)
    # Sync only index segments
    count = service.sync_upstox_instruments(segments=["NSE_INDEX", "BSE_INDEX"])
    
    assert count == 2
    assert db_session.query(InstrumentMaster).count() == 2
    
    # Verify resolving
    res_nifty = service.resolve_symbol("NIFTY")
    assert res_nifty is not None
    assert res_nifty.instrument_key == "NSE_INDEX|NIFTY 50"
    
    res_sensex = service.resolve_symbol("SENSEX")
    assert res_sensex is not None
    assert res_sensex.instrument_key == "BSE_INDEX|SENSEX"

def test_default_universe(db_session):
    # Seed data
    db_session.add(InstrumentMaster(
        broker="upstox", instrument_key="K1", segment="NSE_INDEX", exchange="NSE", 
        instrument_type="INDEX", trading_symbol="NIFTY 50", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db_session.add(InstrumentMaster(
        broker="upstox", instrument_key="K2", segment="BSE_INDEX", exchange="BSE", 
        instrument_type="INDEX", trading_symbol="SENSEX", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db_session.commit()
    
    with patch("backend.instruments.service.settings.UPSTOX_DEFAULT_SYMBOLS", "NIFTY,SENSEX"):
        service = InstrumentService(db_session)
        universe = service.get_default_training_universe()
        assert len(universe) == 2
        assert {u.instrument_key for u in universe} == {"K1", "K2"}

@patch("backend.instruments.service.UpstoxInstrumentsClient.fetch_instruments")
def test_sync_idempotency(mock_fetch, db_session):
    service = InstrumentService(db_session)
    
    # 1. Initial sync
    mock_fetch.return_value = [{
        "instrument_key": "NSE_INDEX|NIFTY 50",
        "segment": "NSE_INDEX", "exchange": "NSE", "instrument_type": "INDEX",
        "trading_symbol": "NIFTY 50", "name": "NIFTY 50", "strike": 0, "tick_size": 0.05, "lot_size": 50
    }]
    service.sync_upstox_instruments(segments=["NSE_INDEX"])
    assert db_session.query(InstrumentMaster).count() == 1
    inst1 = db_session.query(InstrumentMaster).first()
    assert inst1.name == "NIFTY 50"
    
    # 2. Re-sync with changed value
    mock_fetch.return_value = [{
        "instrument_key": "NSE_INDEX|NIFTY 50",
        "segment": "NSE_INDEX", "exchange": "NSE", "instrument_type": "INDEX",
        "trading_symbol": "NIFTY 50", "name": "NIFTY 50 UPDATED", "strike": 0, "tick_size": 0.05, "lot_size": 50
    }]
    service.sync_upstox_instruments(segments=["NSE_INDEX"])
    
    # Should still have only 1 row
    assert db_session.query(InstrumentMaster).count() == 1
    inst2 = db_session.query(InstrumentMaster).first()
    assert inst2.name == "NIFTY 50 UPDATED"

def test_generic_symbol_resolution(db_session):
    service = InstrumentService(db_session)
    db_session.add(InstrumentMaster(
        broker="upstox", instrument_key="NSE_EQ|RELIANCE", segment="NSE_EQ", exchange="NSE", 
        instrument_type="EQ", trading_symbol="RELIANCE", name="RELIANCE INDUSTRIES LTD", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db_session.commit()
    
    # Case insensitive exact match on trading_symbol
    res = service.resolve_symbol("reliance")
    assert res is not None
    assert res.instrument_key == "NSE_EQ|RELIANCE"
    
    # Match on name substring
    res = service.resolve_symbol("INDUSTRIES")
    assert res is not None
    assert res.instrument_key == "NSE_EQ|RELIANCE"
