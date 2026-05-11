import pytest
from unittest.mock import patch, MagicMock
from backend.orchestration.training_report import (
    run_price_training_for_symbols,
    run_rl_training_for_symbols,
    summarize_training_results,
    split_training_status,
    persist_training_results
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.db import Base, TrainedModelRecord

@pytest.fixture
def db_session():
    # Use an in-memory SQLite database for testing
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_persist_training_results_db(db_session):
    """
    Verify that training results are correctly persisted to the DB and result dicts are enriched.
    """
    results = [
        {
            "symbol": "NIFTY",
            "interval": "5m",
            "trainer": "price_model",
            "status": "success",
            "artifact_path": "models/price_model/NIFTY_5m.pt",
            "error": None,
        },
        {
            "symbol": "SENSEX",
            "interval": "5m",
            "trainer": "rl_agent",
            "status": "failed",
            "artifact_path": None,
            "error": "training crashed",
        }
    ]
    
    enriched = persist_training_results(db_session, results)
    
    assert len(enriched) == 2
    
    # NIFTY Success
    assert enriched[0]["symbol"] == "NIFTY"
    assert enriched[0]["registry_record_id"] is not None
    assert enriched[0]["active"] is True
    
    # SENSEX Failure
    assert enriched[1]["symbol"] == "SENSEX"
    assert enriched[1]["registry_record_id"] is not None
    assert enriched[1]["active"] is False
    
    # Verify DB rows
    records = db_session.query(TrainedModelRecord).all()
    assert len(records) == 2
    
    # Check mapping
    nifty_rec = db_session.query(TrainedModelRecord).filter_by(symbol="NIFTY").first()
    assert nifty_rec.model_type == "price_model"
    assert nifty_rec.status == "success"
    assert nifty_rec.is_active == 1
    
    sensex_rec = db_session.query(TrainedModelRecord).filter_by(symbol="SENSEX").first()
    assert sensex_rec.model_type == "rl_agent"
    assert sensex_rec.status == "failed"
    assert sensex_rec.is_active == 0

@patch("backend.orchestration.training_report.train_price_model")
def test_run_price_training_success_fail(mock_train):
    """
    Verify that price training helper correctly captures successes, soft failures, and exceptions.
    """
    def side_effect(symbol, interval, **kwargs):
        if symbol == "NIFTY":
            return f"models/price_model/{symbol}_{interval}.pt"
        if symbol == "SENSEX":
            return None # Training returned no path
        if symbol == "CRASH":
            raise Exception("engine overheat")
            
    mock_train.side_effect = side_effect
    
    results = run_price_training_for_symbols(["NIFTY", "SENSEX", "CRASH"], "5m")
    
    assert len(results) == 3
    
    # Success
    assert results[0]["symbol"] == "NIFTY"
    assert results[0]["status"] == "success"
    assert "nifty_5m.pt" in results[0]["artifact_path"].lower()
    assert results[0]["error"] is None
    
    # Soft Failure (no path)
    assert results[1]["symbol"] == "SENSEX"
    assert results[1]["status"] == "failed"
    assert results[1]["artifact_path"] is None
    assert "no artifact path" in results[1]["error"].lower()
    
    # Exception
    assert results[2]["symbol"] == "CRASH"
    assert results[2]["status"] == "failed"
    assert "engine overheat" in results[2]["error"]

@patch("backend.orchestration.training_report.train_rl_agent")
def test_run_rl_training_success_fail(mock_train):
    """
    Verify that RL training helper correctly captures results.
    """
    mock_train.return_value = "models/rl/agent.zip"
    
    results = run_rl_training_for_symbols(["NIFTY"], "5m")
    
    assert len(results) == 1
    assert results[0]["status"] == "success"
    assert results[0]["artifact_path"] == "models/rl/agent.zip"

def test_summarize_training_results():
    """
    Verify that the summary counts are calculated correctly from mixed results.
    """
    price_results = [
        {"status": "success"},
        {"status": "failed"}
    ]
    rl_results = [
        {"status": "success"},
        {"status": "success"}
    ]
    
    summary = summarize_training_results(price_results, rl_results)
    
    assert summary["price_model"]["total"] == 2
    assert summary["price_model"]["success"] == 1
    assert summary["price_model"]["failed"] == 1
    
    assert summary["rl_agent"]["total"] == 2
    assert summary["rl_agent"]["success"] == 2
    assert summary["rl_agent"]["failed"] == 0

def test_split_training_status():
    """
    Verify helper to split succeeded and failed symbols.
    """
    results = [
        {"symbol": "S1", "status": "success"},
        {"symbol": "S2", "status": "failed"},
        {"symbol": "S3", "status": "success"}
    ]
    success, failed = split_training_status(results)
    assert success == ["S1", "S3"]
    assert failed == ["S2"]
