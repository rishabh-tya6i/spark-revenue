import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, TrainedModelRecord
from backend.orchestration.model_registry import (
    register_trained_model,
    get_latest_active_model,
    list_models,
    model_record_to_dict
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

def test_registration_activation_logic(db_session):
    """
    Verify that registering a new successful model deactivates the old one.
    Verify that failed runs are not activated.
    """
    # 1. Register first model
    r1 = register_trained_model(db_session, "NIFTY", "5m", "price_model", "path1", "success")
    assert r1.is_active == 1
    
    # 2. Register second model for same tuple
    r2 = register_trained_model(db_session, "NIFTY", "5m", "price_model", "path2", "success")
    assert r2.is_active == 1
    
    # Refresh r1 to check is_active
    db_session.refresh(r1)
    assert r1.is_active == 0
    
    # 3. Register failed model
    r3 = register_trained_model(db_session, "NIFTY", "5m", "price_model", "path3", "failed")
    assert r3.is_active == 0
    
    # Check latest lookup
    latest = get_latest_active_model(db_session, "NIFTY", "5m", "price_model")
    assert latest.id == r2.id
    assert latest.artifact_path == "path2"

def test_list_models_filtering(db_session):
    """
    Verify that list_models respects symbol, interval, and active filters.
    """
    register_trained_model(db_session, "NIFTY", "5m", "price_model", "p1", "success")
    register_trained_model(db_session, "SENSEX", "5m", "rl_agent", "p2", "success")
    register_trained_model(db_session, "NIFTY", "1h", "price_model", "p3", "failed")
    
    # All
    assert len(list_models(db_session)) == 3
    
    # Symbol
    assert len(list_models(db_session, symbol="NIFTY")) == 2
    
    # Active only
    assert len(list_models(db_session, active_only=True)) == 2
    
    # Type
    assert len(list_models(db_session, model_type="rl_agent")) == 1

def test_model_record_to_dict(db_session):
    """
    Verify JSON conversion helper.
    """
    r = register_trained_model(db_session, "NIFTY", "5m", "price_model", "path", "success", notes="some notes")
    data = model_record_to_dict(r)
    
    assert data["symbol"] == "NIFTY"
    assert data["is_active"] is True
    assert data["notes"] == "some notes"
    assert "created_ts" in data
