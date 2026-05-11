import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, ANY
from backend.orchestration.utils import get_prepare_interval, get_prepare_window
from backend.orchestration.data_prep import (
    prepare_training_data_core,
    sync_instruments_core,
    backfill_ohlc_for_universe_core,
    backfill_features_for_universe_core
)

def test_prepare_utils():
    with patch("backend.orchestration.utils.settings") as mock_settings:
        mock_settings.TRAIN_PREPARE_INTERVAL = "15m"
        mock_settings.TRAIN_DEFAULT_INTERVAL = "5m"
        mock_settings.TRAIN_LOOKBACK_DAYS = 60
        
        assert get_prepare_interval() == "15m"
        
        start, end = get_prepare_window()
        # Allow for slight timing difference in test
        assert (end - start).days == 60

def test_prepare_utils_fallback():
    with patch("backend.orchestration.utils.settings") as mock_settings:
        mock_settings.TRAIN_PREPARE_INTERVAL = None
        mock_settings.TRAIN_DEFAULT_INTERVAL = "1h"
        
        assert get_prepare_interval() == "1h"

@patch("backend.orchestration.data_prep.InstrumentService")
@patch("backend.orchestration.data_prep.SessionLocal")
def test_sync_instruments_core(mock_session, mock_service_class):
    mock_service = mock_service_class.return_value
    mock_service.sync_upstox_instruments.return_value = 50
    
    count = sync_instruments_core(segments=["NSE_INDEX"])
    assert count == 50
    mock_service.sync_upstox_instruments.assert_called_once_with(segments=["NSE_INDEX"])

@patch("backend.orchestration.data_prep.OhlcIngestor")
@patch("backend.orchestration.data_prep.UpstoxMarketDataClient")
@patch("backend.orchestration.data_prep.SessionLocal")
def test_ohlc_backfill_loop(mock_session, mock_client_class, mock_ingestor_class):
    mock_ingestor = mock_ingestor_class.return_value
    
    # Mock one failure, one success
    def side_effect(symbol, **kwargs):
        if symbol == "FAIL":
            raise Exception("api error")
        return
    
    mock_ingestor.ingest_historical.side_effect = side_effect
    
    status = backfill_ohlc_for_universe_core(
        symbols=["NIFTY", "FAIL"],
        start=datetime.now(),
        end=datetime.now(),
        interval="5m"
    )
    
    assert status["NIFTY"] == "ok"
    assert "error: api error" in status["FAIL"]

@patch("backend.orchestration.data_prep.FeatureStore")
def test_feature_backfill_loop(mock_fs_class):
    mock_fs = mock_fs_class.return_value
    
    def side_effect(symbol, **kwargs):
        if symbol == "FAIL":
            raise Exception("calc error")
        return
    
    mock_fs.compute_and_store_price_features.side_effect = side_effect
    
    status = backfill_features_for_universe_core(
        symbols=["NIFTY", "FAIL"],
        start=datetime.now(),
        end=datetime.now(),
        interval="5m"
    )
    
    assert status["NIFTY"] == "ok"
    assert "error: calc error" in status["FAIL"]

@patch("backend.orchestration.data_prep.sync_instruments_core")
@patch("backend.orchestration.data_prep.get_training_universe")
@patch("backend.orchestration.data_prep.backfill_ohlc_for_universe_core")
@patch("backend.orchestration.data_prep.backfill_features_for_universe_core")
@patch("backend.orchestration.data_prep.get_trainable_symbols")
@patch("backend.orchestration.data_prep.SessionLocal")
def test_prepare_training_data_core(mock_session, mock_trainable, mock_features, mock_ohlc, mock_universe, mock_sync):
    mock_sync.return_value = 100
    mock_universe.return_value = ["NIFTY"]
    mock_ohlc.return_value = {"NIFTY": "ok"}
    mock_features.return_value = {"NIFTY": "ok"}
    mock_trainable.return_value = (["NIFTY"], [{"symbol": "NIFTY", "trainable": True}])
    
    summary = prepare_training_data_core(sync_first=True)
    
    assert summary["instrument_sync_count"] == 100
    assert summary["symbols"] == ["NIFTY"]
    assert summary["ohlc"]["NIFTY"] == "ok"
    assert summary["features"]["NIFTY"] == "ok"
    assert summary["trainable_symbols"] == ["NIFTY"]
    mock_sync.assert_called_once()

@patch("backend.orchestration.data_prep.sync_instruments_core")
@patch("backend.orchestration.data_prep.get_training_universe")
@patch("backend.orchestration.data_prep.SessionLocal")
def test_prepare_training_data_empty_universe(mock_session, mock_universe, mock_sync):
    mock_universe.return_value = []
    
    summary = prepare_training_data_core(sync_first=False)
    
    assert summary["symbols"] == []
    assert summary["instrument_sync_count"] == 0
    mock_sync.assert_not_called()
