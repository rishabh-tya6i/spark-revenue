from datetime import datetime, timezone
from typing import Optional, Dict
from ..config import settings

def is_record_stale(record_ts: Optional[datetime], max_age_minutes: int, now: Optional[datetime] = None) -> bool:
    """
    Returns True if the record_ts is None or older than max_age_minutes relative to now.
    """
    if record_ts is None:
        return True
    
    current_time = now or datetime.now(timezone.utc)
    
    # Ensure record_ts has timezone info if current_time does (standardizing to UTC)
    if record_ts.tzinfo is None:
        record_ts = record_ts.replace(tzinfo=timezone.utc)
    
    age_seconds = (current_time - record_ts).total_seconds()
    return age_seconds > (max_age_minutes * 60)

def evaluate_execution_source_staleness(
    decision_ts: Optional[datetime] = None, 
    override_ts: Optional[datetime] = None, 
    now: Optional[datetime] = None
) -> dict:
    """
    Evaluates freshness for both decision and override independently.
    """
    current_time = now or datetime.now(timezone.utc)
    
    dec_stale = is_record_stale(decision_ts, settings.EXECUTION_MAX_DECISION_AGE_MINUTES, now=current_time)
    ov_stale = is_record_stale(override_ts, settings.EXECUTION_MAX_OVERRIDE_AGE_MINUTES, now=current_time)
    
    return {
        "decision_stale": dec_stale,
        "override_stale": ov_stale,
        "decision_max_age_minutes": settings.EXECUTION_MAX_DECISION_AGE_MINUTES,
        "override_max_age_minutes": settings.EXECUTION_MAX_OVERRIDE_AGE_MINUTES
    }

def build_staleness_reason(has_override: bool, override_stale: bool, decision_stale: bool) -> Optional[str]:
    """
    Recommended logic to pick a primary staleness reason for reporting.
    """
    if has_override and override_stale:
        return "stale_override"
    elif not has_override and decision_stale:
        return "stale_decision"
    # Note: If fresh override exists, we don't care if decision is stale
    return None
