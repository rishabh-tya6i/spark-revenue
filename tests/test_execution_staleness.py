import pytest
from datetime import datetime, timedelta, timezone
from backend.orchestration.execution_staleness import (
    is_record_stale, 
    evaluate_execution_source_staleness,
    build_staleness_reason
)
from backend.config import settings

def test_is_record_stale():
    now = datetime.now(timezone.utc)
    
    # Not stale
    ts_recent = now - timedelta(minutes=10)
    assert is_record_stale(ts_recent, 30, now=now) is False
    
    # Stale
    ts_old = now - timedelta(minutes=31)
    assert is_record_stale(ts_old, 30, now=now) is True
    
    # None is stale
    assert is_record_stale(None, 30, now=now) is True

def test_evaluate_execution_source_staleness():
    now = datetime.now(timezone.utc)
    
    # Setup thresholds from settings (mocked or actual)
    # Default: 30 for decision, 60 for override
    
    # Fresh both
    res = evaluate_execution_source_staleness(
        decision_ts=now - timedelta(minutes=5),
        override_ts=now - timedelta(minutes=5),
        now=now
    )
    assert res["decision_stale"] is False
    assert res["override_stale"] is False
    
    # Stale decision, fresh override
    res = evaluate_execution_source_staleness(
        decision_ts=now - timedelta(minutes=40),
        override_ts=now - timedelta(minutes=5),
        now=now
    )
    assert res["decision_stale"] is True
    assert res["override_stale"] is False
    
    # Fresh decision, stale override
    res = evaluate_execution_source_staleness(
        decision_ts=now - timedelta(minutes=5),
        override_ts=now - timedelta(minutes=70),
        now=now
    )
    assert res["decision_stale"] is False
    assert res["override_stale"] is True

def test_build_staleness_reason():
    # Fresh override -> no reason (we ignore stale decision if override is fresh)
    assert build_staleness_reason(True, False, True) is None
    
    # Stale override -> stale_override
    assert build_staleness_reason(True, True, False) == "stale_override"
    
    # No override, stale decision -> stale_decision
    assert build_staleness_reason(False, False, True) == "stale_decision"
    
    # No override, fresh decision -> None
    assert build_staleness_reason(False, False, False) is None
