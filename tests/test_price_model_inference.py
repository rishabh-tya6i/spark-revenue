import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import numpy as np
import torch
from backend.price_model.app import app

client = TestClient(app)

@pytest.fixture
def mock_inference_data():
    # Mock the DB query data
    dummy_data = []
    for i in range(60):
        dummy_data.append((100.0 + i, 50.0, 100.0 + i, 100.0 + i, 100.0 + i, None))
    
    with patch('backend.price_model.service.SessionLocal') as mock_session:
        session_instance = mock_session.return_value.__enter__.return_value
        session_instance.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = dummy_data
        yield dummy_data

@pytest.fixture
def mock_model():
    # Mock the model loading and forward pass
    mock_model_instance = MagicMock()
    # Mock output logits for 3 classes
    mock_model_instance.return_value = torch.FloatTensor([[0.1, 0.8, 0.1]]) 
    
    with patch('backend.price_model.service.get_model', return_value=mock_model_instance):
        yield mock_model_instance

def test_predict_endpoint(mock_inference_data, mock_model):
    response = client.post(
        "/predict/price-path",
        json={"symbol": "BTCUSDT", "interval": "5m"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["prediction_type"] == "classification"
    assert data["label"] == "FLAT" # probability 0.8 at index 1
    assert "probabilities" in data
    assert data["probabilities"]["FLAT"] == pytest.approx(torch.softmax(torch.FloatTensor([[0.1, 0.8, 0.1]]), dim=1).numpy()[0][1])
