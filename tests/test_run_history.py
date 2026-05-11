import pytest
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, OrchestrationRunRecord
from backend.orchestration.run_history import (
    build_run_record_summary,
    register_orchestration_run,
    list_orchestration_runs,
    get_orchestration_run,
    orchestration_run_to_dict
)

# Test DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_build_run_record_summary_train():
    result = {
        "status": "completed",
        "trainable_symbols": ["NIFTY"],
        "training_summary": {
            "price_model": {"total": 1, "success": 1, "failed": 0},
            "rl_agent": {"total": 1, "success": 0, "failed": 1}
        }
    }
    summary = build_run_record_summary("train", result)
    assert summary["trainable_symbols"] == ["NIFTY"]
    assert summary["price_model"]["success"] == 1
    assert summary["rl_agent"]["failed"] == 1

def test_build_run_record_summary_inference():
    result = {
        "status": "completed",
        "symbols": ["A", "B"],
        "inference_ready_symbols": ["A"],
        "summary": {
            "decision": {"total": 1, "success": 1, "failed": 0}
        }
    }
    summary = build_run_record_summary("inference", result)
    assert summary["symbols"] == ["A", "B"]
    assert summary["inference_ready_symbols"] == ["A"]
    assert summary["decision"]["success"] == 1

def test_register_and_fetch_run(db):
    result = {
        "status": "completed",
        "symbols": ["NIFTY"],
        "execution_ready_symbols": ["NIFTY"],
        "summary": {"total": 1, "success": 1, "skipped": 0, "failed": 0}
    }
    
    # Register
    record_dict = register_orchestration_run(db, "execution", "catalog_filter", "5m", result)
    assert record_dict["id"] is not None
    assert record_dict["run_type"] == "execution"
    assert record_dict["success_count"] == 1
    assert record_dict["summary"]["symbols"] == ["NIFTY"]
    
    # List
    runs = list_orchestration_runs(db, run_type="execution")
    assert len(runs) == 1
    assert runs[0].id == record_dict["id"]
    
    # Get
    fetched = get_orchestration_run(db, record_dict["id"])
    assert fetched.run_type == "execution"

def test_register_cycle_run(db):
    result = {
        "status": "completed",
        "summary": {
            "selected_symbols": 10,
            "inference_ready_symbols": 8,
            "decision_success": 8,
            "execution_ready_symbols": 2,
            "execution_success": 2,
            "execution_skipped": 0,
            "execution_failed": 0
        }
    }
    record_dict = register_orchestration_run(db, "cycle", "explicit", "5m", result)
    assert record_dict["selected_symbols_count"] == 10
    assert record_dict["ready_symbols_count"] == 8
    assert record_dict["success_count"] == 2
    assert record_dict["failed_count"] == 0

def test_register_train_run_real_shape(db):
    result = {
        "status": "completed",
        "trainable_symbols": ["NIFTY", "RELIANCE"],
        "training_summary": {
            "price_model": {"total": 2, "success": 2, "failed": 0},
            "rl_agent": {"total": 2, "success": 1, "failed": 1}
        }
    }
    record_dict = register_orchestration_run(db, "train", "catalog_filter", "5m", result)
    assert record_dict["selected_symbols_count"] == 2
    assert record_dict["ready_symbols_count"] == 2
    assert record_dict["success_count"] == 3 # 2 price + 1 RL
    assert record_dict["failed_count"] == 1  # 1 RL
    assert record_dict["summary"]["trainable_symbols"] == ["NIFTY", "RELIANCE"]
    assert record_dict["summary"]["price_model"]["success"] == 2
    assert record_dict["summary"]["rl_agent"]["failed"] == 1

def test_register_execution_run_with_guardrails(db):
    guardrail_sum = {
        "execution_enabled": True,
        "allowed_actions": ["BUY"],
        "max_symbols_per_run": 1,
        "allowed_count": 1,
        "blocked_count": 1
    }
    result = {
        "status": "completed",
        "symbols": ["NIFTY", "SENSEX"],
        "execution_ready_symbols": ["NIFTY", "SENSEX"],
        "summary": {"total": 1, "success": 1, "skipped": 0, "failed": 0},
        "guardrail_summary": guardrail_sum
    }
    
    # Register
    record_dict = register_orchestration_run(db, "execution", "explicit", "5m", result)
    
    # Verify persisted summary
    summary = record_dict["summary"]
    assert "guardrail_summary" in summary
    assert summary["guardrail_summary"]["blocked_count"] == 1
    assert summary["guardrail_summary"]["allowed_actions"] == ["BUY"]
    
    # Verify cycle pass-through persistence
    cycle_result = {
        "status": "completed",
        "summary": {"selected_symbols": 1},
        "execution": {
            "guardrail_summary": guardrail_sum
        }
    }
    cycle_record = register_orchestration_run(db, "cycle", "explicit", "5m", cycle_result)
    assert cycle_record["summary"]["guardrail_summary"]["blocked_count"] == 1

def test_register_run_with_overrides(db):
    override_ctx = {
        "active_symbols": ["NIFTY"],
        "applied": [{"symbol": "NIFTY", "override_action": "SKIP"}]
    }
    result = {
        "status": "completed",
        "symbols": ["NIFTY"],
        "execution_ready_symbols": ["NIFTY"],
        "summary": {"total": 1, "success": 0, "skipped": 1, "failed": 0},
        "overrides": override_ctx
    }
    
    # Register execution
    record = register_orchestration_run(db, "execution", "explicit", "5m", result)
    assert record["summary"]["override_summary"]["applied_count"] == 1
    assert record["summary"]["override_summary"]["active_symbols"] == ["NIFTY"]
    
    # Register cycle
    cycle_result = {
        "status": "completed",
        "summary": {"selected_symbols": 1},
        "execution": {
            "overrides": override_ctx
        }
    }
    record_cycle = register_orchestration_run(db, "cycle", "explicit", "5m", cycle_result)
    assert record_cycle["summary"]["override_summary"]["applied_count"] == 1

def test_register_run_with_dispatch(db):
    dispatch_sum = {
        "new_dispatches": 1,
        "duplicate_skips": 1
    }
    # Execution
    exec_result = {
        "status": "completed",
        "symbols": ["NIFTY", "SENSEX"],
        "execution_ready_symbols": ["NIFTY", "SENSEX"],
        "summary": {"total": 2, "success": 1, "skipped": 1, "failed": 0},
        "dispatch_summary": dispatch_sum
    }
    record_exec = register_orchestration_run(db, "execution", "explicit", "5m", exec_result)
    assert record_exec["summary"]["dispatch_summary"]["new_dispatches"] == 1
    assert record_exec["summary"]["dispatch_summary"]["duplicate_skips"] == 1

    # Cycle
    cycle_result = {
        "status": "completed",
        "summary": {"selected_symbols": 2},
        "execution": {
            "dispatch_summary": dispatch_sum
        }
    }
    record_cycle = register_orchestration_run(db, "cycle", "explicit", "5m", cycle_result)
    assert record_cycle["summary"]["dispatch_summary"]["new_dispatches"] == 1
    assert record_cycle["summary"]["dispatch_summary"]["duplicate_skips"] == 1
