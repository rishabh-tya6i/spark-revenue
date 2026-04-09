import pytest
import sys
from unittest.mock import patch
from backend.orchestration.cli import main

def test_cli_train_price_models(mocker):
    mock_flow = mocker.patch("backend.orchestration.cli.train_price_models_flow")
    
    with patch.object(sys, 'argv', ['cli.py', 'train-price-models', '--symbols', 'BTCUSDT', '--epochs', '5']):
        main()
    
    mock_flow.assert_called_once_with(symbols=['BTCUSDT'], interval=None, epochs=5)

def test_cli_run_daily(mocker):
    mock_flow = mocker.patch("backend.orchestration.cli.daily_training_flow")
    
    with patch.object(sys, 'argv', ['cli.py', 'run-daily']):
        main()
    
    mock_flow.assert_called_once()
