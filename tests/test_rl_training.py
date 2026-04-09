import pytest
import os
from unittest.mock import patch
import numpy as np
from backend.rl.train import train_rl_agent
from backend.config import settings

@pytest.fixture
def mock_rl_data():
    features = np.random.randn(200, 5)
    prices = np.linspace(100, 110, 200)
    with patch('backend.rl.train.load_rl_data', return_value=(features, prices)):
        yield features, prices

def test_train_rl_agent_creates_file(mock_rl_data, tmp_path):
    test_model_dir = tmp_path / "models"
    with patch('backend.rl.train.settings.RL_AGENT_MODEL_DIR', str(test_model_dir)):
        # Run training for small episodes
        model_path = train_rl_agent("TEST", "5m", episodes=1)
        
        assert os.path.exists(model_path)
        assert model_path.endswith(".zip")
