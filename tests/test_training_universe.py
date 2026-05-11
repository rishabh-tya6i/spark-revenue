import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, ANY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, InstrumentMaster
from backend.orchestration.universe import (
    parse_csv_setting, 
    normalize_repo_symbol, 
    select_explicit_symbols, 
    select_catalog_symbols,
    get_training_universe
)
from backend.orchestration.utils import get_train_symbols

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

def test_csv_parsing():
    assert parse_csv_setting(None) == []
    assert parse_csv_setting("") == []
    assert parse_csv_setting("NIFTY, SENSEX") == ["NIFTY", "SENSEX"]
    assert parse_csv_setting(" , NIFTY,,") == ["NIFTY"]

def test_symbol_normalization():
    assert normalize_repo_symbol("NIFTY 50") == "NIFTY"
    assert normalize_repo_symbol("NIFTY_50") == "NIFTY"
    assert normalize_repo_symbol("SENSEX") == "SENSEX"
    assert normalize_repo_symbol("RELIANCE") == "RELIANCE"
    assert normalize_repo_symbol(None) == ""

def test_explicit_mode():
    with patch("backend.orchestration.universe.settings") as mock_settings:
        mock_settings.TRAIN_SYMBOLS = "NIFTY, SENSEX, NIFTY"
        mock_settings.UPSTOX_DEFAULT_SYMBOLS = "SHOULD_NOT_USE"
        
        universe = select_explicit_symbols()
        assert universe == ["NIFTY", "SENSEX"] # Normalized and deduplicated

def test_explicit_fallback():
    with patch("backend.orchestration.universe.settings") as mock_settings:
        mock_settings.TRAIN_SYMBOLS = None
        mock_settings.UPSTOX_DEFAULT_SYMBOLS = "NIFTY 50, SENSEX"
        
        universe = select_explicit_symbols()
        assert universe == ["NIFTY", "SENSEX"]

def test_catalog_mode(db_session):
    # Seed instrument_master
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
    db_session.add(InstrumentMaster(
        broker="upstox", instrument_key="K3", segment="NSE_EQ", exchange="NSE", 
        instrument_type="EQ", trading_symbol="RELIANCE", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db_session.add(InstrumentMaster(
        broker="upstox", instrument_key="K4", segment="NSE_INDEX", exchange="NSE", 
        instrument_type="INDEX", trading_symbol="NIFTY BANK", is_active=0, # Inactive
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db_session.commit()
    
    with patch("backend.orchestration.universe.settings") as mock_settings:
        mock_settings.UPSTOX_UNIVERSE_SEGMENTS = "NSE_INDEX,BSE_INDEX"
        mock_settings.UPSTOX_UNIVERSE_INSTRUMENT_TYPES = "INDEX"
        mock_settings.TRAIN_MAX_SYMBOLS = 10
        
        universe = select_catalog_symbols(db_session)
        assert len(universe) == 2
        assert "NIFTY" in universe
        assert "SENSEX" in universe
        assert "RELIANCE" not in universe

def test_orchestration_utils_integration(db_session):
    # Test explicit mode works without session
    # We must patch the settings in universe.py because get_train_symbols calls get_training_universe
    with patch("backend.orchestration.universe.settings") as mock_settings:
        mock_settings.TRAIN_UNIVERSE_MODE = "explicit"
        mock_settings.TRAIN_SYMBOLS = "NIFTY"
        
        # We also need to patch utils.settings because get_train_symbols checks it
        with patch("backend.orchestration.utils.settings", mock_settings):
            symbols = get_train_symbols()
            assert symbols == ["NIFTY"]

def test_flow_integration():
    from backend.orchestration.flows import run_price_models_training_core
    
    with patch("backend.orchestration.flows.get_train_symbols") as mock_get_syms:
        mock_get_syms.return_value = ["SYM1", "SYM2"]
        
        # We mock the runner (which would normally be the Prefect task)
        mock_runner = MagicMock()
        
        # 1. Test dynamic selection (no symbols passed)
        run_price_models_training_core(runner=mock_runner)
        assert mock_runner.call_count == 2
        mock_runner.assert_any_call("SYM1", ANY, epochs=10)
        mock_runner.assert_any_call("SYM2", ANY, epochs=10)
        
        # 2. Test explicit override
        mock_runner.reset_mock()
        run_price_models_training_core(symbols=["OVERRIDE"], runner=mock_runner)
        assert mock_runner.call_count == 1
        mock_runner.assert_any_call("OVERRIDE", ANY, epochs=10)
