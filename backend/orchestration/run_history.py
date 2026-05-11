import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..db import OrchestrationRunRecord

logger = logging.getLogger(__name__)

def build_run_record_summary(run_type: str, result: dict) -> dict:
    """
    Normalizes orchestration result payloads into a compact summary for persistence.
    """
    status = result.get("status", "failed")
    
    if run_type == "train":
        # derive from Module 6 / 7 result
        # result shape usually: {"status": "completed", "trainable_symbols": [...], "training_summary": {...}}
        train_sum = result.get("training_summary", {})
        return {
            "trainable_symbols": result.get("trainable_symbols", []),
            "price_model": train_sum.get("price_model", {}),
            "rl_agent": train_sum.get("rl_agent", {}),
        }
        
    elif run_type == "inference":
        # derive from Module 8
        # result shape: {"status": "completed", "symbols": [...], "inference_ready_symbols": [...], "summary": {...}}
        inf_sum = result.get("summary", {})
        return {
            "symbols": result.get("symbols", []),
            "inference_ready_symbols": result.get("inference_ready_symbols", []),
            "price_prediction": inf_sum.get("price_prediction", {}),
            "rl_action": inf_sum.get("rl_action", {}),
            "decision": inf_sum.get("decision", {}),
        }
        
    elif run_type == "execution":
        # derive from Module 9 / 14
        overrides = result.get("overrides", {})
        override_summary = {
            "active_symbols": overrides.get("active_symbols", []),
            "applied_count": len(overrides.get("applied", []))
        } if overrides else None

        return {
            "symbols": result.get("symbols", []),
            "execution_ready_symbols": result.get("execution_ready_symbols", []),
            "summary": result.get("summary", {}),
            "guardrail_summary": result.get("guardrail_summary"),
            "override_summary": override_summary,
            "dispatch_summary": result.get("dispatch_summary"),
            "staleness_summary": result.get("staleness_summary"),
        }
        
    elif run_type == "cycle":
        # derive from Module 10 / 14
        exec_res = result.get("execution", {})
        overrides = exec_res.get("overrides", {})
        override_summary = {
            "active_symbols": overrides.get("active_symbols", []),
            "applied_count": len(overrides.get("applied", []))
        } if overrides else None

        return {
            "summary": result.get("summary", {}),
            "guardrail_summary": exec_res.get("guardrail_summary"),
            "override_summary": override_summary,
            "dispatch_summary": exec_res.get("dispatch_summary"),
            "staleness_summary": exec_res.get("staleness_summary"),
        }
        
    return {}

def register_orchestration_run(
    session: Session, 
    run_type: str, 
    mode: Optional[str], 
    interval: Optional[str], 
    result: dict
) -> dict:
    """
    Persists an OrchestrationRunRecord based on the provided result.
    """
    compact_summary = build_run_record_summary(run_type, result)
    status = result.get("status", "failed")
    reason = result.get("reason")
    
    # Initialize counts
    sel_count = 0
    ready_count = 0
    succ_count = 0
    skip_count = 0
    fail_count = 0
    
    if run_type == "train":
        trainable = result.get("trainable_symbols", [])
        sel_count = len(trainable)
        ready_count = sel_count
        train_sum = result.get("training_summary", {})
        pm = train_sum.get("price_model", {})
        rl = train_sum.get("rl_agent", {})
        succ_count = pm.get("success", 0) + rl.get("success", 0)
        fail_count = pm.get("failed", 0) + rl.get("failed", 0)
        
    elif run_type == "inference":
        sel_count = len(result.get("symbols", []))
        ready_count = len(result.get("inference_ready_symbols", []))
        inf_sum = result.get("summary", {})
        dec = inf_sum.get("decision", {})
        succ_count = dec.get("success", 0)
        fail_count = dec.get("failed", 0)
        
    elif run_type == "execution":
        sel_count = len(result.get("symbols", []))
        ready_count = len(result.get("execution_ready_symbols", []))
        exec_sum = result.get("summary", {})
        succ_count = exec_sum.get("success", 0)
        skip_count = exec_sum.get("skipped", 0)
        fail_count = exec_sum.get("failed", 0)
        
    elif run_type == "cycle":
        cycle_sum = result.get("summary", {})
        sel_count = cycle_sum.get("selected_symbols", 0)
        ready_count = cycle_sum.get("inference_ready_symbols", 0)
        succ_count = cycle_sum.get("execution_success", 0)
        skip_count = cycle_sum.get("execution_skipped", 0)
        fail_count = cycle_sum.get("execution_failed", 0)

    record = OrchestrationRunRecord(
        run_type=run_type,
        mode=mode,
        interval=interval,
        status=status,
        reason=reason,
        selected_symbols_count=sel_count,
        ready_symbols_count=ready_count,
        success_count=succ_count,
        skipped_count=skip_count,
        failed_count=fail_count,
        summary_json=json.dumps(compact_summary),
        created_ts=datetime.utcnow()
    )
    
    session.add(record)
    session.commit()
    session.refresh(record)
    
    return orchestration_run_to_dict(record)

def list_orchestration_runs(
    session: Session, 
    run_type: Optional[str] = None, 
    limit: int = 50
) -> List[OrchestrationRunRecord]:
    """
    Lists recent orchestration runs, newest first.
    """
    query = session.query(OrchestrationRunRecord)
    if run_type:
        query = query.filter(OrchestrationRunRecord.run_type == run_type)
    return query.order_by(desc(OrchestrationRunRecord.created_ts)).limit(limit).all()

def get_orchestration_run(session: Session, run_id: int) -> Optional[OrchestrationRunRecord]:
    """
    Fetches a single orchestration run record by ID.
    """
    return session.query(OrchestrationRunRecord).filter(OrchestrationRunRecord.id == run_id).first()

def orchestration_run_to_dict(record: OrchestrationRunRecord) -> dict:
    """
    Converts a record into a dict for API/CLI consumption.
    """
    return {
        "id": record.id,
        "run_type": record.run_type,
        "mode": record.mode,
        "interval": record.interval,
        "status": record.status,
        "reason": record.reason,
        "selected_symbols_count": record.selected_symbols_count,
        "ready_symbols_count": record.ready_symbols_count,
        "success_count": record.success_count,
        "skipped_count": record.skipped_count,
        "failed_count": record.failed_count,
        "summary": json.loads(record.summary_json),
        "created_ts": record.created_ts.isoformat()
    }
