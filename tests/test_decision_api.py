import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime
from backend.decision_engine.app import app
from backend.decision_engine.schemas import FusedDecisionOut

client = TestClient(app)

@pytest.fixture
def mock_decision():
    return FusedDecisionOut(
        id=1,
        symbol="BTCUSDT",
        interval="5m",
        timestamp=datetime.utcnow(),
        decision_label="BULLISH",
        decision_score=0.7,
        price_direction="UP",
        price_confidence=0.8,
        rl_action="BUY",
        rl_confidence=0.9
    )

def test_compute_decision_api(mock_decision):
    with patch('backend.decision_engine.service.DecisionEngineService.compute_and_store_decision', return_value=mock_decision):
        with patch('backend.decision_engine.service.DecisionEngineService.generate_alert_from_decision', return_value=None):
            response = client.post("/decision/compute", json={"symbol": "BTCUSDT", "interval": "5m"})
            assert response.status_code == 200
            data = response.json()
            assert data["decision"]["symbol"] == "BTCUSDT"
            assert data["decision"]["decision_label"] == "BULLISH"
            assert data["alert"] is None

def test_get_latest_decision_api(mock_decision):
    with patch('backend.decision_engine.service.DecisionEngineService.get_latest_decision', return_value=mock_decision):
        response = client.get("/decision/latest?symbol=BTCUSDT")
        assert response.status_code == 200
        assert response.json()["symbol"] == "BTCUSDT"

def test_get_latest_decision_404():
    with patch('backend.decision_engine.service.DecisionEngineService.get_latest_decision', return_value=None):
        response = client.get("/decision/latest?symbol=UNKNOWN")
        assert response.status_code == 404
