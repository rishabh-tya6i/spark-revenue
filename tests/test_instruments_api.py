import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from backend.main import app
from backend.db import Base, get_db, InstrumentMaster

# Use an in-memory SQLite database for testing with StaticPool to share connection
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def test_list_instruments(client):
    # Seed data
    db = TestingSessionLocal()
    db.add(InstrumentMaster(
        broker="upstox", instrument_key="K1", segment="NSE_INDEX", exchange="NSE", 
        instrument_type="INDEX", trading_symbol="NIFTY 50", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db.commit()
    db.close()
    
    response = client.get("/instruments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["instrument_key"] == "K1"

def test_resolve_symbol_api(client):
    # Seed data
    db = TestingSessionLocal()
    db.add(InstrumentMaster(
        broker="upstox", instrument_key="K1", segment="NSE_INDEX", exchange="NSE", 
        instrument_type="INDEX", trading_symbol="NIFTY 50", is_active=1,
        created_ts=datetime.now(), updated_ts=datetime.now()
    ))
    db.commit()
    db.close()
    
    response = client.get("/instruments/resolve?symbol=NIFTY")
    assert response.status_code == 200
    data = response.json()
    assert data["instrument_key"] == "K1"
    
    response = client.get("/instruments/resolve?symbol=INVALID")
    assert response.status_code == 404
