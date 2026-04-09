import pytest
from unittest.mock import patch, MagicMock
from prefect.testing.utilities import prefect_test_harness
from backend.orchestration.flows import (
    train_price_models_flow,
    train_rl_agents_flow,
    daily_training_flow
)

@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture():
    with prefect_test_harness():
        yield

def test_train_price_models_flow(mocker):
    # Mock symbols and task
    mocker.patch("backend.orchestration.flows.get_train_symbols", return_value=["BTCUSDT", "ETHUSDT"])
    mock_task = mocker.patch("backend.orchestration.flows.train_price_model_task", return_value="path/to/model")
    
    results = train_price_models_flow(epochs=5)
    
    assert len(results) == 2
    assert results == ["path/to/model", "path/to/model"]
    assert mock_task.call_count == 2
    mock_task.assert_any_call("BTCUSDT", "5m", epochs=5)

def test_train_rl_agents_flow(mocker):
    mocker.patch("backend.orchestration.flows.get_train_symbols", return_value=["BTCUSDT"])
    mock_task = mocker.patch("backend.orchestration.flows.train_rl_agent_task", return_value="path/to/rl")
    
    results = train_rl_agents_flow(episodes=10)
    
    assert len(results) == 1
    assert results == ["path/to/rl"]
    mock_task.assert_called_once_with("BTCUSDT", "5m", episodes=10)

def test_daily_training_flow(mocker):
    # Mock the sub-flows
    mock_price_flow = mocker.patch("backend.orchestration.flows.train_price_models_flow", return_value=["p1"])
    mock_rl_flow = mocker.patch("backend.orchestration.flows.train_rl_agents_flow", return_value=["r1"])
    
    result = daily_training_flow()
    
    assert result == {"price_models": ["p1"], "rl_agents": ["r1"]}
    mock_price_flow.assert_called_once()
    mock_rl_flow.assert_called_once()
