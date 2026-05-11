import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

SYMBOLS = ["NIFTY", "SENSEX"]
DETAILS = [
    {
        "symbol": "NIFTY",
        "interval": "5m",
        "ohlc_count": 100,
        "feature_count": 100,
        "min_ohlc_required": 77,
        "min_feature_required": 77,
        "trainable": True,
        "reason": None,
    },
    {
        "symbol": "SENSEX",
        "interval": "5m",
        "ohlc_count": 10,
        "feature_count": 0,
        "min_ohlc_required": 77,
        "min_feature_required": 77,
        "trainable": False,
        "reason": "missing_ohlc_and_features",
    },
]

# --- CLI Tests ---

def test_show_trainability_cli(capsys):
    """
    Test show-trainability CLI command.
    """
    with patch("backend.orchestration.cli.get_training_universe") as mock_universe, \
         patch("backend.orchestration.cli.get_trainable_symbols") as mock_trainable:
        
        mock_universe.return_value = SYMBOLS
        mock_trainable.return_value = (["NIFTY"], DETAILS)
        
        with patch("sys.argv", ["cli.py", "show-trainability", "--mode", "catalog_filter", "--interval", "5m"]):
            cli_main()
            
            captured = capsys.readouterr()
            assert "--- Trainability Inspection (Mode: catalog_filter, Interval: 5m) ---" in captured.out
            assert "NIFTY" in captured.out
            assert "SENSEX" in captured.out
            assert "True" in captured.out
            assert "False" in captured.out
            assert "missing_ohlc_and_features" in captured.out

# --- API Tests ---

def test_get_trainability_api():
    """
    Test GET /orchestration/trainability API.
    """
    with patch("backend.orchestration.app.get_training_universe") as mock_universe, \
         patch("backend.orchestration.app.get_trainable_symbols") as mock_trainable:
        
        mock_universe.return_value = SYMBOLS
        mock_trainable.return_value = (["NIFTY"], DETAILS)
        
        response = client.get("/orchestration/trainability?mode=catalog_filter&interval=5m")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "catalog_filter"
        assert data["interval"] == "5m"
        assert data["symbols"] == SYMBOLS
        assert data["trainable_symbols"] == ["NIFTY"]
        assert len(data["details"]) == 2
        assert data["details"][0]["symbol"] == "NIFTY"
        assert data["details"][0]["trainable"] is True

def test_get_trainability_api_default():
    """
    Test GET /orchestration/trainability API with default params.
    """
    with patch("backend.orchestration.app.get_training_universe") as mock_universe, \
         patch("backend.orchestration.app.get_trainable_symbols") as mock_trainable:
        
        mock_universe.return_value = SYMBOLS
        mock_trainable.return_value = (["NIFTY"], DETAILS)
        
        response = client.get("/orchestration/trainability")
        
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "interval" in data
        assert data["trainable_symbols"] == ["NIFTY"]
