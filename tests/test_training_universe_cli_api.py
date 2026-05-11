import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

# --- CLI Tests ---

def test_show_universe_cli(capsys):
    """
    Test show-universe CLI command.
    """
    with patch("backend.orchestration.cli.get_training_universe") as mock_get_universe:
        mock_get_universe.return_value = ["NIFTY", "SENSEX"]
        
        # Patch sys.argv to simulate: python -m backend.orchestration.cli show-universe --mode explicit
        with patch("sys.argv", ["cli.py", "show-universe", "--mode", "explicit"]):
            # We also need to patch SessionLocal used in CLI
            with patch("backend.orchestration.cli.SessionLocal") as mock_session:
                cli_main()
                
                captured = capsys.readouterr()
                assert "--- Training Universe (Mode: explicit) ---" in captured.out
                assert "1. NIFTY" in captured.out
                assert "2. SENSEX" in captured.out

# --- API Tests ---

def test_get_universe_api():
    """
    Test GET /orchestration/universe API.
    """
    # Note: We patch the function inside orchestration.app
    with patch("backend.orchestration.app.get_training_universe") as mock_get_universe:
        mock_get_universe.return_value = ["NIFTY", "SENSEX"]
        
        response = client.get("/orchestration/universe?mode=explicit")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "explicit"
        assert data["symbols"] == ["NIFTY", "SENSEX"]

def test_get_universe_api_default_mode():
    """
    Test GET /orchestration/universe without mode param.
    """
    with patch("backend.orchestration.app.get_training_universe") as mock_get_universe:
        mock_get_universe.return_value = ["NIFTY"]
        
        # Mock settings.TRAIN_UNIVERSE_MODE inside orchestration.app
        with patch("backend.orchestration.app.settings") as mock_settings:
            mock_settings.TRAIN_UNIVERSE_MODE = "catalog_filter"
            
            response = client.get("/orchestration/universe")
            
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "catalog_filter"
            assert data["symbols"] == ["NIFTY"]
