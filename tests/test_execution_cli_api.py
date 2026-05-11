import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
from datetime import datetime

from backend.main import app
from backend.orchestration.cli import main as cli_main
from backend.orchestration.execution_runner import run_universe_execution_core

client = TestClient(app)

# --- Core Tests ---

def test_run_universe_execution_core_logic():
    with patch("backend.orchestration.execution_runner.SessionLocal") as mock_session_cls, \
         patch("backend.orchestration.execution_runner.get_training_universe") as mock_get_uni, \
         patch("backend.orchestration.execution_runner.get_execution_ready_symbols") as mock_get_ready, \
         patch("backend.orchestration.execution_runner.evaluate_execution_guardrails") as mock_guard, \
         patch("backend.orchestration.execution_runner.execute_latest_decisions_for_symbols") as mock_exec, \
         patch("backend.orchestration.execution_runner.register_orchestration_run") as mock_reg, \
         patch("backend.orchestration.execution_runner.get_active_execution_override") as mock_get_ov:
        
        mock_get_ov.return_value = None
        mock_guard.return_value = {
            "execution_enabled": True,
            "allowed_actions": ["BUY", "SELL"],
            "max_symbols_per_run": 5,
            "requested_ready_symbols": ["NIFTY"],
            "allowed_symbols": ["NIFTY"],
            "blocked_symbols": []
        }
        mock_reg.return_value = {"id": 1}
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_get_uni.return_value = ["NIFTY", "SENSEX"]
        
        # Scenario 1: None ready
        mock_get_ready.return_value = ([], [{"ready": False, "symbol": "NIFTY", "reason": "missing"}])
        res = run_universe_execution_core(mode="explicit")
        assert res["status"] == "skipped"
        assert res["execution_ready_symbols"] == []
        
        # Scenario 2: One ready
        mock_get_ready.return_value = (["NIFTY"], [{"ready": True, "symbol": "NIFTY"}])
        mock_exec.return_value = ([{"symbol": "NIFTY", "status": "success"}], {})
        
        res = run_universe_execution_core(mode="explicit")
        assert res["status"] == "completed"
        assert res["execution_ready_symbols"] == ["NIFTY"]
        assert len(res["execution_results"]) == 1

# --- CLI Tests ---

def test_show_execution_readiness_cli(capsys):
    with patch("backend.orchestration.cli.get_training_universe") as mock_uni, \
         patch("backend.orchestration.cli.get_execution_ready_symbols") as mock_ready:
        
        mock_uni.return_value = ["NIFTY"]
        mock_ready.return_value = (["NIFTY"], [{
            "symbol": "NIFTY", "decision_id": 101, "decision_label": "BULLISH",
            "decision_score": 0.85, "rl_action": "BUY", "ready": True, "reason": None,
            "override_active": True, "override_action": "SKIP"
        }])
        
        with patch("sys.argv", ["cli.py", "show-execution-readiness", "--mode", "explicit"]):
            cli_main()
            captured = capsys.readouterr()
            assert "NIFTY" in captured.out
            assert "BUY" in captured.out
            assert "SKIP" in captured.out
            assert "OVR" in captured.out
            assert "Y" in captured.out

def test_run_universe_execution_cli(capsys):
    with patch("backend.orchestration.cli.run_universe_execution_core") as mock_core:
        mock_core.return_value = {
            "status": "completed",
            "symbols": ["NIFTY"],
            "execution_ready_symbols": ["NIFTY"],
            "execution_results": [{"symbol": "NIFTY", "status": "success", "side": "BUY", "quantity": 1.0, "price": 200.0, "order_id": 12, "error": None}],
            "summary": {"total": 1, "success": 1, "skipped": 0, "failed": 0},
            "readiness": []
        }
        
        with patch("sys.argv", ["cli.py", "run-universe-execution", "--mode", "explicit"]):
            cli_main()
            captured = capsys.readouterr()
            assert "Universe Execution Report" in captured.out
            assert "Success:        1" in captured.out
            assert "ORDER_ID" in captured.out

