import pytest
from unittest.mock import MagicMock, patch
from backend.orchestration.flows import run_daily_training_flow_core, run_train_trainable_core

def test_daily_flow_skip_behavior():
    """
    Verify that the daily flow skips training if no symbols are trainable.
    Ensures that empty result blocks are returned.
    """
    mock_prep = MagicMock()
    mock_prep.return_value = {
        "symbols": ["NIFTY", "SENSEX"],
        "trainable_symbols": [],
        "trainability": [
            {"symbol": "NIFTY", "trainable": False, "reason": "insufficient_ohlc"},
            {"symbol": "SENSEX", "trainable": False, "reason": "insufficient_ohlc"}
        ]
    }
    
    mock_price_train = MagicMock()
    mock_rl_train = MagicMock()
    
    with patch("backend.orchestration.flows.SessionLocal"), \
         patch("backend.orchestration.run_history.register_orchestration_run") as mock_reg:
        mock_reg.return_value = {"id": 1}
        result = run_daily_training_flow_core(
            prep_runner=mock_prep,
            price_train_runner=mock_price_train,
            rl_train_runner=mock_rl_train
        )
    
    assert result["status"] == "skipped"
    assert result["reason"] == "no_trainable_symbols"
    assert result["training_summary"]["price_model"]["total"] == 0
    assert result["price_model_results"] == []
    
    mock_price_train.assert_not_called()
    mock_rl_train.assert_not_called()

def test_daily_flow_filtering_behavior():
    """
    Verify that only trainable symbols are passed to training flows.
    """
    mock_prep = MagicMock()
    mock_prep.return_value = {
        "symbols": ["NIFTY", "SENSEX"],
        "trainable_symbols": ["NIFTY"],
        "trainability": [
            {"symbol": "NIFTY", "trainable": True},
            {"symbol": "SENSEX", "trainable": False, "reason": "insufficient_ohlc"}
        ]
    }
    
    mock_price_train = MagicMock()
    mock_price_train.return_value = [{"symbol": "NIFTY", "trainer": "price_model", "interval": "5m", "status": "success", "artifact_path": "pt"}]
    mock_rl_train = MagicMock()
    mock_rl_train.return_value = [{"symbol": "NIFTY", "trainer": "rl_agent", "interval": "5m", "status": "success", "artifact_path": "zip"}]
    
    with patch("backend.orchestration.flows.persist_training_results") as mock_persist, \
         patch("backend.orchestration.flows.SessionLocal"), \
         patch("backend.orchestration.run_history.register_orchestration_run") as mock_reg:
        
        mock_reg.return_value = {"id": 2}
        # Mock enrichment
        mock_persist.side_effect = lambda session, results: [
            {**r, "registry_record_id": 1, "active": True} for r in results
        ]
        
        result = run_daily_training_flow_core(
            prep_runner=mock_prep,
            price_train_runner=mock_price_train,
            rl_train_runner=mock_rl_train
        )
    
    assert result["status"] == "completed"
    assert result["trainable_symbols"] == ["NIFTY"]
    assert result["training_summary"]["price_model"]["success"] == 1
    
    mock_rl_train.assert_called_once_with(symbols=["NIFTY"])

    # Verify registry enrichment
    assert result["price_model_results"][0]["registry_record_id"] == 1
    assert result["price_model_results"][0]["active"] is True
    assert result["rl_agent_results"][0]["registry_record_id"] == 1
    assert result["rl_agent_results"][0]["active"] is True

@patch("backend.orchestration.flows.prepare_training_data_core")
@patch("backend.orchestration.flows.run_price_models_training_core")
@patch("backend.orchestration.flows.run_rl_agents_training_core")
def test_train_trainable_core_structure(mock_rl, mock_price, mock_prep):
    """
    Verify that the train-trainable core helper returns the full structured result.
    """
    mock_prep.return_value = {
        "symbols": ["NIFTY"],
        "trainable_symbols": ["NIFTY"],
        "trainability": [{"symbol": "NIFTY", "trainable": True}]
    }
    mock_price.return_value = [{"symbol": "NIFTY", "trainer": "price_model", "interval": "5m", "status": "success", "artifact_path": "pt"}]
    mock_rl.return_value = [{"symbol": "NIFTY", "trainer": "rl_agent", "interval": "5m", "status": "success", "artifact_path": "zip"}]
    
    with patch("backend.orchestration.flows.persist_training_results") as mock_persist, \
         patch("backend.orchestration.flows.SessionLocal"), \
         patch("backend.orchestration.run_history.register_orchestration_run") as mock_reg:
        
        mock_reg.return_value = {"id": 3}
        mock_persist.side_effect = lambda session, results: [
            {**r, "registry_record_id": 1, "active": True} for r in results
        ]
        result = run_train_trainable_core(mode="explicit")
    
    assert result["status"] == "completed"
    assert "data_prep" in result
    assert "training_summary" in result
    assert len(result["price_model_results"]) == 1
    assert result["price_model_results"][0]["status"] == "success"
    # Verify registry enrichment
    assert result["price_model_results"][0]["registry_record_id"] == 1
    assert result["price_model_results"][0]["active"] is True
