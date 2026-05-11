import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..db import TrainedModelRecord

logger = logging.getLogger(__name__)

def register_trained_model(
    session: Session, 
    symbol: str, 
    interval: str, 
    model_type: str, 
    artifact_path: Optional[str], 
    status: str, 
    trainer_run_id: Optional[str] = None, 
    notes: Optional[str] = None
) -> TrainedModelRecord:
    """
    Registers a training run result in the database.
    If status is 'success', it deactivates previous models for the same tuple (symbol, interval, model_type).
    """
    # Use UTC for consistency
    now = datetime.now(timezone.utc)
    
    # 1. Handle activation logic
    is_active = 0
    if status == "success":
        # Deactivate old models for the same symbol/interval/model_type
        session.query(TrainedModelRecord).filter(
            TrainedModelRecord.symbol == symbol,
            TrainedModelRecord.interval == interval,
            TrainedModelRecord.model_type == model_type,
            TrainedModelRecord.is_active == 1
        ).update({"is_active": 0})
        
        is_active = 1
        logger.info(f"Registering new active {model_type} for {symbol} ({interval})")
    else:
        logger.warning(f"Registering failed {model_type} run for {symbol} ({interval})")

    # 2. Create the new record
    record = TrainedModelRecord(
        symbol=symbol,
        interval=interval,
        model_type=model_type,
        artifact_path=artifact_path or "",
        status=status,
        is_active=is_active,
        trainer_run_id=trainer_run_id,
        notes=notes,
        created_ts=now
    )
    
    session.add(record)
    session.commit()
    session.refresh(record)
    
    return record

def get_latest_active_model(session: Session, symbol: str, interval: str, model_type: str) -> Optional[TrainedModelRecord]:
    """
    Returns the latest active model record for the given tuple.
    """
    return session.query(TrainedModelRecord).filter(
        TrainedModelRecord.symbol == symbol,
        TrainedModelRecord.interval == interval,
        TrainedModelRecord.model_type == model_type,
        TrainedModelRecord.is_active == 1
    ).order_by(desc(TrainedModelRecord.created_ts)).first()

def list_models(
    session: Session, 
    symbol: Optional[str] = None, 
    interval: Optional[str] = None, 
    model_type: Optional[str] = None, 
    active_only: bool = False, 
    limit: int = 50
) -> List[TrainedModelRecord]:
    """
    Lists registered models based on filters.
    """
    query = session.query(TrainedModelRecord)
    
    if symbol:
        query = query.filter(TrainedModelRecord.symbol == symbol)
    if interval:
        query = query.filter(TrainedModelRecord.interval == interval)
    if model_type:
        query = query.filter(TrainedModelRecord.model_type == model_type)
    if active_only:
        query = query.filter(TrainedModelRecord.is_active == 1)
        
    return query.order_by(desc(TrainedModelRecord.created_ts)).limit(limit).all()

def model_record_to_dict(record: TrainedModelRecord) -> dict:
    """
    Converts ORM record to a JSON-serializable dictionary.
    """
    return {
        "id": record.id,
        "symbol": record.symbol,
        "interval": record.interval,
        "model_type": record.model_type,
        "artifact_path": record.artifact_path,
        "status": record.status,
        "is_active": bool(record.is_active),
        "trainer_run_id": record.trainer_run_id,
        "notes": record.notes,
        "created_ts": record.created_ts.isoformat() if record.created_ts else None
    }
