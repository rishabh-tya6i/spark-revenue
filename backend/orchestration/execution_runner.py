import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..db import DecisionRecord, SessionLocal
from ..execution.service import ExecutionService
from .universe import get_training_universe
from .utils import get_train_interval
from .execution_readiness import get_execution_ready_symbols
from .execution_guardrails import evaluate_execution_guardrails, build_execution_guardrail_summary
from .run_history import register_orchestration_run
from .execution_overrides import get_active_execution_override, execution_override_to_dict
from .execution_dispatch import has_been_dispatched, register_dispatch_record
from .execution_staleness import evaluate_execution_source_staleness, build_staleness_reason

logger = logging.getLogger(__name__)

def run_universe_execution_core(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    require_actionable: bool = True,
) -> dict:
    """
    Core logic to orchestrate paper execution across the current universe.
    1. Resolves selected universe.
    2. Filters for execution-ready symbols (based on latest stored decisions).
    3. Evaluates global execution guardrails.
    4. Applies manual operator overrides.
    5. Executes allowed decisions/overrides through the Paper Execution Service.
    """
    logger.info("Starting Universe Execution core logic")
    
    # 1. Resolve Universe
    with SessionLocal() as session:
        symbols = get_training_universe(session, mode=mode)
    exec_interval = interval or get_train_interval()
    
    # 2. Check readiness
    with SessionLocal() as session:
        ready_symbols, readiness_details = get_execution_ready_symbols(
            session, symbols, exec_interval, require_actionable=require_actionable
        )
    
    # 3. Evaluate Guardrails
    guardrail_result = evaluate_execution_guardrails(readiness_details)
    guardrail_summary = build_execution_guardrail_summary(guardrail_result)
    allowed_symbols = guardrail_result["allowed_symbols"]
    
    if not ready_symbols:
        logger.warning("No execution-ready symbols found. Skipping execution.")
        result = {
            "status": "skipped",
            "reason": "no_execution_ready_symbols",
            "symbols": symbols,
            "execution_ready_symbols": [],
            "guardrails": guardrail_result,
            "guardrail_summary": guardrail_summary,
            "readiness": readiness_details,
            "execution_results": [],
            "summary": summarize_execution_results([]),
            "dispatch_summary": {
                "new_dispatches": 0,
                "duplicate_skips": 0
            },
            "staleness_summary": {
                "stale_decision_symbols": [],
                "stale_override_symbols": []
            }
        }
    elif not allowed_symbols:
        logger.warning("All execution-ready symbols blocked by guardrails.")
        result = {
            "status": "skipped",
            "reason": "blocked_by_guardrails",
            "symbols": symbols,
            "execution_ready_symbols": ready_symbols,
            "guardrails": guardrail_result,
            "guardrail_summary": guardrail_summary,
            "readiness": readiness_details,
            "execution_results": [],
            "summary": summarize_execution_results([]),
            "dispatch_summary": {
                "new_dispatches": 0,
                "duplicate_skips": 0
            },
            "staleness_summary": {
                "stale_decision_symbols": [],
                "stale_override_symbols": []
            }
        }
    else:
        # 4. Execute decisions (with overrides)
        execution_results, overrides_context = execute_latest_decisions_for_symbols(allowed_symbols, exec_interval)
        
        # Extract dispatch summary from results
        dispatch_summary = {
            "new_dispatches": sum(1 for r in execution_results if (r.get("dispatch") or {}).get("registered") is True),
            "duplicate_skips": sum(1 for r in execution_results if (r.get("dispatch") or {}).get("duplicate") is True)
        }
        
        result = {
            "status": "completed",
            "symbols": symbols,
            "execution_ready_symbols": ready_symbols,
            "guardrails": guardrail_result,
            "guardrail_summary": guardrail_summary,
            "overrides": overrides_context,
            "readiness": readiness_details,
            "execution_results": execution_results,
            "summary": summarize_execution_results(execution_results),
            "dispatch_summary": dispatch_summary,
            "staleness_summary": {
                "stale_decision_symbols": [r["symbol"] for r in execution_results if r.get("error") == "stale_decision"],
                "stale_override_symbols": [r["symbol"] for r in execution_results if r.get("error") == "stale_override"]
            }
        }
    
    # 5. Persist run history
    with SessionLocal() as session:
        run_record = register_orchestration_run(
            session=session,
            run_type="execution",
            mode=mode,
            interval=exec_interval,
            result=result
        )
        result["run_record_id"] = run_record["id"]
        
    return result

