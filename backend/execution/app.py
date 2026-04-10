from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from ..db import get_db, ExecutionOrder
from .service import ExecutionService
from .schemas import AccountSnapshotOut, OrderOut

router = APIRouter()

@router.post("/execution/decision/{decision_id}", response_model=OrderOut)
def execute_trade(decision_id: int, db: Session = Depends(get_db)):
    service = ExecutionService(db)
    account = service.get_or_create_default_account()
    order = service.execute_decision(account.id, decision_id)
    if not order:
        raise HTTPException(status_code=204, detail="No trade executed for this decision")
    return OrderOut.from_attributes(order)

@router.get("/execution/account", response_model=AccountSnapshotOut)
def get_account_status(db: Session = Depends(get_db)):
    service = ExecutionService(db)
    account = service.get_or_create_default_account()
    return service.get_account_snapshot(account.id)

@router.get("/execution/orders", response_model=List[OrderOut])
def list_orders(
    symbol: str = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    query = db.query(ExecutionOrder)
    if symbol:
        query = query.filter(ExecutionOrder.symbol == symbol)
    orders = query.order_by(ExecutionOrder.created_ts.desc()).limit(limit).all()
    return [OrderOut.from_attributes(o) for o in orders]
