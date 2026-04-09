import logging
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException

from ..db import SessionLocal, OhlcBar, BacktestRun, BacktestMetric
from ..config import settings
from . import engine, schemas

logger = logging.getLogger(__name__)

class BacktestingService:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def load_bars(self, symbol: str, interval: str, start_ts: datetime, end_ts: datetime) -> List[Dict]:
        with self.session_factory() as session:
            bars = session.query(OhlcBar).filter(
                OhlcBar.symbol == symbol,
                OhlcBar.interval == interval,
                OhlcBar.start_ts >= start_ts,
                OhlcBar.start_ts <= end_ts
            ).order_by(OhlcBar.start_ts.asc()).all()
            
            return [
                {
                    "timestamp": b.start_ts,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": float(b.volume)
                } for b in bars
            ]

    def run_backtest(self, request: schemas.BacktestRequest) -> Tuple[schemas.BacktestRunOut, schemas.BacktestMetricsOut]:
        initial_capital = request.initial_capital or settings.BACKTEST_INITIAL_CAPITAL
        
        # 1. Initialize Run Record
        with self.session_factory() as session:
            run = BacktestRun(
                strategy_name=request.strategy_name,
                symbol=request.symbol,
                interval=request.interval,
                start_ts=request.start_ts,
                end_ts=request.end_ts,
                initial_capital=initial_capital,
                status="RUNNING",
                created_ts=datetime.utcnow()
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            run_id = run.id

        try:
            # 2. Load Data
            bars = self.load_bars(request.symbol, request.interval, request.start_ts, request.end_ts)
            if len(bars) < 20:
                with self.session_factory() as session:
                    run = session.query(BacktestRun).get(run_id)
                    run.status = "FAILED"
                    run.details = "Insufficient historical data (min 20 bars required)"
                    session.commit()
                raise ValueError(f"Insufficient bars: {len(bars)}")

            # 3. Strategy Setup
            if request.strategy_name == "rule_based":
                strategy = engine.RuleBasedStrategy(window=20)
            else:
                # Default to rule_based for v1
                strategy = engine.RuleBasedStrategy(window=20)

            # 4. Run Core Engine
            history, final_capital = engine.run_backtest(
                bars=bars,
                strategy=strategy,
                initial_capital=initial_capital,
                transaction_cost_bps=settings.BACKTEST_TRANSACTION_COST_BPS
            )

            # 5. Compute Metrics
            equity = engine.compute_equity_curve(history)
            metrics_dict = {
                "win_rate": engine.compute_win_rate(history),
                "max_drawdown": engine.compute_max_drawdown(equity),
                "sharpe": engine.compute_sharpe(equity)
            }

            # 6. Finalize Run Record
            with self.session_factory() as session:
                run = session.query(BacktestRun).get(run_id)
                run.final_capital = final_capital
                run.status = "COMPLETED"
                run.completed_ts = datetime.utcnow()
                
                # Store Metrics
                for name, val in metrics_dict.items():
                    m = BacktestMetric(backtest_id=run_id, metric_name=name, metric_value=val)
                    session.add(m)
                
                session.commit()
                session.refresh(run)
                
                return schemas.BacktestRunOut.model_validate(run), schemas.BacktestMetricsOut(backtest_id=run_id, metrics=metrics_dict)

        except Exception as e:
            logger.error(f"Backtest {run_id} failed: {e}")
            with self.session_factory() as session:
                run = session.query(BacktestRun).get(run_id)
                run.status = "FAILED"
                run.details = str(e)
                session.commit()
            raise

    def get_backtest_run(self, run_id: int) -> Optional[schemas.BacktestRunOut]:
        with self.session_factory() as session:
            run = session.query(BacktestRun).get(run_id)
            return schemas.BacktestRunOut.model_validate(run) if run else None

    def get_backtest_metrics(self, run_id: int) -> Optional[schemas.BacktestMetricsOut]:
        with self.session_factory() as session:
            metrics = session.query(BacktestMetric).filter(BacktestMetric.backtest_id == run_id).all()
            if not metrics:
                return None
            return schemas.BacktestMetricsOut(
                backtest_id=run_id,
                metrics={m.metric_name: m.metric_value for m in metrics}
            )

# Router
router = APIRouter()

@router.post("/backtest/run")
async def run_backtest(request: schemas.BacktestRequest):
    service = BacktestingService()
    try:
        run, metrics = service.run_backtest(request)
        return {"run": run, "metrics": metrics}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/backtest/run/{run_id}", response_model=schemas.BacktestRunOut)
async def get_run(run_id: int):
    service = BacktestingService()
    run = service.get_backtest_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.get("/backtest/metrics/{run_id}", response_model=schemas.BacktestMetricsOut)
async def get_metrics(run_id: int):
    service = BacktestingService()
    metrics = service.get_backtest_metrics(run_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return metrics