def execute_latest_decisions_for_symbols(symbols: List[str], interval: str) -> tuple[List[dict], dict]:
    """
    Orchestrates paper execution across a list of symbols using existing ExecutionService.
    Applies manual overrides if present.
    """
    results = []
    overrides_applied = []
    active_override_symbols = []
    
    with SessionLocal() as session:
        service = ExecutionService(session)
        account = service.get_or_create_default_account()
        
        for symbol in symbols:
            # 1. Check for manual override
            override = get_active_execution_override(session, symbol, interval)
            override_dict = execution_override_to_dict(override) if override else None
            
            if override:
                active_override_symbols.append(symbol)
                overrides_applied.append({"symbol": symbol, "override_action": override.override_action})
                
                # --- STALENESS CHECK (Override) ---
                staleness = evaluate_execution_source_staleness(override_ts=override.created_ts)
                if staleness["override_stale"]:
                    results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "status": "skipped",
                        "decision_id": None,
                        "order_id": None,
                        "side": None,
                        "quantity": None,
                        "price": None,
                        "error": "stale_override",
                        "override": override_dict,
                        "staleness": staleness
                    })
                    continue

                # --- IDEMPOTENCY CHECK (Override) ---
                if has_been_dispatched(session, "override", override.id):
                    results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "status": "skipped",
                        "decision_id": None,
                        "order_id": None,
                        "side": None,
                        "quantity": None,
                        "price": None,
                        "error": "already_dispatched",
                        "override": override_dict,
                        "dispatch": {
                            "source_type": "override",
                            "source_id": override.id,
                            "duplicate": True
                        }
                    })
                    continue

                if override.override_action == "SKIP":
                    results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "status": "skipped",
                        "decision_id": None,
                        "order_id": None,
                        "side": None,
                        "quantity": None,
                        "price": None,
                        "error": "manual_override_skip",
                        "override": override_dict,
                        "dispatch": {
                            "source_type": "override",
                            "source_id": override.id,
                            "registered": True,
                            "duplicate": False
                        }
                    })
                    register_dispatch_record(session, symbol, interval, "override", override.id, "SKIP", "skipped", reason="manual_override_skip")
                    continue
                
                if override.override_action == "HOLD":
                    results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "status": "skipped",
                        "decision_id": None,
                        "order_id": None,
                        "side": None,
                        "quantity": None,
                        "price": None,
                        "error": "manual_override_hold",
                        "override": override_dict,
                        "dispatch": {
                            "source_type": "override",
                            "source_id": override.id,
                            "registered": True,
                            "duplicate": False
                        }
                    })
                    register_dispatch_record(session, symbol, interval, "override", override.id, "HOLD", "skipped", reason="manual_override_hold")
                    continue
                
                # Manual BUY/SELL
                try:
                    order = service.execute_manual_action(account.id, symbol, override.override_action, interval)
                    if order:
                        results.append({
                            "symbol": symbol,
                            "interval": interval,
                            "status": "success",
                            "decision_id": None,
                            "order_id": order.id,
                            "side": order.side,
                            "quantity": float(order.quantity),
                            "price": float(order.price),
                            "error": None,
                            "override": override_dict,
                            "dispatch": {
                                "source_type": "override",
                                "source_id": override.id,
                                "registered": True,
                                "duplicate": False
                            }
                        })
                        register_dispatch_record(session, symbol, interval, "override", override.id, override.override_action, "executed", order_id=order.id)
                    else:
                        results.append({
                            "symbol": symbol,
                            "interval": interval,
                            "status": "failed",
                            "decision_id": None,
                            "order_id": None,
                            "side": None,
                            "quantity": None,
                            "price": None,
                            "error": "manual_execution_failed",
                            "override": override_dict,
                            "dispatch": {
                                "source_type": "override",
                                "source_id": override.id,
                                "registered": True,
                                "duplicate": False
                            }
                        })
                        register_dispatch_record(session, symbol, interval, "override", override.id, override.override_action, "failed", reason="manual_execution_failed")
                except Exception as e:
                    logger.exception(f"Manual execution failed for {symbol}")
                    results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "status": "failed",
                        "decision_id": None,
                        "order_id": None,
                        "side": None,
                        "quantity": None,
                        "price": None,
                        "error": str(e),
                        "override": override_dict,
                        "dispatch": {
                            "source_type": "override",
                            "source_id": override.id,
                            "registered": True,
                            "duplicate": False
                        }
                    })
                    register_dispatch_record(session, symbol, interval, "override", override.id, override.override_action, "failed", reason=str(e))
                continue

            # 2. Normal path: Look up latest decision
            decision = session.query(DecisionRecord).filter(
                DecisionRecord.symbol == symbol,
                DecisionRecord.interval == interval
            ).order_by(desc(DecisionRecord.timestamp)).first()
            
            if not decision:
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "status": "skipped",
                    "decision_id": None,
                    "order_id": None,
                    "side": None,
                    "quantity": None,
                    "price": None,
                    "error": "missing_decision",
                })
                continue
            
            # --- STALENESS CHECK (Decision) ---
            staleness = evaluate_execution_source_staleness(decision_ts=decision.timestamp)
            if staleness["decision_stale"]:
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "status": "skipped",
                    "decision_id": decision.id,
                    "order_id": None,
                    "side": None,
                    "quantity": None,
                    "price": None,
                    "error": "stale_decision",
                    "staleness": staleness
                })
                continue

            # --- IDEMPOTENCY CHECK (Decision) ---
            if has_been_dispatched(session, "decision", decision.id):
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "status": "skipped",
                    "decision_id": decision.id,
                    "order_id": None,
                    "side": None,
                    "quantity": None,
                    "price": None,
                    "error": "already_dispatched",
                    "dispatch": {
                        "source_type": "decision",
                        "source_id": decision.id,
                        "duplicate": True
                    }
                })
                continue
                
            # 3. Call existing execution path
            try:
                order = service.execute_decision(account.id, decision.id)
                
                if order:
                    results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "status": "success",
                        "decision_id": decision.id,
                        "order_id": order.id,
                        "side": order.side,
                        "quantity": float(order.quantity),
                        "price": float(order.price),
                        "error": None,
                        "dispatch": {
                            "source_type": "decision",
                            "source_id": decision.id,
                            "registered": True,
                            "duplicate": False
                        }
                    })
                    register_dispatch_record(session, symbol, interval, "decision", decision.id, order.side, "executed", order_id=order.id)
                else:
                    results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "status": "skipped",
                        "decision_id": decision.id,
                        "order_id": None,
                        "side": None,
                        "quantity": None,
                        "price": None,
                        "error": "no trade generated",
                        "dispatch": {
                            "source_type": "decision",
                            "source_id": decision.id,
                            "registered": True,
                            "duplicate": False
                        }
                    })
                    register_dispatch_record(session, symbol, interval, "decision", decision.id, decision.rl_action or "HOLD", "skipped", reason="no trade generated")
            except Exception as e:
                logger.exception(f"Execution failed for {symbol}")
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "status": "failed",
                    "decision_id": decision.id,
                    "order_id": None,
                    "side": None,
                    "quantity": None,
                    "price": None,
                    "error": str(e),
                    "dispatch": {
                        "source_type": "decision",
                        "source_id": decision.id,
                        "registered": True,
                        "duplicate": False
                    }
                })
                register_dispatch_record(session, symbol, interval, "decision", decision.id, decision.rl_action or "UNKNOWN", "failed", reason=str(e))
            
            # Add staleness block for successful or non-stale-skipped results too (optional but for consistency)
            if results and results[-1]["symbol"] == symbol and "staleness" not in results[-1]:
                results[-1]["staleness"] = evaluate_execution_source_staleness(
                    decision_ts=decision.timestamp if not override else None,
                    override_ts=override.created_ts if override else None
                )
                
    overrides_context = {
        "active_symbols": active_override_symbols,
        "applied": overrides_applied
    }
    return results, overrides_context

def summarize_execution_results(results: List[dict]) -> dict:
    """
    Returns counts of successes, skips, and failures across all execution attempts.
    """
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    new_dispatches = sum(1 for r in results if (r.get("dispatch") or {}).get("registered") is True)
    duplicate_skips = sum(1 for r in results if (r.get("dispatch") or {}).get("duplicate") is True)
    
    return {
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "new_dispatches": new_dispatches,
        "duplicate_skips": duplicate_skips
    }
