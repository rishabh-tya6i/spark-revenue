import numpy as np
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence, Dict, Tuple

logger = logging.getLogger(__name__)

@dataclass
class TradeResult:
    timestamp: datetime
    position: int      # -1, 0, 1
    action: str        # BUY/SELL/HOLD
    price: float
    portfolio_value: float

class BaseStrategy(ABC):
    @abstractmethod
    def decide(self, bar_index: int, bars: List[Dict]) -> str:
        """Return 'BUY', 'SELL', or 'HOLD'"""

class RuleBasedStrategy(BaseStrategy):
    def __init__(self, window: int = 20):
        self.window = window

    def decide(self, bar_index: int, bars: List[Dict]) -> str:
        if bar_index < self.window:
            return "HOLD"
        
        closes = [b["close"] for b in bars[max(0, bar_index - self.window):bar_index + 1]]
        ma = sum(closes) / len(closes)
        current_close = bars[bar_index]["close"]
        
        if current_close > ma:
            return "BUY"
        elif current_close < ma:
            return "SELL"
        else:
            return "HOLD"

def run_backtest(
    bars: List[Dict],
    strategy: BaseStrategy,
    initial_capital: float,
    transaction_cost_bps: float,
) -> Tuple[List[TradeResult], float]:
    cash = initial_capital
    position = 0  # number of shares/contracts
    history = []
    
    cost_factor = transaction_cost_bps / 10000.0
    
    for i, bar in enumerate(bars):
        action = strategy.decide(i, bars)
        price = bar["close"]
        
        # Simple Logic: Convert action into position target
        # BUY -> position 1, SELL -> position -1, HOLD -> no change
        target_pos = position
        if action == "BUY":
            target_pos = 1
        elif action == "SELL":
            target_pos = -1
            
        if target_pos != position:
            # Execute at bar close
            # Notional traded = abs(new_pos - old_pos) * price
            # But since it's v1 and we use unit positions (1 or -1 share) for simplicity:
            # Actual implementation would use target_pos * cash etc.
            # Here we just simulate 1 unit to keep it simple as requested.
            trade_notional = abs(target_pos - position) * price
            fee = trade_notional * cost_factor
            cash = cash - fee
            position = target_pos
            
        portfolio_value = cash + position * price
        history.append(TradeResult(
            timestamp=bar["timestamp"],
            position=position,
            action=action,
            price=price,
            portfolio_value=portfolio_value
        ))
        
    final_capital = history[-1].portfolio_value if history else initial_capital
    return history, final_capital

def compute_equity_curve(history: List[TradeResult]) -> np.ndarray:
    return np.array([h.portfolio_value for h in history])

def compute_win_rate(history: List[TradeResult]) -> float:
    if len(history) < 2:
        return 0.0
    
    # Win rate of daily/step-wise returns for simplicity
    pvals = [h.portfolio_value for h in history]
    diffs = np.diff(pvals)
    wins = np.sum(diffs > 0)
    total = np.sum(diffs != 0)
    return float(wins / total) if total > 0 else 0.0

def compute_max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak
    return float(np.min(drawdowns))

def compute_sharpe(equity: np.ndarray, risk_free_rate: float = 0.0) -> float:
    if len(equity) < 2:
        return 0.0
    returns = np.diff(equity) / equity[:-1]
    if np.std(returns) == 0:
        return 0.0
    # Annualized Sharpe (assuming 5m intervals, approx 252*78 steps per year)
    steps_per_year = 252 * 78
    sharpe = (np.mean(returns) - risk_free_rate) / np.std(returns)
    return float(sharpe * np.sqrt(steps_per_year))
