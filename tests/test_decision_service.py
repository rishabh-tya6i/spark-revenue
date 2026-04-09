import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from backend.db import Base, engine, SessionLocal, DecisionRecord
from backend.decision_engine.service import DecisionEngineService
from backend.decision_engine.schemas import FusedDecisionOut

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(DecisionRecord).delete()
        session.commit()
    yield

def test_compute_and_store_decision():
    service = DecisionEngineService()
    
    # Mock collect_inputs to avoid DB dependencies in v1
    mock_inputs = {
        "price": {"label": "UP", "probabilities": {"UP": 0.8}},
        "rl": {"action": "BUY", "confidence": 0.9},
        "sentiment": [],
        "options": None
    }
    
    with patch.object(service, 'collect_inputs', return_value=mock_inputs):
        decision = service.compute_and_store_decision("BTCUSDT", "5m")
        
        assert isinstance(decision, FusedDecisionOut)
        assert decision.symbol == "BTCUSDT"
        assert decision.decision_label in ["BULLISH", "STRONG_BULLISH"]
        
        # Verify persistence
        with SessionLocal() as session:
            record = session.query(DecisionRecord).first()
            assert record is not None
            assert record.symbol == "BTCUSDT"
            assert record.decision_label == decision.decision_label

def test_get_latest_decision():
    service = DecisionEngineService()
    
    # Manual seed
    with SessionLocal() as session:
        session.add(DecisionRecord(
            symbol="ETHUSDT", interval="1h", timestamp=datetime.utcnow(),
            decision_label="NEUTRAL", decision_score=0.5
        ))
        session.commit()
        
    latest = service.get_latest_decision("ETHUSDT", "1h")
    assert latest is not None
    assert latest.symbol == "ETHUSDT"
    assert latest.decision_label == "NEUTRAL"
