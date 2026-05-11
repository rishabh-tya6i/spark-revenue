import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

# --- CLI Tests ---

def test_run_operational_cycle_cli(capsys):
    with patch("backend.orchestration.cli.run_operational_cycle_core") as mock_core:
        mock_core.return_value = {
            "status": "completed",
            "mode": "explicit",
            "interval": "5m",
            "summary": {
                "selected_symbols": 1,
                "inference_ready_symbols": 1,
                "decision_success": 1,
                "execution_ready_symbols": 1,
                "execution_success": 1,
                "execution_skipped": 0,
                "execution_failed": 0
            },
            "inference": {"status": "completed", "summary": {"decision": {"success": 1, "total": 1}}},
            "execution": {"status": "completed", "summary": {"success": 1, "failed": 0}}
        }
        
        with patch("sys.argv", ["cli.py", "run-operational-cycle", "--mode", "explicit"]):
            cli_main()
            captured = capsys.readouterr()
            assert "=== End-to-End Operational Cycle Report ===" in captured.out
            assert "Overall Status: completed" in captured.out
            assert "Execution Success:     1" in captured.out

# --- API Tests ---

def test_run_cycle_api():
    with patch("backend.orchestration.app.run_operational_cycle_core") as mock_core:
        mock_core.return_value = {"status": "completed", "summary": {}}
        
        response = client.post("/orchestration/run-cycle?mode=explicit")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
