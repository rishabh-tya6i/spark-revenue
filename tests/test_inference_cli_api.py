import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

# --- CLI Tests ---

def test_show_inference_readiness_cli(capsys):
    with patch("backend.orchestration.cli.get_training_universe") as mock_uni, \
         patch("backend.orchestration.cli.get_inference_ready_symbols") as mock_ready:
        
        mock_uni.return_value = ["NIFTY"]
        mock_ready.return_value = (["NIFTY"], [{
            "symbol": "NIFTY",
            "price_model_ready": True,
            "rl_model_ready": True,
            "feature_ready": True,
            "ready": True,
            "reason": None
        }])
        
        with patch("sys.argv", ["cli.py", "show-inference-readiness", "--mode", "explicit"]):
            cli_main()
            
            captured = capsys.readouterr()
            assert "NIFTY" in captured.out
            assert "Y" in captured.out # check columns

def test_run_universe_inference_cli(capsys):
    with patch("backend.orchestration.cli.run_inference_universe_core") as mock_core:
        mock_core.return_value = {
            "status": "completed",
            "symbols": ["NIFTY"],
            "inference_ready_symbols": ["NIFTY"],
            "summary": {
                "price_prediction": {"success": 1, "total": 1},
                "rl_action": {"success": 1, "total": 1},
                "decision": {"success": 1, "total": 1}
            },
            "price_results": [], "rl_results": [], "decision_results": []
        }
        
        with patch("sys.argv", ["cli.py", "run-universe-inference", "--mode", "explicit"]):
            cli_main()
            
            captured = capsys.readouterr()
            assert "Universe Inference Execution Report" in captured.out
            assert "Status: completed" in captured.out
            assert "Symbols Ready:    1" in captured.out

# --- API Tests ---

def test_get_inference_readiness_api():
    with patch("backend.orchestration.app.get_inference_ready_symbols") as mock_ready, \
         patch("backend.orchestration.app.get_training_universe") as mock_uni:
        
        mock_uni.return_value = ["NIFTY"]
        mock_ready.return_value = (["NIFTY"], [])
        
        response = client.get("/orchestration/inference-readiness?mode=explicit")
        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == ["NIFTY"]
        assert data["inference_ready_symbols"] == ["NIFTY"]

def test_run_inference_api():
    with patch("backend.orchestration.app.run_inference_universe_core") as mock_core:
        mock_core.return_value = {"status": "completed"}
        
        response = client.post("/orchestration/run-inference?mode=explicit")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
