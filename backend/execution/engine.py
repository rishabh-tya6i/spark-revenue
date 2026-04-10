import logging

logger = logging.getLogger(__name__)

class ExecutionEngine:
    def __init__(self, max_position_per_symbol: float = 1.0, max_notional_per_symbol: float = 20000.0):
        self.max_position_per_symbol = max_position_per_symbol
        self.max_notional_per_symbol = max_notional_per_symbol

    def apply_order(
        self,
        side: str,
        quantity: float,
        price: float,
        current_qty: float,
        current_avg_price: float,
        cash_balance: float
    ) -> tuple[float, float, float, float]:
        """
        Calculates the new position state after an order.
        Returns: (new_qty, new_avg_price, new_cash_balance, realized_pnl)
        """
        notional = quantity * price
        realized_pnl = 0.0

        if side == "BUY":
            # Risk check (simplified for v1)
            if (current_qty + quantity) * price > self.max_notional_per_symbol:
                logger.warning(f"Order rejected: Max notional exceeded for symbol")
                # For v1, we might still apply it or raise an error. 
                # Let's just log and proceed for paper trading unless it's extreme.
            
            new_qty = current_qty + quantity
            if new_qty > 0:
                if current_qty >= 0:
                    # Adding to long
                    new_avg_price = (current_qty * current_avg_price + quantity * price) / new_qty
                else:
                    # Closing short
                    closed_qty = min(abs(current_qty), quantity)
                    realized_pnl = (current_avg_price - price) * closed_qty
                    remaining_qty = quantity - closed_qty
                    if remaining_qty > 0:
                        new_avg_price = price
                    else:
                        new_avg_price = current_avg_price if new_qty != 0 else 0.0
            else:
                # Still short but less
                realized_pnl = (current_avg_price - price) * quantity
                new_avg_price = current_avg_price
            
            new_cash_balance = cash_balance - notional

        elif side == "SELL":
            new_qty = current_qty - quantity
            if new_qty < 0:
                if current_qty <= 0:
                    # Adding to short
                    new_avg_price = (abs(current_qty) * current_avg_price + quantity * price) / abs(new_qty)
                else:
                    # Closing long
                    closed_qty = min(current_qty, quantity)
                    realized_pnl = (price - current_avg_price) * closed_qty
                    remaining_qty = quantity - closed_qty
                    if remaining_qty > 0:
                        new_avg_price = price
                    else:
                        new_avg_price = current_avg_price if new_qty != 0 else 0.0
            else:
                # Still long but less
                realized_pnl = (price - current_avg_price) * quantity
                new_avg_price = current_avg_price
            
            new_cash_balance = cash_balance + notional

        else:
            raise ValueError(f"Invalid side: {side}")

        return new_qty, new_avg_price, new_cash_balance, realized_pnl

def compute_unrealized_pnl(quantity: float, avg_price: float, market_price: float) -> float:
    if quantity == 0:
        return 0.0
    return (market_price - avg_price) * quantity
