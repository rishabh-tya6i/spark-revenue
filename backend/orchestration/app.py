from fastapi import APIRouter, Depends, Query, Body, HTTPException
from typing import Optional, List
from sqlalchemy.orm import Session
from .flows import (
    daily_training_flow, 
    run_train_trainable_core, 
    run_inference_universe_core,
    run_universe_execution_core,
    run_operational_cycle_core
)
from .universe import get_training_universe
from .data_prep import prepare_training_data_core
from .trainability import get_trainable_symbols
from .inference_readiness import get_inference_ready_symbols
from .execution_readiness import get_execution_ready_symbols
from .model_registry import list_models, get_latest_active_model, model_record_to_dict
from .run_history import (
    list_orchestration_runs, 
    get_orchestration_run, 
    orchestration_run_to_dict
)
from .state_snapshot import build_operational_state_snapshot
from .execution_guardrails import evaluate_execution_guardrails, build_execution_guardrail_summary
from .execution_overrides import (
    set_execution_override, 
    clear_execution_override, 
    list_active_execution_overrides
)
from .execution_dispatch import list_dispatch_records, execution_dispatch_to_dict
from ..db import get_db
from ..config import settings

router = APIRouter()

@router.post("/orchestration/run-daily")
async def trigger_daily():
    """
    Triggers the daily master training flow (Prep -> Train).
    Returns the enhanced structured results including preparation and training outcomes.
    """
    results = daily_training_flow()
    return results

@router.get("/orchestration/universe")
async def get_universe(
    mode: Optional[str] = Query(None, description="Universe selection mode ('explicit' or 'catalog_filter')"),
    limit: Optional[int] = Query(None, description="Limit results"),
    db: Session = Depends(get_db)
):
    """
    Returns the current training universe based on selection mode.
    """
    selected_mode = mode or settings.TRAIN_UNIVERSE_MODE
    symbols = get_training_universe(db, mode=selected_mode)
    
    if limit:
        symbols = symbols[:limit]
        
    return {
        "mode": selected_mode,
        "symbols": symbols
    }

@router.post("/orchestration/prepare-training-data")
async def prepare_training_data(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    lookback_days: Optional[int] = Query(None),
    sync_first: bool = Query(True)
):
    """
    Triggers the training data preparation (OHLC + Features).
    Includes trainability evaluation in the summary.
    """
    summary = prepare_training_data_core(
        mode=mode,
        interval=interval,
        lookback_days=lookback_days,
        sync_first=sync_first
    )
    return summary

@router.get("/orchestration/trainability")
async def get_trainability(
    mode: Optional[str] = Query(None, description="Universe selection mode"),
    interval: Optional[str] = Query(None, description="Interval to check"),
    db: Session = Depends(get_db)
):
    """
    Evaluates trainability for the current universe without triggering data preparation.
    """
    selected_mode = mode or settings.TRAIN_UNIVERSE_MODE
    selected_interval = interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
    
    symbols = get_training_universe(db, mode=selected_mode)
    trainable_symbols, details = get_trainable_symbols(db, symbols, selected_interval)
    
    return {
        "mode": selected_mode,
        "interval": selected_interval,
        "symbols": symbols,
        "trainable_symbols": trainable_symbols,
        "details": details
    }

@router.post("/orchestration/train-trainable")
async def train_trainable(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    lookback_days: Optional[int] = Query(None),
    sync_first: bool = Query(True),
    epochs: int = Query(10),
    episodes: Optional[int] = Query(None)
):
    """
    Operator-facing endpoint that triggers data preparation followed by training for only ready symbols.
    Returns the full structured execution report.
    """
    results = run_train_trainable_core(
        mode=mode,
        interval=interval,
        lookback_days=lookback_days,
        sync_first=sync_first,
        epochs=epochs,
        episodes=episodes
    )
    return results

