import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, OrchestrationRunRecord, TrainedModelRecord, DecisionRecord, ExecutionOrder, ExecutionPosition, ExecutionAccount
from backend.orchestration.state_snapshot import (
    get_latest_run_by_type,
    get_latest_active_models_summary,
    get_latest_decision_summary,
    get_latest_execution_summary,
    get_latest_dispatch_summary,
    build_operational_state_snapshot
)
from backend.db import ExecutionDispatchRecord

# Test DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    # Seed account for execution tests
    acc = ExecutionAccount(name="default", initial_balance=10000, cash_balance=10000, created_ts=datetime.utcnow(), updated_ts=datetime.utcnow())
    session.add(acc)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_get_latest_run_by_type(db):
    # Seed
    r1 = OrchestrationRunRecord(run_type="train", status="completed", created_ts=datetime.utcnow() - timedelta(minutes=10), summary_json="{}", success_count=0, failed_count=0, selected_symbols_count=0, ready_symbols_count=0, skipped_count=0)
    r2 = OrchestrationRunRecord(run_type="train", status="completed", created_ts=datetime.utcnow(), summary_json="{}", success_count=0, failed_count=0, selected_symbols_count=0, ready_symbols_count=0, skipped_count=0)
    db.add_all([r1, r2])
    db.commit()
    
    latest = get_latest_run_by_type(db, "train")
    assert latest["id"] == r2.id

def test_get_latest_active_models_summary(db):
    # Seed
    m1 = TrainedModelRecord(symbol="NIFTY", interval="5m", model_type="price_model", artifact_path="pt", status="success", is_active=1, created_ts=datetime.utcnow())
    m2 = TrainedModelRecord(symbol="NIFTY", interval="5m", model_type="rl_agent", artifact_path="zip", status="success", is_active=1, created_ts=datetime.utcnow())
    db.add_all([m1, m2])
    db.commit()
    
    summary = get_latest_active_models_summary(db, ["NIFTY", "SENSEX"], "5m")
    assert "NIFTY" in summary["price_model_available"]
    assert "NIFTY" in summary["rl_agent_available"]
    assert "SENSEX" in summary["missing_price_model"]
    assert "SENSEX" in summary["missing_rl_agent"]

def test_get_latest_decision_summary(db):
    # Seed
    # Case 1: rl_action is BUY (Actionable)
    d1 = DecisionRecord(symbol="NIFTY", interval="5m", decision_label="STRONG_BULLISH", decision_score=0.9, rl_action="BUY", timestamp=datetime.utcnow())
    # Case 2: rl_action is HOLD (Hold)
    d2 = DecisionRecord(symbol="SENSEX", interval="5m", decision_label="STRONG_BULLISH", decision_score=0.8, rl_action="HOLD", timestamp=datetime.utcnow())
    # Case 3: Actionable decision_label but rl_action is unexpected (Hold)
    d3 = DecisionRecord(symbol="BANKNIFTY", interval="5m", decision_label="BUY", decision_score=0.7, rl_action="UNEXPECTED", timestamp=datetime.utcnow())
    
    db.add_all([d1, d2, d3])
    db.commit()
    
    summary = get_latest_decision_summary(db, ["NIFTY", "SENSEX", "BANKNIFTY", "MIDCAP"], "5m")
    
    # NIFTY should be actionable because rl_action == "BUY"
    assert "NIFTY" in summary["actionable"]
    # SENSEX should be hold because rl_action == "HOLD", even though decision_label was STRONG_BULLISH
    assert "SENSEX" in summary["hold"]
    # BANKNIFTY should be hold because rl_action was unexpected
    assert "BANKNIFTY" in summary["hold"]
    # MIDCAP should be missing because it wasn't seeded
    assert "MIDCAP" in summary["missing"]
    # All seeded symbols should be in has_decision
    assert set(summary["has_decision"]) == {"NIFTY", "SENSEX", "BANKNIFTY"}

def test_get_latest_execution_summary(db):
    # Seed
    acc = db.query(ExecutionAccount).first()
    o1 = ExecutionOrder(account_id=acc.id, symbol="NIFTY", side="BUY", quantity=1, price=100, created_ts=datetime.utcnow())
    p1 = ExecutionPosition(account_id=acc.id, symbol="NIFTY", quantity=1, avg_price=100, updated_ts=datetime.utcnow())
    db.add_all([o1, p1])
    db.commit()
    
    summary = get_latest_execution_summary(db, ["NIFTY", "SENSEX"])
    assert "NIFTY" in summary["has_orders"]
    assert "NIFTY" in summary["open_positions"]
    assert "SENSEX" in summary["no_activity"]

def test_build_operational_state_snapshot(db):
    from unittest.mock import patch
    with patch("backend.orchestration.state_snapshot.get_training_universe") as mock_uni, \
         patch("backend.orchestration.state_snapshot.get_inference_ready_symbols") as mock_inf, \
         patch("backend.orchestration.state_snapshot.get_execution_ready_symbols") as mock_exec:
        
        mock_uni.return_value = ["NIFTY"]
        mock_inf.return_value = (["NIFTY"], [])
        mock_exec.return_value = (["NIFTY"], [])
        
        snapshot = build_operational_state_snapshot(db, mode="explicit", interval="5m")
        assert snapshot["mode"] == "explicit"
        assert snapshot["symbols"] == ["NIFTY"]
        assert "models" in snapshot
        assert "decisions" in snapshot
        assert "execution_state" in snapshot
        assert "latest_runs" in snapshot
        assert "execution_dispatch" in snapshot

def test_get_latest_dispatch_summary(db):
    # Seed
    # NIFTY: Decision seeded, not dispatched
    d1 = DecisionRecord(symbol="NIFTY", interval="5m", decision_label="BUY", decision_score=0.9, rl_action="BUY", timestamp=datetime.utcnow())
    db.add(d1)
    db.commit()

    # SENSEX: Decision seeded, ALREADY dispatched
    d2 = DecisionRecord(symbol="SENSEX", interval="5m", decision_label="BUY", decision_score=0.9, rl_action="BUY", timestamp=datetime.utcnow())
    db.add(d2)
    db.commit()
    
    disp = ExecutionDispatchRecord(
        symbol="SENSEX", interval="5m", source_type="decision", source_id=d2.id,
        dispatched_action="BUY", status="executed", created_ts=datetime.utcnow()
    )
    db.add(disp)
    db.commit()

    summary = get_latest_dispatch_summary(db, ["NIFTY", "SENSEX", "MIDCAP"], "5m")
    assert "SENSEX" in summary["already_dispatched"]
    assert "NIFTY" in summary["not_dispatched"]
    assert "MIDCAP" in summary["not_dispatched"]
