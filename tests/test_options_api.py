import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from backend.options_intel.app import app
from backend.options_intel.schemas import OptionSignalOut

client = TestClient(app)

def test_get_signal_not_found():
    response = client.get("/options/signal?symbol=NONEXIST&expiry=2024-01-01")
    assert response.status_code == 404

def test_refresh_snapshot_success():
    mock_signal = OptionSignalOut(
        id=1,
        symbol="NIFTY",
        expiry=datetime.utcnow(),
        timestamp=datetime.utcnow(),
        pcr=1.1,
        max_pain_strike=21000.0,
        call_oi_total=100000,
        put_oi_total=110000,
        signal_label="NEUTRAL",
        signal_strength=0.0
    )
    
    with patch('backend.options_intel.service.OptionsIngestor.ingest_snapshot', return_value=10):
        with patch('backend.options_intel.service.OptionsIntelService.compute_and_store_signals', return_value=mock_signal):
            payload = {"symbol": "NIFTY", "expiry": "2024-12-26T00:00:00"}
            response = client.post("/options/refresh-snapshot", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "NIFTY"
            assert data["pcr"] == 1.1

def test_get_signal_success():
    mock_signal = OptionSignalOut(
        id=1,
        symbol="NIFTY",
        expiry=datetime.utcnow(),
        timestamp=datetime.utcnow(),
        pcr=1.1,
        max_pain_strike=21000.0,
        call_oi_total=100000,
        put_oi_total=110000,
        signal_label="NEUTRAL",
        signal_strength=0.0
    )
    
    with patch('backend.options_intel.service.OptionsIntelService.get_latest_signal', return_value=mock_signal):
        response = client.get("/options/signal?symbol=NIFTY")
        assert response.status_code == 200
        assert response.json()["symbol"] == "NIFTY"
