import pytest
from unittest.mock import patch, MagicMock
from backend.orchestration.cycle_runner import (
    run_operational_cycle_core,
    summarize_cycle_results
)
from backend.orchestration.run_history import register_orchestration_run

def test_summarize_cycle_results():
    inf = {
        "symbols": ["A", "B"],
        "inference_ready_symbols": ["A"],
        "summary": {
            "decision": {"success": 1, "total": 1}
        }
    }
    exe = {
        "execution_ready_symbols": ["A"],
        "summary": {
            "success": 1, "skipped": 0, "failed": 0
        }
    }
    
    summary = summarize_cycle_results(inf, exe)
    assert summary["selected_symbols"] == 2
    assert summary["inference_ready_symbols"] == 1
    assert summary["decision_success"] == 1
    assert summary["execution_ready_symbols"] == 1
    assert summary["execution_success"] == 1

def test_run_operational_cycle_core_skipped():
    with patch("backend.orchestration.cycle_runner.run_inference_universe_core") as mock_inf, \
         patch("backend.orchestration.cycle_runner.run_universe_execution_core") as mock_exe, \
         patch("backend.orchestration.run_history.register_orchestration_run") as mock_reg:
        
        mock_reg.return_value = {"id": 1}
        mock_inf.return_value = {
            "status": "skipped",
            "reason": "no_inference_ready_symbols",
            "symbols": ["NIFTY", "SENSEX"],
            "inference_ready_symbols": [],
            "summary": {"decision": {"success": 0, "total": 0}}
        }
        
        res = run_operational_cycle_core(mode="explicit")
        assert res["status"] == "skipped"
        assert res["reason"] == "no_inference_ready_symbols"
        assert res["execution"]["status"] == "skipped"
        
        # Verify zeroed summary as per contract
        sum_data = res["summary"]
        assert sum_data["selected_symbols"] == 0
        assert sum_data["inference_ready_symbols"] == 0
        assert sum_data["decision_success"] == 0
        assert sum_data["execution_ready_symbols"] == 0
        assert sum_data["execution_success"] == 0
        assert sum_data["execution_skipped"] == 0
        assert sum_data["execution_failed"] == 0
        
        assert mock_exe.call_count == 0

def test_run_operational_cycle_core_completed():
    with patch("backend.orchestration.cycle_runner.run_inference_universe_core") as mock_inf, \
         patch("backend.orchestration.cycle_runner.run_universe_execution_core") as mock_exe, \
         patch("backend.orchestration.run_history.register_orchestration_run") as mock_reg:
        
        mock_reg.return_value = {"id": 2}
        mock_inf.return_value = {
            "status": "completed",
            "symbols": ["NIFTY"],
            "inference_ready_symbols": ["NIFTY"],
            "summary": {"decision": {"success": 1, "total": 1}}
        }
        # Execution success
        mock_exe.return_value = {
            "status": "completed",
            "execution_ready_symbols": ["NIFTY"],
            "summary": {"success": 1, "skipped": 0, "failed": 0}
        }
        
        res = run_operational_cycle_core(mode="explicit")
        assert res["status"] == "completed"
        assert res["summary"]["execution_success"] == 1
        assert mock_exe.call_count == 1

def test_run_operational_cycle_core_guardrail_blocked():
    with patch("backend.orchestration.cycle_runner.run_inference_universe_core") as mock_inf, \
         patch("backend.orchestration.cycle_runner.run_universe_execution_core") as mock_exe, \
         patch("backend.orchestration.run_history.register_orchestration_run") as mock_reg:
        
        mock_reg.return_value = {"id": 3}
        mock_inf.return_value = {
            "status": "completed",
            "symbols": ["NIFTY", "SENSEX"],
            "inference_ready_symbols": ["NIFTY", "SENSEX"],
            "summary": {"decision": {"success": 2, "total": 2}}
        }
        
        # Execution blocked by guardrails
        guardrail_blocked_result = {
            "status": "skipped",
            "reason": "blocked_by_guardrails",
            "execution_ready_symbols": ["NIFTY", "SENSEX"],
            "guardrails": {
                "execution_enabled": True,
                "allowed_actions": ["BUY"],
                "max_symbols_per_run": 1,
                "requested_ready_symbols": ["NIFTY", "SENSEX"],
                "allowed_symbols": ["NIFTY"],
                "blocked_symbols": [{"symbol": "SENSEX", "reason": "disallowed_action"}]
            },
            "guardrail_summary": {
                "execution_enabled": True,
                "allowed_actions": ["BUY"],
                "max_symbols_per_run": 1,
                "allowed_count": 1,
                "blocked_count": 1
            },
            "execution_results": [],
            "summary": {"total": 0, "success": 0, "skipped": 0, "failed": 0}
        }
        mock_exe.return_value = guardrail_blocked_result
        
        res = run_operational_cycle_core(mode="explicit")
        
        # Cycle itself is completed (inference ran), but execution was skipped
        assert res["status"] == "completed"
        assert res["execution"]["status"] == "skipped"
        assert res["execution"]["reason"] == "blocked_by_guardrails"
        
        # Guardrail details must be preserved in the execution sub-result
        assert "guardrails" in res["execution"]
        assert "guardrail_summary" in res["execution"]
        assert res["execution"]["guardrail_summary"]["blocked_count"] == 1
        
        # Summary should reflect inference success but zero execution success
        assert res["summary"]["decision_success"] == 2
        assert res["summary"]["execution_success"] == 0
        assert res["summary"]["execution_ready_symbols"] == 2
