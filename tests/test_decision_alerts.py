import pytest
from datetime import datetime
from backend.db import Base, engine, SessionLocal, AlertRecord
from backend.decision_engine.service import DecisionEngineService
from backend.decision_engine.schemas import FusedDecisionOut

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(AlertRecord).delete()
        session.commit()
    yield

def test_generate_alert_high_confidence():
    service = DecisionEngineService()
    
    # decision_score 0.8 >= settings.DECISION_MIN_CONFIDENCE (0.6)
    decision = FusedDecisionOut(
        symbol="BTCUSDT", interval="5m", timestamp=datetime.utcnow(),
        decision_label="STRONG_BULLISH", decision_score=0.8
    )
    
    alert = service.generate_alert_from_decision(decision)
    assert alert is not None
    assert alert.importance == 0.8
    assert "BTCUSDT" in alert.message
    
    with SessionLocal() as session:
        record = session.query(AlertRecord).first()
        assert record is not None
        assert record.alert_type == "HIGH_CONFIDENCE_STRONG_BULLISH"

def test_no_alert_low_confidence():
    service = DecisionEngineService()
    
    # decision_score 0.4 < 0.6
    decision = FusedDecisionOut(
        symbol="BTCUSDT", interval="5m", timestamp=datetime.utcnow(),
        decision_label="BEARISH", decision_score=0.4
    )
    
    alert = service.generate_alert_from_decision(decision)
    assert alert is None
    
    with SessionLocal() as session:
        count = session.query(AlertRecord).count()
        assert count == 0
