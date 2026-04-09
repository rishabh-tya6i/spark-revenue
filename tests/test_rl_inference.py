import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import numpy as np
from backend.rl.app import app

client = TestClient(app)

@pytest.fixture
def mock_rl_inference_data():
    # Last observation features
    features = np.random.randn(10, 5)
    prices = np.linspace(100, 110, 10)
    
    with patch('backend.rl.service.SessionLocal') as mock_session:
        with patch('backend.rl.service.load_rl_data', return_value=(features, prices)):
            yield features, prices

@pytest.fixture
def mock_rl_model():
    mock_model_instance = MagicMock()
    # Mock predict to return BUY (2)
    mock_model_instance.predict.return_value = (2, None)
    
    with patch('backend.rl.service.get_rl_model', return_value=mock_model_instance):
        yield mock_model_instance

def test_rl_action_endpoint(mock_rl_inference_data, mock_rl_model):
    response = client.post(
        "/rl/action",
        json={"symbol": "BTCUSDT", "interval": "5m"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["action"] == "BUY"
    assert data["action_index"] == 2
