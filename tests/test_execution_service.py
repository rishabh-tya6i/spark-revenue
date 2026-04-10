import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from backend.db import Base, ExecutionAccount, DecisionRecord, OhlcBar
from backend.execution.service import ExecutionService

# Use a separate in-memory SQLite for this test
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_get_or_create_default_account(db_session):
    service = ExecutionService(db_session)
    account = service.get_or_create_default_account()
    assert account.name == "default"
    assert account.cash_balance > 0

    # Ensure it doesn't create a second one
    account2 = service.get_or_create_default_account()
    assert account2.id == account.id

def test_execute_decision_buy(db_session):
    service = ExecutionService(db_session)
    account = service.get_or_create_default_account()
    
    # Setup: OHLC Bar and Decision
    now = datetime.now(timezone.utc)
    bar = OhlcBar(symbol="BTCUSDT", interval="5m", exchange="BINANCE", start_ts=now, end_ts=now, open=100.0, high=105.0, low=95.0, close=102.0, volume=10.0)
    db_session.add(bar)
    
    decision = DecisionRecord(symbol="BTCUSDT", interval="5m", timestamp=now, decision_label="BULLISH", decision_score=0.8, rl_action="BUY")
    db_session.add(decision)
    db_session.commit()

    order = service.execute_decision(account.id, decision.id)
    assert order is not None
    assert order.side == "BUY"
    assert order.price == 102.0
    assert order.quantity == 1.0

    # Verification
    snapshot = service.get_account_snapshot(account.id)
    assert len(snapshot.positions) == 1
    assert snapshot.positions[0].symbol == "BTCUSDT"
    assert snapshot.positions[0].quantity == 1.0
