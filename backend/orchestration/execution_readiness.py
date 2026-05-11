import logging
from typing import List, Tuple, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..db import DecisionRecord
from .execution_overrides import get_active_execution_override
from .execution_staleness import evaluate_execution_source_staleness

logger = logging.getLogger(__name__)

def check_symbol_execution_readiness(session: Session, symbol: str, interval: str, require_actionable: bool = True) -> dict:
    """
    Evaluates if a symbol is ready for paper execution based on the latest decision.
    Includes visibility into active manual overrides.
    """
    # 0. Check for manual override (visibility only)
    override = get_active_execution_override(session, symbol, interval)
    override_action = override.override_action if override else None
    override_active = override is not None

    # 1. Query latest decision
    decision = session.query(DecisionRecord).filter(
        DecisionRecord.symbol == symbol,
        DecisionRecord.interval == interval
    ).order_by(desc(DecisionRecord.timestamp)).first()
    
    # Staleness check (visibility only)
    staleness = evaluate_execution_source_staleness(
        decision_ts=None,
        override_ts=override.created_ts if override else None
    )

    if not decision:
        return {
            "symbol": symbol,
            "interval": interval,
            "ready": False,
            "reason": "missing_decision",
            "decision_id": None,
            "decision_label": None,
            "decision_score": None,
            "rl_action": None,
            "override_action": override_action,
            "override_active": override_active,
            "decision_ts": None,
            "override_created_ts": override.created_ts if override else None,
            "decision_stale": staleness["decision_stale"],
            "override_stale": staleness["override_stale"]
        }

    # 2. Evaluate actionability if required
    ready = True
    reason = None
    
    if require_actionable:
        action = decision.rl_action
        if action is None:
            ready = False
            reason = "missing_rl_action"
        elif action == "HOLD":
            ready = False
            reason = "non_actionable_decision"
        elif action not in ["BUY", "SELL"]:
            # Should not happen based on current logic, but for safety:
            ready = False
            reason = f"unknown_rl_action_{action}"

    # Staleness check (visibility only)
    staleness = evaluate_execution_source_staleness(
        decision_ts=decision.timestamp,
        override_ts=override.created_ts if override else None
    )

    return {
        "symbol": symbol,
        "interval": interval,
        "ready": ready,
        "reason": reason,
        "decision_id": decision.id,
        "decision_label": decision.decision_label,
        "decision_score": float(decision.decision_score) if decision.decision_score is not None else None,
        "rl_action": decision.rl_action,
        "override_action": override_action,
        "override_active": override_active,
        "decision_ts": decision.timestamp,
        "override_created_ts": override.created_ts if override else None,
        "decision_stale": staleness["decision_stale"],
        "override_stale": staleness["override_stale"]
    }

def get_execution_ready_symbols(session: Session, symbols: List[str], interval: str, require_actionable: bool = True) -> Tuple[List[str], List[dict]]:
    """
    Evaluates execution readiness for a list of symbols.
    Returns (ready_symbols_list, all_details_list).
    """
    ready_symbols = []
    all_details = []
    
    for symbol in symbols:
        detail = check_symbol_execution_readiness(session, symbol, interval, require_actionable)
        all_details.append(detail)
        if detail["ready"]:
            ready_symbols.append(symbol)
            
    return ready_symbols, all_details
