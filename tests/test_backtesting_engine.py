import pytest
import numpy as np
from datetime import datetime, timedelta
from backend.backtesting import engine

def test_rule_based_strategy():
    # Create fake bars with uptrend
    bars = []
    base_price = 100.0
    for i in range(30):
        bars.append({
            "timestamp": datetime.now() + timedelta(minutes=i*5),
            "close": base_price + i  # Uptrend
        })
    
    strat = engine.RuleBasedStrategy(window=10)
    # At index 20, MA should be lower than current close 120
    action = strat.decide(20, bars)
    assert action == "BUY"

def test_run_backtest_uptrend():
    bars = []
    base_price = 100.0
    for i in range(50):
        bars.append({
            "timestamp": datetime.now() + timedelta(minutes=i*5),
            "close": base_price + i
        })
    
    # Simple strategy: Always BUY
    class AlwaysBuy(engine.BaseStrategy):
        def decide(self, i, bars): return "BUY"
        
    history, final = engine.run_backtest(bars, AlwaysBuy(), 1000.0, 10.0)
    
    assert final > 1000.0
    assert len(history) == 50
    assert history[-1].position == 1

def test_metrics_calculation():
    # Equity curve: [100, 110, 105, 120]
    equity = np.array([100.0, 110.0, 105.0, 120.0])
    
    mdd = engine.compute_max_drawdown(equity)
    # peak 110, trough 105. drawdown = (105-110)/110 = -5/110 approx -0.045
    assert mdd < 0
    assert mdd == pytest.approx(-5.0/110.0)
    
    # Mock history for win rate
    class MockTrade:
        def __init__(self, pv): self.portfolio_value = pv
        
    history = [MockTrade(100), MockTrade(110), MockTrade(105), MockTrade(120)]
    wr = engine.compute_win_rate(history)
    # diffs: [10, -5, 15] -> 2 wins out of 3.
    assert wr == pytest.approx(2.0/3.0)