def test_list_execution_dispatches_cli_api(capsys):
    # API: List
    with patch("backend.orchestration.app.list_dispatch_records") as mock_list:
        mock_list.return_value = []
        response = client.get("/orchestration/execution-dispatches?symbol=NIFTY&interval=5m")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    # CLI: List
    with patch("backend.orchestration.cli.list_dispatch_records") as mock_list_cli:
        mock_list_cli.return_value = [MagicMock(
            id=1, symbol="NIFTY", interval="5m", source_type="decision", 
            source_id=101, dispatched_action="BUY", status="executed", 
            order_id=55, created_ts=datetime.now()
        )]
        with patch("sys.argv", ["cli.py", "list-execution-dispatches"]):
            cli_main()
            captured = capsys.readouterr()
            assert "NIFTY" in captured.out
            assert "BUY" in captured.out
            assert "executed" in captured.out

# --- API Tests ---

def test_get_execution_readiness_api():
    with patch("backend.orchestration.app.get_execution_ready_symbols") as mock_ready, \
         patch("backend.orchestration.app.get_training_universe") as mock_uni:
        
        mock_uni.return_value = ["NIFTY"]
        mock_ready.return_value = (["NIFTY"], [])
        
        response = client.get("/orchestration/execution-readiness?mode=explicit")
        assert response.status_code == 200
        data = response.json()
        assert data["execution_ready_symbols"] == ["NIFTY"]

def test_run_execution_api():
    with patch("backend.orchestration.app.run_universe_execution_core") as mock_core:
        mock_core.return_value = {"status": "completed"}
        
        response = client.post("/orchestration/run-execution?mode=explicit")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

def test_show_execution_guardrails_cli(capsys):
    with patch("backend.orchestration.cli.get_training_universe") as mock_uni, \
         patch("backend.orchestration.cli.get_execution_ready_symbols") as mock_ready, \
         patch("backend.orchestration.cli.evaluate_execution_guardrails") as mock_guard:
        
        mock_uni.return_value = ["NIFTY"]
        mock_ready.return_value = (["NIFTY"], [{"symbol": "NIFTY", "ready": True, "rl_action": "BUY"}])
        mock_guard.return_value = {
            "execution_enabled": True,
            "allowed_actions": ["BUY", "SELL"],
            "max_symbols_per_run": 5,
            "requested_ready_symbols": ["NIFTY"],
            "allowed_symbols": ["NIFTY"],
            "blocked_symbols": []
        }
        
        with patch("sys.argv", ["cli.py", "show-execution-guardrails", "--mode", "explicit"]):
            cli_main()
            captured = capsys.readouterr()
            assert "Execution Guardrail Inspection" in captured.out
            assert "Execution Enabled:     True" in captured.out
            assert "Allowed Symbols:       NIFTY" in captured.out

def test_get_execution_guardrails_api():
    with patch("backend.orchestration.app.get_training_universe") as mock_uni, \
         patch("backend.orchestration.app.get_execution_ready_symbols") as mock_ready, \
         patch("backend.orchestration.app.evaluate_execution_guardrails") as mock_guard:
        
        mock_uni.return_value = ["NIFTY"]
        mock_ready.return_value = (["NIFTY"], [{"symbol": "NIFTY", "ready": True}])
        mock_guard.return_value = {
            "execution_enabled": True,
            "allowed_actions": ["BUY", "SELL"],
            "max_symbols_per_run": 5,
            "requested_ready_symbols": ["NIFTY"],
            "allowed_symbols": ["NIFTY"],
            "blocked_symbols": []
        }
        
        response = client.get("/orchestration/execution-guardrails?mode=explicit")
        assert response.status_code == 200
        data = response.json()
        assert data["guardrails"]["execution_enabled"] is True
        assert data["guardrail_summary"]["allowed_count"] == 1

