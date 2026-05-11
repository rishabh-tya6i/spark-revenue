import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys

from backend.main import app
from backend.orchestration.cli import main as cli_main

client = TestClient(app)

FAKE_SUMMARY = {
  "mode": "catalog_filter",
  "symbols": ["NIFTY", "SENSEX"],
  "interval": "5m",
  "start": "2026-04-01T00:00:00",
  "end": "2026-05-01T00:00:00",
  "instrument_sync_count": 0,
  "ohlc": {"NIFTY": "ok", "SENSEX": "ok"},
  "features": {"NIFTY": "ok", "SENSEX": "ok"},
  "trainability": [
    {"symbol": "NIFTY", "ohlc_count": 100, "feature_count": 100, "trainable": True, "reason": None},
    {"symbol": "SENSEX", "ohlc_count": 100, "feature_count": 100, "trainable": True, "reason": None}
  ],
  "trainable_symbols": ["NIFTY", "SENSEX"]
}

# --- CLI Tests ---

def test_prepare_training_data_cli(capsys):
    """
    Test prepare-training-data CLI command.
    """
    # Patch the core helper in the CLI module
    with patch("backend.orchestration.cli.prepare_training_data_core") as mock_prep:
        mock_prep.return_value = FAKE_SUMMARY
        
        # Simulate: python -m backend.orchestration.cli prepare-training-data --mode catalog_filter --lookback-days 30 --no-sync
        with patch("sys.argv", ["cli.py", "prepare-training-data", "--mode", "catalog_filter", "--lookback-days", "30", "--no-sync"]):
            cli_main()
            
            captured = capsys.readouterr()
            assert "--- Data Preparation Summary ---" in captured.out
            assert "Universe Mode: catalog_filter" in captured.out
            assert "Symbols: NIFTY, SENSEX" in captured.out
            assert "Interval: 5m" in captured.out
            assert "NIFTY: ok" in captured.out
            assert "SENSEX: ok" in captured.out
            
            mock_prep.assert_called_once_with(
                mode="catalog_filter",
                interval=None,
                lookback_days=30,
                sync_first=False
            )

# --- API Tests ---

def test_prepare_training_data_api():
    """
    Test POST /orchestration/prepare-training-data API.
    """
    # Patch the core helper in the app module
    with patch("backend.orchestration.app.prepare_training_data_core") as mock_prep:
        mock_prep.return_value = FAKE_SUMMARY
        
        response = client.post("/orchestration/prepare-training-data?mode=catalog_filter&lookback_days=30&sync_first=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "catalog_filter"
        assert data["symbols"] == ["NIFTY", "SENSEX"]
        assert "ohlc" in data
        assert "features" in data
        
        mock_prep.assert_called_once_with(
            mode="catalog_filter",
            interval=None,
            lookback_days=30,
            sync_first=False
        )

def test_prepare_training_data_api_default():
    """
    Test POST /orchestration/prepare-training-data API with default params.
    """
    with patch("backend.orchestration.app.prepare_training_data_core") as mock_prep:
        mock_prep.return_value = FAKE_SUMMARY
        
        response = client.post("/orchestration/prepare-training-data")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "catalog_filter"
        
        mock_prep.assert_called_once_with(
            mode=None,
            interval=None,
            lookback_days=None,
            sync_first=True
        )
