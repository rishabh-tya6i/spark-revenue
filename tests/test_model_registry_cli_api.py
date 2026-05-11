import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

# --- CLI Tests ---

def test_list_models_cli(capsys):
    """
    Verify list-models CLI output.
    """
    with patch("backend.orchestration.cli.list_models") as mock_list:
        # Mock ORM records
        mock_rec = MagicMock()
        mock_rec.id = 123
        mock_rec.symbol = "NIFTY"
        mock_rec.interval = "5m"
        mock_rec.model_type = "price_model"
        mock_rec.status = "success"
        mock_rec.is_active = 1
        mock_rec.created_ts = datetime(2026, 5, 10, 19, 0)
        
        mock_list.return_value = [mock_rec]
        
        with patch("sys.argv", ["cli.py", "list-models", "--symbol", "NIFTY"]):
            cli_main()
            
            captured = capsys.readouterr()
            assert "NIFTY" in captured.out
            assert "123" in captured.out
            assert "price_model" in captured.out
            assert "Y" in captured.out # Active flag

def test_show_latest_model_cli(capsys):
    """
    Verify show-latest-model CLI output.
    """
    with patch("backend.orchestration.cli.get_latest_active_model") as mock_get:
        mock_rec = MagicMock()
        mock_rec.id = 123
        mock_rec.symbol = "NIFTY"
        mock_rec.interval = "5m"
        mock_rec.model_type = "price_model"
        mock_rec.status = "success"
        mock_rec.is_active = 1
        mock_rec.artifact_path = "path/to/model"
        mock_rec.created_ts = datetime(2026, 5, 10, 19, 0)
        mock_rec.trainer_run_id = None
        mock_rec.notes = None
        
        mock_get.return_value = mock_rec
        
        with patch("sys.argv", ["cli.py", "show-latest-model", "--symbol", "NIFTY", "--interval", "5m", "--model-type", "price_model"]):
            cli_main()
            
            captured = capsys.readouterr()
            assert "--- Latest Active Model Record ---" in captured.out
            assert "SYMBOL" in captured.out
            assert "NIFTY" in captured.out
            assert "ARTIFACT_PATH" in captured.out
            assert "path/to/model" in captured.out

# --- API Tests ---

def test_get_models_api():
    """
    Verify GET /orchestration/models endpoint.
    """
    with patch("backend.orchestration.app.list_models") as mock_list:
        mock_list.return_value = []
        response = client.get("/orchestration/models?symbol=NIFTY")
        assert response.status_code == 200
        assert response.json() == []

def test_get_latest_model_api():
    """
    Verify GET /orchestration/models/latest endpoint.
    """
    with patch("backend.orchestration.app.get_latest_active_model") as mock_get:
        mock_rec = MagicMock()
        mock_rec.id = 1
        mock_rec.symbol = "NIFTY"
        mock_rec.interval = "5m"
        mock_rec.model_type = "price_model"
        mock_rec.artifact_path = "path/to/artifact"
        mock_rec.status = "success"
        mock_rec.is_active = 1
        mock_rec.trainer_run_id = None
        mock_rec.notes = None
        mock_rec.created_ts = datetime(2026, 5, 10, 19, 0)
        
        mock_get.return_value = mock_rec
        
        response = client.get("/orchestration/models/latest?symbol=NIFTY&interval=5m&model_type=price_model")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "NIFTY"
        assert data["artifact_path"] == "path/to/artifact"
        assert data["is_active"] is True

def test_get_latest_model_404():
    """
    Verify 404 behavior when no model is found.
    """
    with patch("backend.orchestration.app.get_latest_active_model") as mock_get:
        mock_get.return_value = None
        response = client.get("/orchestration/models/latest?symbol=NONE&interval=5m&model_type=price_model")
        assert response.status_code == 404
        assert "active model found" in response.json()["detail"].lower()
