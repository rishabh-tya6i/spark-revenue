import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, ExecutionOverrideRecord
from backend.orchestration.execution_overrides import (
    set_execution_override,
    clear_execution_override,
    get_active_execution_override,
    list_active_execution_overrides,
    execution_override_to_dict
)

# Test DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_set_execution_override(db):
    # 1. Set override
    res = set_execution_override(db, "NIFTY", "5m", "SKIP", "Event risk")
    assert res["symbol"] == "NIFTY"
    assert res["override_action"] == "SKIP"
    assert res["is_active"] is True
    assert res["reason"] == "Event risk"

    # 2. Set another one (replaces old)
    res2 = set_execution_override(db, "NIFTY", "5m", "BUY", "Force buy")
    assert res2["override_action"] == "BUY"
    
    # Verify old one is inactive
    old = db.query(ExecutionOverrideRecord).filter(ExecutionOverrideRecord.id == res["id"]).first()
    assert old.is_active == 0
    assert old.cleared_ts is not None

def test_clear_execution_override(db):
    set_execution_override(db, "NIFTY", "5m", "SKIP")
    
    # Clear
    cleared = clear_execution_override(db, "NIFTY", "5m")
    assert cleared["symbol"] == "NIFTY"
    assert cleared["is_active"] is False
    assert cleared["cleared_ts"] is not None
    
    # Try clearing again
    res = clear_execution_override(db, "NIFTY", "5m")
    assert res is None

def test_list_active_execution_overrides(db):
    set_execution_override(db, "NIFTY", "5m", "SKIP")
    set_execution_override(db, "SENSEX", "5m", "BUY")
    set_execution_override(db, "BANKNIFTY", "15m", "SELL")
    
    # List all
    all_active = list_active_execution_overrides(db)
    assert len(all_active) == 3
    
    # List by interval
    only_5m = list_active_execution_overrides(db, interval="5m")
    assert len(only_5m) == 2
    
def test_invalid_action(db):
    with pytest.raises(ValueError, match="Invalid override action"):
        set_execution_override(db, "NIFTY", "5m", "INVALID")
