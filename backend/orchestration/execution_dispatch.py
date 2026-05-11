import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..db import ExecutionDispatchRecord

logger = logging.getLogger(__name__)

def get_dispatch_record(session: Session, source_type: str, source_id: int) -> Optional[ExecutionDispatchRecord]:
    """
    Lookup a dispatch record by its unique source identity.
    """
    return session.query(ExecutionDispatchRecord).filter(
        ExecutionDispatchRecord.source_type == source_type,
        ExecutionDispatchRecord.source_id == source_id
    ).first()

def has_been_dispatched(session: Session, source_type: str, source_id: int) -> bool:
    """
    Convenience helper to check if a source has already been dispatched.
    """
    return get_dispatch_record(session, source_type, source_id) is not None

def register_dispatch_record(
    session: Session, 
    symbol: str, 
    interval: str, 
    source_type: str, 
    source_id: int, 
    dispatched_action: str, 
    status: str, 
    order_id: Optional[int] = None, 
    reason: Optional[str] = None
) -> dict:
    """
    Creates a new dispatch record.
    """
    # Check if already exists to avoid UniqueConstraintViolation
    existing = get_dispatch_record(session, source_type, source_id)
    if existing:
        return execution_dispatch_to_dict(existing)

    record = ExecutionDispatchRecord(
        symbol=symbol,
        interval=interval,
        source_type=source_type,
        source_id=source_id,
        dispatched_action=dispatched_action,
        status=status,
        order_id=order_id,
        reason=reason,
        created_ts=datetime.now(timezone.utc)
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return execution_dispatch_to_dict(record)

def list_dispatch_records(
    session: Session, 
    symbol: Optional[str] = None, 
    interval: Optional[str] = None, 
    limit: int = 100
) -> List[ExecutionDispatchRecord]:
    """
    List dispatch records, newest first.
    """
    query = session.query(ExecutionDispatchRecord)
    if symbol:
        query = query.filter(ExecutionDispatchRecord.symbol == symbol)
    if interval:
        query = query.filter(ExecutionDispatchRecord.interval == interval)
    
    return query.order_by(desc(ExecutionDispatchRecord.created_ts)).limit(limit).all()

def execution_dispatch_to_dict(record: ExecutionDispatchRecord) -> dict:
    """
    Serializes a dispatch record to a dictionary.
    """
    return {
        "id": record.id,
        "symbol": record.symbol,
        "interval": record.interval,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "dispatched_action": record.dispatched_action,
        "status": record.status,
        "order_id": record.order_id,
        "reason": record.reason,
        "created_ts": record.created_ts.isoformat() if record.created_ts else None
    }
