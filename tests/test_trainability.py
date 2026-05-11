import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, OhlcBar, PriceFeature
from backend.orchestration.trainability import (
    get_min_required_ohlc_bars,
    get_min_required_feature_rows,
    check_symbol_trainability,
    get_trainable_symbols
)

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

def test_threshold_helpers():
    with patch("backend.orchestration.trainability.settings") as mock_settings:
        mock_settings.PRICE_MODEL_INPUT_WINDOW = 60
        mock_settings.PRICE_MODEL_PREDICTION_HORIZON = 12
        mock_settings.TRAINABILITY_MIN_BUFFER_BARS = 5
        
        assert get_min_required_ohlc_bars() == 77
        assert get_min_required_feature_rows() == 77

def test_check_symbol_trainability(db_session):
    threshold = 50 # Default min
    with patch("backend.orchestration.trainability.get_min_required_ohlc_bars", return_value=threshold):
        # 1. Trainable
        for i in range(threshold):
            db_session.add(OhlcBar(symbol="T1", interval="5m", exchange="NSE", start_ts=datetime.now(), end_ts=datetime.now(), open=1, high=1, low=1, close=1, volume=1))
            # Unique constraint on PriceFeature (symbol, ts, interval)
            db_session.add(PriceFeature(symbol="T1", ts=datetime.fromtimestamp(1000000 + i), interval="5m"))
        db_session.commit()
        
        res = check_symbol_trainability(db_session, "T1", "5m")
        assert res["trainable"] is True
        assert res["ohlc_count"] == threshold
        assert res["feature_count"] == threshold
        
        # 2. Missing everything
        res = check_symbol_trainability(db_session, "MISSING", "5m")
        assert res["trainable"] is False
        assert res["reason"] == "missing_ohlc_and_features"
        
        # 3. Insufficient OHLC (and missing features)
        db_session.add(OhlcBar(symbol="FEW", interval="5m", exchange="NSE", start_ts=datetime.now(), end_ts=datetime.now(), open=1, high=1, low=1, close=1, volume=1))
        db_session.commit()
        res = check_symbol_trainability(db_session, "FEW", "5m")
        assert res["trainable"] is False
        assert res["reason"] == "missing_ohlc_and_features"
        
        # 4. Insufficient features
        for i in range(threshold):
            db_session.add(OhlcBar(symbol="FEW_FEAT", interval="5m", exchange="NSE", start_ts=datetime.now(), end_ts=datetime.now(), open=1, high=1, low=1, close=1, volume=1))
        db_session.add(PriceFeature(symbol="FEW_FEAT", ts=datetime.now(), interval="5m"))
        db_session.commit()
        res = check_symbol_trainability(db_session, "FEW_FEAT", "5m")
        assert res["trainable"] is False
        assert res["reason"] == "insufficient_features"

def test_get_trainable_symbols(db_session):
    threshold = 10
    with patch("backend.orchestration.trainability.get_min_required_ohlc_bars", return_value=threshold):
        # SYM1 trainable
        for i in range(threshold):
            db_session.add(OhlcBar(symbol="SYM1", interval="5m", exchange="NSE", start_ts=datetime.now(), end_ts=datetime.now(), open=1, high=1, low=1, close=1, volume=1))
            db_session.add(PriceFeature(symbol="SYM1", ts=datetime.fromtimestamp(2000000 + i), interval="5m"))
        db_session.commit()
        
        trainable, details = get_trainable_symbols(db_session, ["SYM1", "SYM2"], "5m")
        assert trainable == ["SYM1"]
        assert len(details) == 2
        assert details[0]["symbol"] == "SYM1"
        assert details[0]["trainable"] is True
        assert details[1]["symbol"] == "SYM2"
        assert details[1]["trainable"] is False
