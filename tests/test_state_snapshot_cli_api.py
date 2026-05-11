import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

# --- CLI Tests ---

def test_show_state_cli(capsys):
    with patch("backend.orchestration.cli.build_operational_state_snapshot") as mock_snap:
        mock_snap.return_value = {
            "mode": "catalog_filter",
            "interval": "5m",
            "symbols": ["NIFTY"],
            "inference_ready_symbols": ["NIFTY"],
            "execution_ready_symbols": ["NIFTY"],
            "models": {
                "symbols_checked": 1,
                "price_model_available": ["NIFTY"],
                "rl_agent_available": ["NIFTY"],
                "missing_price_model": [],
                "missing_rl_agent": []
            },
            "decisions": {
                "symbols_checked": 1,
                "has_decision": ["NIFTY"],
                "actionable": ["NIFTY"],
                "hold": [],
                "missing": []
            },
            "execution_state": {
                "symbols_checked": 1,
                "has_orders": ["NIFTY"],
                "open_positions": ["NIFTY"],
                "no_activity": []
            },
            "latest_runs": {
                "train": {"id": 1, "status": "completed", "created_ts": "2024-05-10T10:00:00"},
                "inference": None,
                "execution": None,
                "cycle": None
            }
        }
        
        with patch("sys.argv", ["cli.py", "show-state", "--mode", "catalog_filter"]):
            cli_main()
            captured = capsys.readouterr()
            assert "Operational State Snapshot" in captured.out
            assert "NIFTY" in captured.out
            assert "ID 1" in captured.out

# --- API Tests ---

def test_get_state_api():
    with patch("backend.orchestration.app.build_operational_state_snapshot") as mock_snap:
        mock_snap.return_value = {
            "mode": "explicit",
            "interval": "5m",
            "symbols": ["NIFTY"],
            "models": {},
            "decisions": {},
            "execution_state": {},
            "latest_runs": {}
        }
        
        response = client.get("/orchestration/state?mode=explicit")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "explicit"
        assert "symbols" in data
        assert "models" in data
