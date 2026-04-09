import pytest
from datetime import datetime, timedelta
import fakeredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, OhlcBar, PriceFeature
from backend.feature_store.service import FeatureStore
from backend.feature_store.schemas import PriceFeatureOut

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

@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)

def test_compute_and_store_price_features(db_session):
    # Seed OHLC data
    symbol = "BTCUSDT"
    base_ts = datetime(2024, 1, 1, 10, 0)
    for i in range(20):
        bar = OhlcBar(
            symbol=symbol, exchange="BINANCE",
            start_ts=base_ts + timedelta(minutes=5*i),
            end_ts=base_ts + timedelta(minutes=5*(i+1)),
            open=50000+i, high=50500+i, low=49500+i, close=50100+i, volume=1.0
        )
        db_session.add(bar)
    db_session.commit()
    
    # Run feature store
    store = FeatureStore(session_factory=lambda: db_session)
    count = store.compute_and_store_price_features(symbol, base_ts, base_ts + timedelta(hours=2), "5m")
    
    assert count == 20
    # Check if rows exists in DB
    features = db_session.query(PriceFeature).filter(PriceFeature.symbol == symbol).all()
    assert len(features) == 20
    assert features[-1].rsi_14 is not None

def test_feature_idempotency(db_session):
    symbol = "BTCUSDT"
    base_ts = datetime(2024, 1, 1, 10, 0)
    bar = OhlcBar(
        symbol=symbol, exchange="BINANCE",
        start_ts=base_ts, end_ts=base_ts + timedelta(minutes=5),
        open=100, high=110, low=90, close=105, volume=100
    )
    db_session.add(bar)
    db_session.commit()
    
    store = FeatureStore(session_factory=lambda: db_session)
    
    # Run twice
    store.compute_and_store_price_features(symbol, base_ts, base_ts + timedelta(minutes=5), "5m")
    store.compute_and_store_price_features(symbol, base_ts, base_ts + timedelta(minutes=5), "5m")
    
    # Should only have 1 row
    assert db_session.query(PriceFeature).count() == 1

def test_get_latest_price_features_caching(db_session, redis_client):
    symbol = "ETHUSDT"
    interval = "1h"
    ts = datetime(2024, 1, 2, 12, 0)
    
    # Seed DB
    feat = PriceFeature(
        symbol=symbol, ts=ts, interval=interval,
        rsi_14=45.5, vwap=2500.0, ema_short=2480.0, ema_long=2450.0
    )
    db_session.add(feat)
    db_session.commit()
    
    store = FeatureStore(session_factory=lambda: db_session, redis_client=redis_client)
    
    # 1. First call (Cache Miss)
    out1 = store.get_latest_price_features(symbol, interval)
    assert out1.rsi_14 == 45.5
    
    # Check if in Redis
    redis_key = f"feature:price:{symbol}:{interval}"
    assert redis_client.exists(redis_key)
    
    # 2. Second call (Cache Hit)
    # Manually change DB to see if it still returns old cached value
    db_session.query(PriceFeature).filter(PriceFeature.symbol == symbol).update({"rsi_14": 99.9})
    db_session.commit()
    
    out2 = store.get_latest_price_features(symbol, interval)
    assert out2.rsi_14 == 45.5 # Still old value from cache
