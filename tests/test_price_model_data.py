import pytest
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, OhlcBar, PriceFeature
from backend.price_model.data import build_price_model_dataset

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

def test_build_price_model_dataset_shape(db_session):
    symbol = "TEST"
    interval = "5m"
    input_window = 10
    horizon = 2
    
    # Seed data
    base_ts = datetime(2024, 1, 1, 10, 0)
    for i in range(30):
        ts = base_ts + timedelta(minutes=5*i)
        bar = OhlcBar(
            symbol=symbol, exchange="TEST", 
            start_ts=ts, end_ts=ts + timedelta(minutes=5),
            open=100.0+i, high=105.0+i, low=95.0+i, close=100.0+i, volume=100.0
        )
        feat = PriceFeature(
            symbol=symbol, ts=ts + timedelta(minutes=5),
            interval=interval, rsi_14=50.0, vwap=100.0+i, 
            ema_short=100.0+i, ema_long=100.0+i
        )
        db_session.add(bar)
        db_session.add(feat)
    db_session.commit()
    
    X, y = build_price_model_dataset(db_session, symbol, interval, input_window, horizon)
    
    # Total bars: 30
    # After dropna shift(1) log_ret: 29 bars
    # num_samples = 29 - 10 - 2 + 1 = 18
    assert X.shape == (18, 10, 5) # 5 features
    assert y.shape == (18,)
    assert np.all(np.isin(y, [0, 1, 2]))
