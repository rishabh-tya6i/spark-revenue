import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

FAKE_RESULTS = {
    "status": "completed",
    "trainable_symbols": ["NIFTY"],
    "data_prep": {"symbols": ["NIFTY"]},
    "price_model_results": [
        {"symbol": "NIFTY", "status": "success", "artifact_path": "models/nifty.pt", "error": None}
    ],
    "rl_agent_results": [
        {"symbol": "NIFTY", "status": "success", "artifact_path": "models/nifty.zip", "error": None}
    ],
    "training_summary": {
        "price_model": {"total": 1, "success": 1, "failed": 0},
        "rl_agent": {"total": 1, "success": 1, "failed": 0}
    }
}

# --- CLI Tests ---

def test_train_trainable_cli(capsys):
    """
    Test train-trainable CLI command.
    """
    with patch("backend.orchestration.cli.run_train_trainable_core") as mock_run:
        mock_run.return_value = FAKE_RESULTS
        
        with patch("sys.argv", ["cli.py", "train-trainable", "--mode", "catalog_filter", "--lookback-days", "30"]):
            cli_main()
            
            captured = capsys.readouterr()
            assert "--- Training Run Execution Report ---" in captured.out
            assert "Price Models: 1/1 succeeded" in captured.out
            assert "RL Agents:    1/1 succeeded" in captured.out
            assert "NIFTY: OK" in captured.out
            assert "Artifact: models/nifty.pt" in captured.out

# --- API Tests ---

def test_train_trainable_api():
    """
    Test POST /orchestration/train-trainable API.
    """
    with patch("backend.orchestration.app.run_train_trainable_core") as mock_run:
        mock_run.return_value = FAKE_RESULTS
        
        response = client.post("/orchestration/train-trainable?mode=catalog_filter&lookback_days=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["trainable_symbols"] == ["NIFTY"]
        assert data["training_summary"]["price_model"]["success"] == 1
        assert len(data["price_model_results"]) == 1
        assert data["price_model_results"][0]["status"] == "success"

def test_run_daily_api():
    """
    Test POST /orchestration/run-daily API returns the enhanced structure.
    """
    with patch("backend.orchestration.app.daily_training_flow") as mock_run:
        mock_run.return_value = FAKE_RESULTS
        
        response = client.post("/orchestration/run-daily")
        
        assert response.status_code == 200
        data = response.json()
        assert "training_summary" in data
        assert data["status"] == "completed"
