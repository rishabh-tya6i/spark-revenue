import logging
from typing import Optional, Dict
from .inference_runner import run_inference_universe_core
from .execution_runner import run_universe_execution_core

logger = logging.getLogger(__name__)

def summarize_cycle_results(inference_result: dict, execution_result: dict) -> dict:
    """
    Computes a combined operational summary from inference and execution sub-results.
    """
    # 1. Inference counts
    inf_summary = inference_result.get("summary", {})
    decision_sum = inf_summary.get("decision", {})
    
    selected_symbols = len(inference_result.get("symbols", []))
    inference_ready_symbols = len(inference_result.get("inference_ready_symbols", []))
    decision_success = decision_sum.get("success", 0)
    
    # 2. Execution counts
    exec_summary = execution_result.get("summary", {})
    
    execution_ready_symbols = len(execution_result.get("execution_ready_symbols", []))
    execution_success = exec_summary.get("success", 0)
    execution_skipped = exec_summary.get("skipped", 0)
    execution_failed = exec_summary.get("failed", 0)
    
    return {
        "selected_symbols": selected_symbols,
        "inference_ready_symbols": inference_ready_symbols,
        "decision_success": decision_success,
        "execution_ready_symbols": execution_ready_symbols,
        "execution_success": execution_success,
        "execution_skipped": execution_skipped,
        "execution_failed": execution_failed,
        "execution_duplicate_skips": exec_summary.get("duplicate_skips", 0)
    }

def run_operational_cycle_core(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    require_actionable: bool = True
) -> dict:
    """
    Orchestrates a full operational cycle: Inference -> Decision -> Paper Execution.
    Reuses existing universe orchestrators.
    """
    logger.info("Starting End-to-End Operational Cycle")
    
    # 1. Run Universe Inference
    inference_result = run_inference_universe_core(mode=mode, interval=interval)
    
    # 2. Handle Skip
    if inference_result.get("status") == "skipped":
        logger.warning(f"Inference skipped: {inference_result.get('reason')}. Skipping execution.")
        execution_result = {
            "status": "skipped",
            "reason": "inference_not_run_or_no_decisions",
            "symbols": [],
            "execution_ready_symbols": [],
            "readiness": [],
            "execution_results": [],
            "summary": {"total": 0, "success": 0, "skipped": 0, "failed": 0}
        }
        result = {
            "status": "skipped",
            "reason": inference_result.get("reason"),
            "mode": mode,
            "interval": interval,
            "inference": inference_result,
            "execution": execution_result,
            "summary": {
                "selected_symbols": 0,
                "inference_ready_symbols": 0,
                "decision_success": 0,
                "execution_ready_symbols": 0,
                "execution_success": 0,
                "execution_skipped": 0,
                "execution_failed": 0,
                "execution_duplicate_skips": 0
            }
        }
        
        # Persist run history
        from .run_history import register_orchestration_run
        from ..db import SessionLocal
        with SessionLocal() as session:
            run_record = register_orchestration_run(
                session=session,
                run_type="cycle",
                mode=mode,
                interval=interval,
                result=result
            )
            result["run_record_id"] = run_record["id"]
            
        return result
        
    # 3. Run Universe Execution (uses latest decisions)
    execution_result = run_universe_execution_core(
        mode=mode, 
        interval=interval, 
        require_actionable=require_actionable
    )
    
    # 4. Return combined report
    result = {
        "status": "completed",
        "mode": mode,
        "interval": interval,
        "inference": inference_result,
        "execution": execution_result,
        "summary": summarize_cycle_results(inference_result, execution_result)
    }
    
    # 5. Persist run history
    from .run_history import register_orchestration_run
    from ..db import SessionLocal
    with SessionLocal() as session:
        run_record = register_orchestration_run(
            session=session,
            run_type="cycle",
            mode=mode,
            interval=interval,
            result=result
        )
        result["run_record_id"] = run_record["id"]
        
    return result
