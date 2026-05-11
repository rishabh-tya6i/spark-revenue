import logging
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..db import ExecutionOverrideRecord

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"BUY", "SELL", "HOLD", "SKIP"}

def set_execution_override(
    session: Session, 
    symbol: str, 
    interval: str, 
    override_action: str, 
    reason: Optional[str] = None
) -> dict:
    """
    Sets a manual execution override for a symbol and interval.
    Deactivates any existing active overrides for the same tuple.
    """
    action = override_action.upper()
    if action not in VALID_ACTIONS:
        raise ValueError(f"Invalid override action: {action}. Must be one of {VALID_ACTIONS}")

    # 1. Deactivate existing active overrides
    existing = session.query(ExecutionOverrideRecord).filter(
        ExecutionOverrideRecord.symbol == symbol,
        ExecutionOverrideRecord.interval == interval,
        ExecutionOverrideRecord.is_active == 1
    ).all()

    now = datetime.utcnow()
    for record in existing:
        record.is_active = 0
        record.cleared_ts = now
    
    # 2. Insert new active override
    new_record = ExecutionOverrideRecord(
        symbol=symbol,
        interval=interval,
        override_action=action,
        reason=reason,
        is_active=1,
        created_ts=now
    )
    session.add(new_record)
    session.commit()
    session.refresh(new_record)
    
    logger.info(f"Set execution override for {symbol} ({interval}): {action}")
    return execution_override_to_dict(new_record)

def clear_execution_override(session: Session, symbol: str, interval: str) -> Optional[dict]:
    """
    Clears the latest active execution override for a symbol and interval.
    """
    record = session.query(ExecutionOverrideRecord).filter(
        ExecutionOverrideRecord.symbol == symbol,
        ExecutionOverrideRecord.interval == interval,
        ExecutionOverrideRecord.is_active == 1
    ).order_by(desc(ExecutionOverrideRecord.created_ts)).first()
    
    if not record:
        return None
    
    record.is_active = 0
    record.cleared_ts = datetime.utcnow()
    session.commit()
    session.refresh(record)
    
    logger.info(f"Cleared execution override for {symbol} ({interval})")
    return execution_override_to_dict(record)

def get_active_execution_override(session: Session, symbol: str, interval: str) -> Optional[ExecutionOverrideRecord]:
    """
    Returns the latest active override for a symbol and interval.
    """
    return session.query(ExecutionOverrideRecord).filter(
        ExecutionOverrideRecord.symbol == symbol,
        ExecutionOverrideRecord.interval == interval,
        ExecutionOverrideRecord.is_active == 1
    ).order_by(desc(ExecutionOverrideRecord.created_ts)).first()

def list_active_execution_overrides(session: Session, interval: Optional[str] = None, limit: int = 100) -> List[ExecutionOverrideRecord]:
    """
    Lists all currently active execution overrides.
    """
    query = session.query(ExecutionOverrideRecord).filter(ExecutionOverrideRecord.is_active == 1)
    if interval:
        query = query.filter(ExecutionOverrideRecord.interval == interval)
    return query.order_by(desc(ExecutionOverrideRecord.created_ts)).limit(limit).all()

def execution_override_to_dict(record: ExecutionOverrideRecord) -> dict:
    """
    Converts an override record to a dictionary.
    """
    return {
        "id": record.id,
        "symbol": record.symbol,
        "interval": record.interval,
        "override_action": record.override_action,
        "reason": record.reason,
        "is_active": bool(record.is_active),
        "created_ts": record.created_ts.isoformat(),
        "cleared_ts": record.cleared_ts.isoformat() if record.cleared_ts else None
    }