def test_run_universe_execution_blocked_cli(capsys):
    with patch("backend.orchestration.cli.run_universe_execution_core") as mock_core:
        mock_core.return_value = {
            "status": "skipped",
            "reason": "blocked_by_guardrails",
            "symbols": ["NIFTY", "SENSEX"],
            "execution_ready_symbols": ["NIFTY", "SENSEX"],
            "guardrails": {
                "execution_enabled": True,
                "allowed_actions": ["BUY"],
                "max_symbols_per_run": 5,
                "requested_ready_symbols": ["NIFTY", "SENSEX"],
                "allowed_symbols": ["NIFTY"],
                "blocked_symbols": [{"symbol": "SENSEX", "reason": "disallowed_action"}]
            },
            "guardrail_summary": {
                "execution_enabled": True,
                "allowed_actions": ["BUY"],
                "max_symbols_per_run": 5,
                "allowed_count": 1,
                "blocked_count": 1
            },
            "execution_results": [],
            "summary": {"total": 0, "success": 0, "skipped": 0, "failed": 0},
            "readiness": []
        }
        
        with patch("sys.argv", ["cli.py", "run-universe-execution", "--mode", "explicit"]):
            cli_main()
            captured = capsys.readouterr()
            assert "Reason: blocked_by_guardrails" in captured.out
            assert "Blocked Symbols:" in captured.out
            assert "SENSEX: disallowed_action" in captured.out

def test_run_execution_blocked_api():
    with patch("backend.orchestration.app.run_universe_execution_core") as mock_core:
        mock_core.return_value = {
            "status": "skipped",
            "reason": "blocked_by_guardrails",
            "guardrails": {"execution_enabled": False, "blocked_symbols": []},
            "guardrail_summary": {"allowed_count": 0, "blocked_count": 0, "execution_enabled": False}
        }
        
        response = client.post("/orchestration/run-execution?mode=explicit")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["reason"] == "blocked_by_guardrails"
        assert "guardrails" in data
        assert "guardrail_summary" in data

def test_execution_overrides_cli_api(capsys):
    # API: Create
    with patch("backend.orchestration.app.set_execution_override") as mock_set:
        mock_set.return_value = {"symbol": "NIFTY", "override_action": "SKIP"}
        response = client.post("/orchestration/execution-overrides", json={
            "symbol": "NIFTY", "interval": "5m", "override_action": "SKIP"
        })
        assert response.status_code == 200
        assert response.json()["override_action"] == "SKIP"

    # API: List
    with patch("backend.orchestration.app.list_active_execution_overrides") as mock_list:
        mock_list.return_value = []
        response = client.get("/orchestration/execution-overrides?interval=5m")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    # API: Delete
    with patch("backend.orchestration.app.clear_execution_override") as mock_clear:
        mock_clear.return_value = {"symbol": "NIFTY"}
        response = client.delete("/orchestration/execution-overrides?symbol=NIFTY&interval=5m")
        assert response.status_code == 200

    # CLI: Set
    with patch("backend.orchestration.cli.set_execution_override") as mock_set_cli:
        with patch("sys.argv", ["cli.py", "set-execution-override", "--symbol", "NIFTY", "--interval", "5m", "--action", "SKIP"]):
            cli_main()
            captured = capsys.readouterr()
            assert "Override set successfully" in captured.out

    # CLI: List
    with patch("backend.orchestration.cli.list_active_execution_overrides") as mock_list_cli:
        mock_list_cli.return_value = [MagicMock(symbol="NIFTY", interval="5m", override_action="SKIP", created_ts=datetime.now(), reason=None)]
        with patch("sys.argv", ["cli.py", "list-execution-overrides"]):
            cli_main()
            captured = capsys.readouterr()
            assert "NIFTY" in captured.out
            assert "SKIP" in captured.out
