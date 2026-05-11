import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, DecisionRecord
from backend.orchestration.execution_readiness import (
    check_symbol_execution_readiness,
    get_execution_ready_symbols
)

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_execution_readiness_logic(db_session):
    symbol = "NIFTY"
    interval = "5m"
    
    # 1. No decision
    res = check_symbol_execution_readiness(db_session, symbol, interval)
    assert res["ready"] is False
    assert res["reason"] == "missing_decision"
    
    # 2. Decision exists but RL action is HOLD (actionable=True)
    db_session.add(DecisionRecord(
        symbol=symbol, interval=interval, timestamp=datetime.utcnow(),
        decision_label="NEUTRAL", decision_score=0.5, rl_action="HOLD"
    ))
    db_session.commit()
    
    res = check_symbol_execution_readiness(db_session, symbol, interval, require_actionable=True)
    assert res["ready"] is False
    assert res["reason"] == "non_actionable_decision"
    
    # 3. Actionable=False, HOLD is ready
    res = check_symbol_execution_readiness(db_session, symbol, interval, require_actionable=False)
    assert res["ready"] is True
    assert res["rl_action"] == "HOLD"
    
    # 4. Actionable BUY
    db_session.add(DecisionRecord(
        symbol=symbol, interval=interval, timestamp=datetime.utcnow() + timedelta(minutes=5),
        decision_label="BULLISH", decision_score=0.8, rl_action="BUY"
    ))
    db_session.commit()
    
    res = check_symbol_execution_readiness(db_session, symbol, interval, require_actionable=True)
    assert res["ready"] is True
    assert res["rl_action"] == "BUY"
    assert res["decision_label"] == "BULLISH"

def test_get_execution_ready_symbols(db_session):
    # NIFTY ready
    db_session.add(DecisionRecord(
        symbol="NIFTY", interval="5m", timestamp=datetime.utcnow(),
        rl_action="BUY", decision_label="B", decision_score=1.0
    ))
    # SENSEX missing
    db_session.commit()
    
    ready, details = get_execution_ready_symbols(db_session, ["NIFTY", "SENSEX"], "5m")
    assert ready == ["NIFTY"]
    assert len(details) == 2
    assert details[0]["symbol"] == "NIFTY"
    assert details[0]["ready"] is True
    assert details[1]["symbol"] == "SENSEX"
    assert details[1]["ready"] is False