@router.get("/orchestration/models")
async def get_models(
    symbol: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    model_type: Optional[str] = Query(None),
    active_only: bool = Query(False),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    """
    Lists registered models based on filters.
    """
    records = list_models(db, symbol, interval, model_type, active_only, limit)
    return [model_record_to_dict(r) for r in records]

@router.get("/orchestration/models/latest")
async def get_latest_model(
    symbol: str = Query(...),
    interval: str = Query(...),
    model_type: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Returns the latest active model record for given parameters.
    """
    record = get_latest_active_model(db, symbol, interval, model_type)
    if not record:
        raise HTTPException(status_code=404, detail="No active model found for given parameters")
    return model_record_to_dict(record)

@router.get("/orchestration/inference-readiness")
async def get_inference_readiness(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Evaluates inference readiness for the current universe.
    """
    selected_mode = mode or settings.TRAIN_UNIVERSE_MODE
    selected_interval = interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
    
    symbols = get_training_universe(db, mode=selected_mode)
    ready_symbols, details = get_inference_ready_symbols(db, symbols, selected_interval)
    
    return {
        "mode": selected_mode,
        "interval": selected_interval,
        "symbols": symbols,
        "inference_ready_symbols": ready_symbols,
        "details": details
    }

@router.post("/orchestration/run-inference")
async def trigger_universe_inference(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None)
):
    """
    Triggers orchestrated inference for the current universe.
    Only ready symbols are processed.
    """
    results = run_inference_universe_core(
        mode=mode,
        interval=interval
    )
    return results

@router.get("/orchestration/execution-readiness")
async def get_execution_readiness(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    require_actionable: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Evaluates execution readiness for the current universe based on latest decisions.
    """
    selected_mode = mode or settings.TRAIN_UNIVERSE_MODE
    selected_interval = interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
    
    symbols = get_training_universe(db, mode=selected_mode)
    ready_symbols, details = get_execution_ready_symbols(
        db, symbols, selected_interval, require_actionable=require_actionable
    )
    
    return {
        "mode": selected_mode,
        "interval": selected_interval,
        "symbols": symbols,
        "execution_ready_symbols": ready_symbols,
        "details": details
    }

@router.post("/orchestration/run-execution")
async def trigger_universe_execution(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    require_actionable: bool = Query(True)
):
    """
    Triggers orchestrated paper execution for the current universe.
    Only execution-ready symbols (with actionable decisions) are processed.
    """
    results = run_universe_execution_core(
        mode=mode,
        interval=interval,
        require_actionable=require_actionable
    )
    return results

@router.post("/orchestration/run-cycle")
async def trigger_operational_cycle(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    require_actionable: bool = Query(True)
):
    """
    Triggers a full end-to-end operational cycle (Inference -> Decision -> Execution).
    """
    results = run_operational_cycle_core(
        mode=mode,
        interval=interval,
        require_actionable=require_actionable
    )
    return results

@router.get("/orchestration/runs")
async def get_runs(
    run_type: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    """
    Returns a list of recent orchestration runs.
    """
    records = list_orchestration_runs(db, run_type=run_type, limit=limit)
    return [orchestration_run_to_dict(r) for r in records]

@router.get("/orchestration/runs/{run_id}")
async def get_run_detail(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns detailed metadata for a single orchestration run.
    """
    record = get_orchestration_run(db, run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run record {run_id} not found")
    return orchestration_run_to_dict(record)

@router.get("/orchestration/state")
async def get_state(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns the latest operational state snapshot for the current universe.
    Includes readiness, model availability, and latest run summaries.
    """
    snapshot = build_operational_state_snapshot(db, mode=mode, interval=interval)
    return snapshot

@router.get("/orchestration/execution-guardrails")
async def get_execution_guardrails(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    require_actionable: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Evaluates global execution guardrails for the current universe without executing trades.
    Useful for operator inspection.
    """
    selected_mode = mode or settings.TRAIN_UNIVERSE_MODE
    selected_interval = interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
    
    symbols = get_training_universe(db, mode=selected_mode)
    _, details = get_execution_ready_symbols(
        db, symbols, selected_interval, require_actionable=require_actionable
    )
    
    guardrail_result = evaluate_execution_guardrails(details)
    guardrail_summary = build_execution_guardrail_summary(guardrail_result)
    
    return {
        "mode": selected_mode,
        "interval": selected_interval,
        "execution_ready_symbols": [d["symbol"] for d in details if d.get("ready")],
        "guardrails": guardrail_result,
        "guardrail_summary": guardrail_summary
    }

@router.post("/orchestration/execution-overrides")
async def set_override(
    symbol: str = Body(...),
    interval: str = Body(...),
    override_action: str = Body(...),
    reason: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Sets a manual execution override for a symbol and interval.
    """
    try:
        res = set_execution_override(db, symbol, interval, override_action, reason)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/orchestration/execution-overrides")
async def delete_override(
    symbol: str = Query(...),
    interval: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Clears the active manual override for a symbol and interval.
    """
    res = clear_execution_override(db, symbol, interval)
    if not res:
        raise HTTPException(status_code=404, detail="No active override found")
    return res

@router.get("/orchestration/execution-overrides")
async def get_overrides(
    interval: Optional[str] = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """
    Lists all currently active execution overrides.
    """
    from .execution_overrides import execution_override_to_dict
    records = list_active_execution_overrides(db, interval, limit)
    return [execution_override_to_dict(r) for r in records]

@router.get("/orchestration/execution-dispatches")
async def get_dispatches(
    symbol: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """
    Returns a list of recent execution dispatches.
    """
    records = list_dispatch_records(db, symbol, interval, limit)
    return [execution_dispatch_to_dict(r) for r in records]

@router.get("/orchestration/execution-staleness")
async def get_execution_staleness(
    mode: Optional[str] = Query(None),
    interval: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns detailed staleness information for candidates in the current universe.
    """
    from .state_snapshot import get_latest_staleness_summary
    selected_mode = mode or settings.TRAIN_UNIVERSE_MODE
    selected_interval = interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
    
    symbols = get_training_universe(db, mode=selected_mode)
    _, details = get_execution_ready_symbols(db, symbols, selected_interval)
    
    summary = get_latest_staleness_summary(db, symbols, selected_interval)
    
    return {
        "mode": selected_mode,
        "interval": selected_interval,
        "symbols": symbols,
        "details": details,
        "summary": summary
    }
