import pytest
from backend.execution.engine import ExecutionEngine, compute_unrealized_pnl

def test_engine_buy_new():
    engine = ExecutionEngine()
    # Buying 1 unit at 100 with zero existing
    new_qty, new_avg, new_cash, pnl = engine.apply_order("BUY", 1.0, 100.0, 0.0, 0.0, 1000.0)
    assert new_qty == 1.0
    assert new_avg == 100.0
    assert new_cash == 900.0
    assert pnl == 0.0

def test_engine_buy_existing():
    engine = ExecutionEngine()
    # Already have 1 unit at 100, buying 1 more at 110
    new_qty, new_avg, new_cash, pnl = engine.apply_order("BUY", 1.0, 110.0, 1.0, 100.0, 900.0)
    assert new_qty == 2.0
    assert new_avg == 105.0
    assert new_cash == 790.0
    assert pnl == 0.0

def test_engine_sell_closing():
    engine = ExecutionEngine()
    # Have 1 unit at 100, selling 1 unit at 120 (gain of 20)
    new_qty, new_avg, new_cash, pnl = engine.apply_order("SELL", 1.0, 120.0, 1.0, 100.0, 900.0)
    assert new_qty == 0.0
    assert pnl == 20.0
    assert new_cash == 1020.0

def test_compute_unrealized_pnl():
    # Long 1 unit at 100, market is 110 -> +10
    assert compute_unrealized_pnl(1.0, 100.0, 110.0) == 10.0
    # Short 1 unit (qty -1) at 100, market is 110 -> -10
    assert compute_unrealized_pnl(-1.0, 100.0, 110.0) == -10.0
