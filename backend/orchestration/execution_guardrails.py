import logging
from typing import List, Optional, Dict

from ..config import settings

logger = logging.getLogger(__name__)

def parse_allowed_actions(value: Optional[str]) -> List[str]:
    """
    Parses comma-separated allowed actions into a clean list.
    Default: ["BUY", "SELL"]
    """
    if not value or not value.strip():
        return ["BUY", "SELL"]
    
    parts = value.split(",")
    actions = [p.strip().upper() for p in parts if p.strip()]
    return actions if actions else ["BUY", "SELL"]

def evaluate_execution_guardrails(
    readiness_details: List[dict],
    require_actionable: bool = True,
    max_symbols: Optional[int] = None,
    allowed_actions: Optional[List[str]] = None
) -> dict:
    """
    Applies global guardrails to filtered execution-ready symbols.
    
    Returns:
    {
        "execution_enabled": bool,
        "allowed_actions": list[str],
        "max_symbols_per_run": int,
        "requested_ready_symbols": list[str],
        "allowed_symbols": list[str],
        "blocked_symbols": [{"symbol": str, "reason": str}]
    }
    """
    enabled = settings.EXECUTION_ENABLED
    max_syms = max_symbols if max_symbols is not None else settings.EXECUTION_MAX_SYMBOLS_PER_RUN
    allowed = allowed_actions if allowed_actions is not None else parse_allowed_actions(settings.EXECUTION_ALLOWED_ACTIONS)
    
    requested = [d["symbol"] for d in readiness_details if d.get("ready")]
    allowed_symbols = []
    blocked_symbols = []
    
    if not enabled:
        # Globally disabled
        for sym in requested:
            blocked_symbols.append({"symbol": sym, "reason": "execution_disabled"})
        
        return {
            "execution_enabled": False,
            "allowed_actions": allowed,
            "max_symbols_per_run": max_syms,
            "requested_ready_symbols": requested,
            "allowed_symbols": [],
            "blocked_symbols": blocked_symbols
        }

    # Filter and cap
    for detail in readiness_details:
        if not detail.get("ready"):
            continue
            
        sym = detail["symbol"]
        action = detail.get("rl_action", "HOLD")
        
        # 1. Action filter
        if action not in allowed:
            blocked_symbols.append({"symbol": sym, "reason": "disallowed_action"})
            continue
            
        # 2. Max symbols cap
        if len(allowed_symbols) >= max_syms:
            blocked_symbols.append({"symbol": sym, "reason": "max_symbols_cap"})
            continue
            
        allowed_symbols.append(sym)
        
    return {
        "execution_enabled": True,
        "allowed_actions": allowed,
        "max_symbols_per_run": max_syms,
        "requested_ready_symbols": requested,
        "allowed_symbols": allowed_symbols,
        "blocked_symbols": blocked_symbols
    }

def build_execution_guardrail_summary(guardrail_result: dict) -> dict:
    """
    Returns a compact summary for persistence and high-level reporting.
    """
    return {
        "execution_enabled": guardrail_result["execution_enabled"],
        "allowed_actions": guardrail_result["allowed_actions"],
        "max_symbols_per_run": guardrail_result["max_symbols_per_run"],
        "allowed_count": len(guardrail_result["allowed_symbols"]),
        "blocked_count": len(guardrail_result["blocked_symbols"])
    }
