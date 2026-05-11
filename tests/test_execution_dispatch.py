import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, ExecutionDispatchRecord
from backend.orchestration.execution_dispatch import (
    register_dispatch_record,
    get_dispatch_record,
    has_been_dispatched,
    list_dispatch_records,
    execution_dispatch_to_dict
)

# Use in-memory SQLite for testing helpers
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_dispatch_helpers(db_session):
    # 1. Register a record
    record_dict = register_dispatch_record(
        db_session, 
        symbol="NIFTY", 
        interval="5m", 
        source_type="decision", 
        source_id=101, 
        dispatched_action="BUY", 
        status="executed",
        order_id=55
    )
    
    assert record_dict["symbol"] == "NIFTY"
    assert record_dict["source_id"] == 101
    assert record_dict["status"] == "executed"
    
    # 2. Check existence
    assert has_been_dispatched(db_session, "decision", 101) is True
    assert has_been_dispatched(db_session, "decision", 102) is False
    
    # 3. Lookup
    record = get_dispatch_record(db_session, "decision", 101)
    assert record is not None
    assert record.symbol == "NIFTY"
    
    # 4. Duplicate registration (should return existing)
    record_dict_2 = register_dispatch_record(
        db_session, 
        symbol="NIFTY", 
        interval="5m", 
        source_type="decision", 
        source_id=101, 
        dispatched_action="BUY", 
        status="executed"
    )
    assert record_dict_2["id"] == record_dict["id"]
    
    # 5. List records
    all_records = list_dispatch_records(db_session)
    assert len(all_records) == 1
    
    # 6. List with filter
    nifty_records = list_dispatch_records(db_session, symbol="NIFTY")
    assert len(nifty_records) == 1
    
    sensex_records = list_dispatch_records(db_session, symbol="SENSEX")
    assert len(sensex_records) == 0

def test_dispatch_to_dict(db_session):
    record = register_dispatch_record(
        db_session, "NIFTY", "5m", "override", 500, "SKIP", "skipped", reason="manual"
    )
    # register returns a dict already, but let's test the helper directly
    db_record = get_dispatch_record(db_session, "override", 500)
    d = execution_dispatch_to_dict(db_record)
    assert d["source_type"] == "override"
    assert d["source_id"] == 500
    assert d["dispatched_action"] == "SKIP"
    assert d["status"] == "skipped"
    assert d["reason"] == "manual"
    assert "created_ts" in d
