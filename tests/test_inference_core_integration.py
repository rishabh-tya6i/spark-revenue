import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from backend.db import Base, NewsSentiment, OptionSignal
from backend.orchestration.inference_runner import run_inference_universe_core
from backend.decision_engine.service import DecisionEngineService

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

def test_run_inference_universe_core_signature():
    """
    Verifies that run_inference_universe_core correctly uses get_training_universe 
    with a session object and the expected signature.
    """
    with patch("backend.orchestration.inference_runner.SessionLocal") as mock_session_cls, \
         patch("backend.orchestration.inference_runner.get_training_universe") as mock_get_uni, \
         patch("backend.orchestration.inference_runner.get_inference_ready_symbols") as mock_get_ready, \
         patch("backend.orchestration.inference_runner.run_price_inference_for_symbols") as mock_price, \
         patch("backend.orchestration.inference_runner.run_rl_inference_for_symbols") as mock_rl, \
         patch("backend.orchestration.inference_runner.compute_decisions_for_symbols") as mock_dec, \
         patch("backend.orchestration.inference_runner.summarize_inference_results") as mock_sum, \
         patch("backend.orchestration.run_history.register_orchestration_run") as mock_reg:
        
        mock_reg.return_value = {"id": 1}
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_get_uni.return_value = ["NIFTY"]
        mock_get_ready.return_value = (["NIFTY"], [{"ready": True}])
        mock_sum.return_value = {}

        results = run_inference_universe_core(mode="explicit", interval="5m")
        
        # Verify get_training_universe was called with session and mode
        # It's called inside the first context block in the real function now
        mock_get_uni.assert_called_once_with(mock_session, mode="explicit")
        
        assert results["symbols"] == ["NIFTY"]
        assert results["inference_ready_symbols"] == ["NIFTY"]
        assert "readiness" in results

def test_decision_engine_collect_inputs_field_consistency(db_session):
    """
    Verifies that DecisionEngineService.collect_inputs queries NewsSentiment 
    using the correct 'created_ts' field.
    """
    # Seed data
    db_session.add(NewsSentiment(
        news_id=1,
        sentiment_score=0.8,
        sentiment_label="POSITIVE",
        model_name="test-model",
        created_ts=datetime.utcnow()
    ))
    db_session.add(OptionSignal(
        symbol="NIFTY",
        expiry=datetime.utcnow(),
        timestamp=datetime.utcnow(),
        signal_label="BULLISH",
        pcr=0.9,
        max_pain_strike=19000
    ))
    db_session.commit()

    service = DecisionEngineService(session_factory=lambda: db_session)
    
    # This call should not raise AttributeError: 'NewsSentiment' object has no attribute 'timestamp'
    # nor should it fail if the query is correct.
    inputs = service.collect_inputs("NIFTY", "5m")
    
    assert len(inputs["sentiment"]) == 1
    assert inputs["sentiment"][0].sentiment_label == "POSITIVE"
    assert inputs["options"].symbol == "NIFTY"
