import pytest
import os
import shutil
import numpy as np
from unittest.mock import patch
from backend.price_model.train import train_price_model
from backend.config import settings

@pytest.fixture
def mock_dataset():
    # Mock build_price_model_dataset to return synthetic data
    X = np.random.randn(100, settings.PRICE_MODEL_INPUT_WINDOW, 5)
    y = np.random.randint(0, 3, size=(100,))
    with patch('backend.price_model.train.build_price_model_dataset', return_value=(X, y)):
        yield X, y

def test_train_price_model_creates_file(mock_dataset, tmp_path):
    # Set the model dir and mlflow tracking uri to a temporary path
    test_model_dir = tmp_path / "models"
    test_mlruns_dir = tmp_path / "mlruns"
    
    import mlflow
    mlflow.set_tracking_uri(f"file://{test_mlruns_dir}")
    
    with patch('backend.price_model.train.settings.PRICE_MODEL_DIR', str(test_model_dir)):
        # Run training for 1 epoch
        model_path = train_price_model("BTCUSDT", "5m", epochs=1, batch_size=10)
        
        assert os.path.exists(model_path)
        assert model_path.endswith(".pt")
