import logging
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..db import OrchestrationRunRecord, TrainedModelRecord, DecisionRecord, ExecutionOrder, ExecutionPosition
from .run_history import orchestration_run_to_dict
from .universe import get_training_universe
from .inference_readiness import get_inference_ready_symbols
from .execution_readiness import get_execution_ready_symbols
from .model_registry import get_latest_active_model
from .execution_guardrails import parse_allowed_actions
from .execution_overrides import list_active_execution_overrides, get_active_execution_override
from .execution_dispatch import has_been_dispatched
from .execution_staleness import evaluate_execution_source_staleness
from ..config import settings

logger = logging.getLogger(__name__)

def get_latest_dispatch_summary(session: Session, symbols: List[str], interval: str) -> dict:
    """
    Summarizes dispatch status for the latest candidate (override or decision) per symbol.
    """
    already_dispatched = []
    not_dispatched = []

    for sym in symbols:
        # Determine candidate source
        # 1. Active Override?
        override = get_active_execution_override(session, sym, interval)
        if override:
            if has_been_dispatched(session, "override", override.id):
                already_dispatched.append(sym)
            else:
                not_dispatched.append(sym)
            continue
        
        # 2. Latest Decision?
        decision = session.query(DecisionRecord)\
            .filter(DecisionRecord.symbol == sym, DecisionRecord.interval == interval)\
            .order_by(desc(DecisionRecord.timestamp))\
            .first()
        
        if decision:
            if has_been_dispatched(session, "decision", decision.id):
                already_dispatched.append(sym)
            else:
                not_dispatched.append(sym)
        else:
            # No decision, no override -> not dispatched (nothing to dispatch)
            not_dispatched.append(sym)

    return {
        "symbols_checked": len(symbols),
        "already_dispatched": already_dispatched,
        "not_dispatched": not_dispatched
    }

def get_latest_staleness_summary(session: Session, symbols: List[str], interval: str) -> dict:
    """
    Summarizes staleness for the latest candidate (override or decision) per symbol.
    """
    stale_decisions = []
    stale_overrides = []
    fresh_candidates = []

    for sym in symbols:
        override = get_active_execution_override(session, sym, interval)
        if override:
            staleness = evaluate_execution_source_staleness(override_ts=override.created_ts)
            if staleness["override_stale"]:
                stale_overrides.append(sym)
            else:
                fresh_candidates.append(sym)
            continue
        
        decision = session.query(DecisionRecord)\
            .filter(DecisionRecord.symbol == sym, DecisionRecord.interval == interval)\
            .order_by(desc(DecisionRecord.timestamp))\
            .first()
        
        if decision:
            staleness = evaluate_execution_source_staleness(decision_ts=decision.timestamp)
            if staleness["decision_stale"]:
                stale_decisions.append(sym)
            else:
                fresh_candidates.append(sym)

    return {
        "symbols_checked": len(symbols),
        "stale_decision_symbols": stale_decisions,
        "stale_override_symbols": stale_overrides,
        "fresh_candidates": fresh_candidates
    }

def get_latest_run_by_type(session: Session, run_type: str) -> Optional[dict]:
    """
    Fetches the newest OrchestrationRunRecord for a given type.
    """
    record = session.query(OrchestrationRunRecord)\
        .filter(OrchestrationRunRecord.run_type == run_type)\
        .order_by(desc(OrchestrationRunRecord.created_ts))\
        .first()
    
    if not record:
        return None
    return orchestration_run_to_dict(record)

def get_latest_active_models_summary(session: Session, symbols: List[str], interval: str) -> dict:
    """
    Summarizes availability of active models for the provided symbols.
    """
    price_avail = []
    rl_avail = []
    missing_price = []
    missing_rl = []

    for sym in symbols:
        # Check price model
        pm = get_latest_active_model(session, sym, interval, "price_model")
        if pm:
            price_avail.append(sym)
        else:
            missing_price.append(sym)
            
        # Check RL agent
        rl = get_latest_active_model(session, sym, interval, "rl_agent")
        if rl:
            rl_avail.append(sym)
        else:
            missing_rl.append(sym)

    return {
        "symbols_checked": len(symbols),
        "price_model_available": price_avail,
        "rl_agent_available": rl_avail,
        "missing_price_model": missing_price,
        "missing_rl_agent": missing_rl
    }

