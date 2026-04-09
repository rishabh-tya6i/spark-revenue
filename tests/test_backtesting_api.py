import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from backend.backtesting.app import app
from backend.backtesting.schemas import BacktestRunOut, BacktestMetricsOut

client = TestClient(app)

@pytest.fixture
def mock_run_out():
    return BacktestRunOut(
        id=1,
        strategy_name="rule_based",
        symbol="BTCUSDT",
        interval="5m",
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
        initial_capital=10000.0,
        final_capital=11000.0,
        status="COMPLETED",
        created_ts=datetime.utcnow(),
        completed_ts=datetime.utcnow()
    )

@pytest.fixture
def mock_metrics_out():
    return BacktestMetricsOut(
        backtest_id=1,
        metrics={"win_rate": 0.6, "max_drawdown": -0.05, "sharpe": 1.5}
    )

def test_run_backtest_api(mock_run_out, mock_metrics_out):
    with patch("backend.backtesting.service.BacktestingService.run_backtest", return_value=(mock_run_out, mock_metrics_out)):
        response = client.post("/backtest/run", json={
            "symbol": "BTCUSDT",
            "start_ts": "2024-01-01T00:00:00",
            "end_ts": "2024-01-02T00:00:00"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["run"]["id"] == 1
        assert "win_rate" in data["metrics"]["metrics"]

def test_get_run_api(mock_run_out):
    with patch("backend.backtesting.service.BacktestingService.get_backtest_run", return_value=mock_run_out):
        response = client.get("/backtest/run/1")
        assert response.status_code == 200
        assert response.json()["symbol"] == "BTCUSDT"

def test_get_metrics_api(mock_metrics_out):
    with patch("backend.backtesting.service.BacktestingService.get_backtest_metrics", return_value=mock_metrics_out):
        response = client.get("/backtest/metrics/1")
        assert response.status_code == 200
        assert response.json()["metrics"]["win_rate"] == 0.6
