import logging
from typing import List, Dict, Optional
from ..price_model.service import predict_price_core
from ..rl.service import get_rl_action_core
from ..decision_engine.service import DecisionEngineService
from .inference_readiness import get_inference_ready_symbols
from .universe import get_training_universe
from .utils import get_train_interval
from .execution_readiness import get_execution_ready_symbols
from ..db import SessionLocal

logger = logging.getLogger(__name__)

def run_inference_universe_core(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
) -> dict:
    """
    Core logic to orchestrate inference across the current universe.
    1. Resolves selected universe.
    2. Filters for inference-ready symbols.
    3. Runs price, RL, and decision inference for ready symbols.
    """
    logger.info("Starting Universe Inference core logic")
    
    # 1. Resolve Universe
    with SessionLocal() as session:
        symbols = get_training_universe(session, mode=mode)
    inf_interval = interval or get_train_interval()
    
    # 2. Check readiness
    with SessionLocal() as session:
        ready_symbols, readiness_details = get_inference_ready_symbols(session, symbols, inf_interval)
    
    if not ready_symbols:
        logger.warning("No inference-ready symbols found. Skipping inference.")
        result = {
            "status": "skipped",
            "reason": "no_inference_ready_symbols",
            "symbols": symbols,
            "inference_ready_symbols": [],
            "readiness": readiness_details,
            "price_results": [],
            "rl_results": [],
            "decision_results": [],
            "summary": summarize_inference_results([], [], [])
        }
        
        # Persist run history
        from .run_history import register_orchestration_run
        with SessionLocal() as session:
            run_record = register_orchestration_run(
                session=session,
                run_type="inference",
                mode=mode,
                interval=inf_interval,
                result=result
            )
            result["run_record_id"] = run_record["id"]
            
        return result

    # 3. Execute inference pipelines
    price_results = run_price_inference_for_symbols(ready_symbols, inf_interval)
    rl_results = run_rl_inference_for_symbols(ready_symbols, inf_interval)
    decision_results = compute_decisions_for_symbols(ready_symbols, inf_interval)
    
    result = {
        "status": "completed",
        "symbols": symbols,
        "inference_ready_symbols": ready_symbols,
        "readiness": readiness_details,
        "price_results": price_results,
        "rl_results": rl_results,
        "decision_results": decision_results,
        "summary": summarize_inference_results(price_results, rl_results, decision_results)
    }
    
    # 4. Persist run history
    from .run_history import register_orchestration_run
    with SessionLocal() as session:
        run_record = register_orchestration_run(
            session=session,
            run_type="inference",
            mode=mode,
            interval=inf_interval,
            result=result
        )
        result["run_record_id"] = run_record["id"]
        
    return result

def run_price_inference_for_symbols(symbols: List[str], interval: str) -> List[dict]:
    """
    Orchestrates price predictions for a set of symbols.
    """
    results = []
    for symbol in symbols:
        try:
            resp = predict_price_core(symbol, interval)
            results.append({
                "symbol": symbol,
                "interval": interval,
                "kind": "price_prediction",
                "status": "success",
                "label": resp.label,
                "probabilities": resp.probabilities,
                "model_version": resp.model_version,
                "error": None,
            })
        except Exception as e:
            logger.error(f"Price inference failed for {symbol}: {str(e)}")
            results.append({
                "symbol": symbol,
                "interval": interval,
                "kind": "price_prediction",
                "status": "failed",
                "label": None,
                "probabilities": None,
                "model_version": None,
                "error": str(e),
            })
    return results

def run_rl_inference_for_symbols(symbols: List[str], interval: str) -> List[dict]:
    """
    Orchestrates RL actions for a set of symbols.
    """
    results = []
    for symbol in symbols:
        try:
            resp = get_rl_action_core(symbol, interval)
            results.append({
                "symbol": symbol,
                "interval": interval,
                "kind": "rl_action",
                "status": "success",
                "action": resp.action,
                "action_index": resp.action_index,
                "confidence": resp.confidence,
                "policy_version": resp.policy_version,
                "error": None,
            })
        except Exception as e:
            logger.error(f"RL inference failed for {symbol}: {str(e)}")
            results.append({
                "symbol": symbol,
                "interval": interval,
                "kind": "rl_action",
                "status": "failed",
                "action": None,
                "action_index": None,
                "confidence": None,
                "policy_version": None,
                "error": str(e),
            })
    return results

def compute_decisions_for_symbols(symbols: List[str], interval: str) -> List[dict]:
    """
    Orchestrates fused decision computation for a set of symbols.
    """
    results = []
    service = DecisionEngineService()
    for symbol in symbols:
        try:
            resp = service.compute_decision_core(symbol, interval)
            results.append({
                "symbol": symbol,
                "interval": interval,
                "kind": "decision",
                "status": "success",
                "decision_id": resp.decision.id,
                "decision_label": resp.decision.decision_label,
                "decision_score": float(resp.decision.decision_score),
                "alert_created": resp.alert is not None,
                "error": None,
            })
        except Exception as e:
            logger.error(f"Decision computation failed for {symbol}: {str(e)}")
            results.append({
                "symbol": symbol,
                "interval": interval,
                "kind": "decision",
                "status": "failed",
                "decision_id": None,
                "decision_label": None,
                "decision_score": None,
                "alert_created": False,
                "error": str(e),
            })
    return results

def summarize_inference_results(price_results, rl_results, decision_results) -> dict:
    """
    Returns counts of successes and failures across all inference stages.
    """
    def _sum(items):
        total = len(items)
        success = sum(1 for i in items if i["status"] == "success")
        return {"total": total, "success": success, "failed": total - success}

    return {
        "price_prediction": _sum(price_results),
        "rl_action": _sum(rl_results),
        "decision": _sum(decision_results),
    }