def get_latest_decision_summary(session: Session, symbols: List[str], interval: str) -> dict:
    """
    Summarizes the latest DecisionRecords for the provided symbols.
    """
    has_decision = []
    actionable = []
    hold = []
    missing = []

    for sym in symbols:
        record = session.query(DecisionRecord)\
            .filter(DecisionRecord.symbol == sym, DecisionRecord.interval == interval)\
            .order_by(desc(DecisionRecord.timestamp))\
            .first()
        
        if record:
            has_decision.append(sym)
            if record.rl_action in ["BUY", "SELL"]:
                actionable.append(sym)
            else:
                # Default to hold for HOLD or unexpected values
                hold.append(sym)
        else:
            missing.append(sym)

    return {
        "symbols_checked": len(symbols),
        "has_decision": has_decision,
        "actionable": actionable,
        "hold": hold,
        "missing": missing
    }

def get_latest_execution_summary(session: Session, symbols: List[str]) -> dict:
    """
    Summarizes recent execution activity for the provided symbols.
    """
    has_orders = []
    open_positions = []
    no_activity = []

    for sym in symbols:
        # Check for orders
        order = session.query(ExecutionOrder)\
            .filter(ExecutionOrder.symbol == sym)\
            .first()
        
        # Check for non-zero position
        pos = session.query(ExecutionPosition)\
            .filter(ExecutionPosition.symbol == sym)\
            .order_by(desc(ExecutionPosition.updated_ts))\
            .first()
        
        active_pos = pos and pos.quantity != 0
        
        if order:
            has_orders.append(sym)
        
        if active_pos:
            open_positions.append(sym)
            
        if not order and not active_pos:
            no_activity.append(sym)

    return {
        "symbols_checked": len(symbols),
        "has_orders": has_orders,
        "open_positions": open_positions,
        "no_activity": no_activity
    }

def build_operational_state_snapshot(
    session: Session, 
    mode: Optional[str] = None, 
    interval: Optional[str] = None
) -> dict:
    """
    Aggregates universe selection, readiness, latest runs, and state into a single snapshot.
    """
    selected_mode = mode or settings.TRAIN_UNIVERSE_MODE
    selected_interval = interval or settings.TRAIN_DEFAULT_INTERVAL or "5m"
    
    # 1. Resolve Universe
    symbols = get_training_universe(session, mode=selected_mode)
    
    # 2. Compute Readiness
    inf_ready_symbols, _ = get_inference_ready_symbols(session, symbols, selected_interval)
    exec_ready_symbols, _ = get_execution_ready_symbols(session, symbols, selected_interval)
    
    # 3. Aggregations
    model_summary = get_latest_active_models_summary(session, symbols, selected_interval)
    decision_summary = get_latest_decision_summary(session, symbols, selected_interval)
    exec_summary = get_latest_execution_summary(session, symbols)
    
    # 4. Latest Runs
    latest_runs = {
        "train": get_latest_run_by_type(session, "train"),
        "inference": get_latest_run_by_type(session, "inference"),
        "execution": get_latest_run_by_type(session, "execution"),
        "cycle": get_latest_run_by_type(session, "cycle"),
    }
    
    return {
        "mode": selected_mode,
        "interval": selected_interval,
        "symbols": symbols,
        "inference_ready_symbols": inf_ready_symbols,
        "execution_ready_symbols": exec_ready_symbols,
        "models": model_summary,
        "decisions": decision_summary,
        "execution_state": exec_summary,
        "execution_guardrails": {
            "execution_enabled": settings.EXECUTION_ENABLED,
            "allowed_actions": parse_allowed_actions(settings.EXECUTION_ALLOWED_ACTIONS),
            "max_symbols_per_run": settings.EXECUTION_MAX_SYMBOLS_PER_RUN
        },
        "execution_overrides": {
            "active_symbols": [o.symbol for o in list_active_execution_overrides(session, selected_interval)],
            "actions": {o.symbol: o.override_action for o in list_active_execution_overrides(session, selected_interval)}
        },
        "execution_dispatch": get_latest_dispatch_summary(session, symbols, selected_interval),
        "execution_staleness": get_latest_staleness_summary(session, symbols, selected_interval),
        "latest_runs": latest_runs
    }
