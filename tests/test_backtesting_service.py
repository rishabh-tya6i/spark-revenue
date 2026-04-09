import pytest
from datetime import datetime, timedelta
from backend.db import Base, engine, SessionLocal, OhlcBar, BacktestRun
from backend.backtesting.service import BacktestingService
from backend.backtesting.schemas import BacktestRequest

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(OhlcBar).delete()
        session.query(BacktestRun).delete()
        
        # Seed some data
        base_ts = datetime.utcnow() - timedelta(days=1)
        for i in range(100):
            ts = base_ts + timedelta(minutes=i*5)
            session.add(OhlcBar(
                symbol="BTCUSDT",
                interval="5m",
                exchange="BINANCE",
                start_ts=ts,
                end_ts=ts + timedelta(minutes=5),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1000.0
            ))
        session.commit()
    yield

def test_backtest_service_run_success():
    service = BacktestingService()
    
    start_ts = datetime.utcnow() - timedelta(days=2)
    end_ts = datetime.utcnow() + timedelta(days=1)
    
    request = BacktestRequest(
        symbol="BTCUSDT",
        interval="5m",
        start_ts=start_ts,
        end_ts=end_ts,
        initial_capital=10000.0
    )
    
    run, metrics = service.run_backtest(request)
    
    assert run.status == "COMPLETED"
    assert run.final_capital is not None
    assert "win_rate" in metrics.metrics
    assert "sharpe" in metrics.metrics

def test_backtest_service_insufficient_data():
    service = BacktestingService()
    
    # Request symbol with no data
    request = BacktestRequest(
        symbol="INVALID",
        interval="5m",
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
        initial_capital=10000.0
    )
    
    with pytest.raises(ValueError, match="Insufficient bars"):
        service.run_backtest(request)
    
    # Check if run record exists with FAILED status
    with SessionLocal() as session:
        run = session.query(BacktestRun).filter(BacktestRun.symbol == "INVALID").first()
        assert run is not None
        assert run.status == "FAILED"
