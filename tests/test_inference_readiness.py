import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from backend.db import Base, TrainedModelRecord, OhlcBar, PriceFeature
from backend.orchestration.inference_readiness import check_symbol_inference_readiness, get_inference_ready_symbols

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_inference_readiness_logic(db_session):
    symbol = "NIFTY"
    interval = "5m"
    
    # 1. No models, no features
    res = check_symbol_inference_readiness(db_session, symbol, interval)
    assert res["ready"] is False
    assert "missing_price_model" in res["reason"]
    assert "missing_rl_model" in res["reason"]
    assert "missing_features" in res["reason"]
    
    # 2. Add price model only
    pm = TrainedModelRecord(
        symbol=symbol, interval=interval, model_type="price_model",
        artifact_path="p.pt", status="success", is_active=1,
        created_ts=datetime.utcnow()
    )
    db_session.add(pm)
    db_session.commit()
    
    res = check_symbol_inference_readiness(db_session, symbol, interval)
    assert res["price_model_ready"] is True
    assert res["ready"] is False
    assert "missing_rl_model" in res["reason"]
    
    # 3. Add RL model
    rl = TrainedModelRecord(
        symbol=symbol, interval=interval, model_type="rl_agent",
        artifact_path="r.zip", status="success", is_active=1,
        created_ts=datetime.utcnow()
    )
    db_session.add(rl)
    db_session.commit()
    
    res = check_symbol_inference_readiness(db_session, symbol, interval)
    assert res["rl_model_ready"] is True
    assert res["ready"] is False
    assert res["reason"] == "missing_features"
    
    # 4. Add features (but not enough)
    # settings.PRICE_MODEL_INPUT_WINDOW is usually 60.
    for i in range(10):
        ts = datetime(2026, 1, 1, 10, i)
        ohlc = OhlcBar(symbol=symbol, interval=interval, exchange="NSE", start_ts=ts, end_ts=ts, open=100, high=101, low=99, close=100.5, volume=1000)
        feat = PriceFeature(symbol=symbol, interval=interval, ts=ts, rsi_14=50, vwap=100.2, ema_short=100.3, ema_long=100.4)
        db_session.add(ohlc)
        db_session.add(feat)
    db_session.commit()
    
    res = check_symbol_inference_readiness(db_session, symbol, interval)
    assert res["feature_ready"] is False
    assert res["ready"] is False
    
    # 5. Add enough features (total > 60)
    for i in range(10, 70):
        hour = 10 + (i // 60)
        minute = i % 60
        ts = datetime(2026, 1, 1, hour, minute)
        ohlc = OhlcBar(symbol=symbol, interval=interval, exchange="NSE", start_ts=ts, end_ts=ts, open=100, high=101, low=99, close=100.5, volume=1000)
        feat = PriceFeature(symbol=symbol, interval=interval, ts=ts, rsi_14=50, vwap=100.2, ema_short=100.3, ema_long=100.4)
        db_session.add(ohlc)
        db_session.add(feat)
    db_session.commit()
    
    res = check_symbol_inference_readiness(db_session, symbol, interval)
    assert res["feature_ready"] is True
    assert res["ready"] is True
    assert res["reason"] is None

def test_get_inference_ready_symbols(db_session):
    # Setup one ready (NIFTY) and one not (SENSEX)
    # NIFTY
    for mtype in ["price_model", "rl_agent"]:
        db_session.add(TrainedModelRecord(
            symbol="NIFTY", interval="5m", model_type=mtype,
            artifact_path="x", status="success", is_active=1,
            created_ts=datetime.utcnow()
        ))
    for i in range(70):
        hour = 10 + (i // 60)
        minute = i % 60
        ts = datetime(2026, 1, 1, hour, minute)
        db_session.add(OhlcBar(symbol="NIFTY", interval="5m", exchange="NSE", start_ts=ts, end_ts=ts, close=100, open=100, high=100, low=100, volume=0))
        db_session.add(PriceFeature(symbol="NIFTY", interval="5m", ts=ts, vwap=100))
    
    # SENSEX (missing models)
    db_session.commit()
    
    ready_list, details = get_inference_ready_symbols(db_session, ["NIFTY", "SENSEX"], "5m")
    assert ready_list == ["NIFTY"]
    assert len(details) == 2
    assert details[0]["symbol"] == "NIFTY"
    assert details[0]["ready"] is True
    assert details[1]["symbol"] == "SENSEX"
    assert details[1]["ready"] is False
