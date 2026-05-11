import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..db import ExecutionAccount, ExecutionPosition, ExecutionOrder, ExecutionPnL, DecisionRecord, OhlcBar
from ..config import settings
from .engine import ExecutionEngine, compute_unrealized_pnl
from .schemas import AccountSnapshotOut, AccountOut, PositionOut, OrderOut

logger = logging.getLogger(__name__)

class ExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = ExecutionEngine(
            max_position_per_symbol=settings.EXECUTION_MAX_POSITION_PER_SYMBOL,
            max_notional_per_symbol=settings.EXECUTION_MAX_NOTIONAL_PER_SYMBOL
        )

    def get_or_create_default_account(self) -> ExecutionAccount:
        account = self.db.query(ExecutionAccount).filter(ExecutionAccount.name == "default").first()
        if not account:
            now = datetime.now(timezone.utc)
            initial_balance = settings.BACKTEST_INITIAL_CAPITAL # Reuse backtest config for default
            account = ExecutionAccount(
                name="default",
                base_currency=settings.EXECUTION_BASE_CURRENCY,
                initial_balance=initial_balance,
                cash_balance=initial_balance,
                created_ts=now,
                updated_ts=now
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            logger.info(f"Created default execution account with balance {initial_balance}")
        return account

    def get_latest_market_price(self, symbol: str, interval: str = "5m") -> float:
        bar = self.db.query(OhlcBar).filter(
            OhlcBar.symbol == symbol,
            OhlcBar.interval == interval,
        ).order_by(desc(OhlcBar.end_ts)).first()
        if not bar:
            logger.warning(f"No price data found for {symbol}, using 0.0")
            return 0.0
        return bar.close

    def execute_decision(self, account_id: int, decision_id: int) -> Optional[ExecutionOrder]:
        decision = self.db.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
        if not decision:
            logger.error(f"Decision {decision_id} not found")
            return None

        # Simple mapping: RL action determines the trade for v1
        if decision.rl_action == "BUY":
            side = "BUY"
            qty = 1.0 # Default 1 unit for v1
        elif decision.rl_action == "SELL":
            side = "SELL"
            qty = 1.0
        else:
            logger.info(f"Decision {decision_id} resulted in NO_TRADE (action: {decision.rl_action})")
            return None

        price = self.get_latest_market_price(decision.symbol, decision.interval or settings.BACKTEST_DEFAULT_INTERVAL)
        if price <= 0:
            logger.error(f"Cannot execute trade for {decision.symbol}: invalid price {price}")
            return None

        account = self.db.query(ExecutionAccount).filter(ExecutionAccount.id == account_id).first()
        position = self.db.query(ExecutionPosition).filter(
            ExecutionPosition.account_id == account_id,
            ExecutionPosition.symbol == decision.symbol
        ).first()

        current_qty = position.quantity if position else 0.0
        current_avg_price = position.avg_price if position else 0.0

        new_qty, new_avg_price, new_cash, realized_pnl = self.engine.apply_order(
            side=side,
            quantity=qty,
            price=price,
            current_qty=current_qty,
            current_avg_price=current_avg_price,
            cash_balance=account.cash_balance
        )

        now = datetime.now(timezone.utc)
        
        # Create Order
        order = ExecutionOrder(
            account_id=account_id,
            symbol=decision.symbol,
            side=side,
            quantity=qty,
            price=price,
            decision_id=decision_id,
            created_ts=now
        )
        self.db.add(order)

        # Update Position
        if not position:
            position = ExecutionPosition(
                account_id=account_id,
                symbol=decision.symbol,
                quantity=new_qty,
                avg_price=new_avg_price,
                updated_ts=now
            )
            self.db.add(position)
        else:
            position.quantity = new_qty
            position.avg_price = new_avg_price
            position.updated_ts = now

        # Update Account
        account.cash_balance = new_cash
        account.updated_ts = now

        self.db.commit()
        self.db.refresh(order)
        logger.info(f"Executed {side} {qty} {decision.symbol} @ {price} for account {account_id}")
        
        return order

    def execute_manual_action(self, account_id: int, symbol: str, side: str, interval: str = "5m", decision_id: Optional[int] = None) -> Optional[ExecutionOrder]:
        """
        Executes a manual override action (BUY/SELL) for a symbol.
        """
        side = side.upper()
        if side not in ["BUY", "SELL"]:
            logger.error(f"Invalid manual side: {side}")
            return None

        qty = 1.0 # Default 1 unit for v1
        price = self.get_latest_market_price(symbol, interval)
        if price <= 0:
            logger.error(f"Cannot execute manual trade for {symbol}: invalid price {price}")
            return None

        account = self.db.query(ExecutionAccount).filter(ExecutionAccount.id == account_id).first()
        position = self.db.query(ExecutionPosition).filter(
            ExecutionPosition.account_id == account_id,
            ExecutionPosition.symbol == symbol
        ).first()

        current_qty = position.quantity if position else 0.0
        current_avg_price = position.avg_price if position else 0.0

        new_qty, new_avg_price, new_cash, realized_pnl = self.engine.apply_order(
            side=side,
            quantity=qty,
            price=price,
            current_qty=current_qty,
            current_avg_price=current_avg_price,
            cash_balance=account.cash_balance
        )

        now = datetime.now(timezone.utc)
        
        # Create Order
        order = ExecutionOrder(
            account_id=account_id,
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price,
            decision_id=decision_id,
            created_ts=now
        )
        self.db.add(order)

        # Update Position
        if not position:
            position = ExecutionPosition(
                account_id=account_id,
                symbol=symbol,
                quantity=new_qty,
                avg_price=new_avg_price,
                updated_ts=now
            )
            self.db.add(position)
        else:
            position.quantity = new_qty
            position.avg_price = new_avg_price
            position.updated_ts = now

        # Update Account
        account.cash_balance = new_cash
        account.updated_ts = now

        self.db.commit()
        self.db.refresh(order)
        logger.info(f"Executed MANUAL {side} {qty} {symbol} @ {price} for account {account_id}")
        
        return order

    def get_account_snapshot(self, account_id: int) -> AccountSnapshotOut:
        account = self.db.query(ExecutionAccount).filter(ExecutionAccount.id == account_id).first()
        positions_orm = self.db.query(ExecutionPosition).filter(ExecutionPosition.account_id == account_id).all()
        
        positions_out = []
        unrealized_pnl_total = 0.0
        market_value_total = 0.0

        for p in positions_orm:
            if p.quantity == 0:
                continue
            mkt_price = self.get_latest_market_price(p.symbol, settings.BACKTEST_DEFAULT_INTERVAL)
            upnl = compute_unrealized_pnl(p.quantity, p.avg_price, mkt_price)
            unrealized_pnl_total += upnl
            market_value_total += (p.quantity * mkt_price)
            
            positions_out.append(PositionOut(
                symbol=p.symbol,
                quantity=p.quantity,
                avg_price=p.avg_price,
                market_price=mkt_price,
                unrealized_pnl=upnl
            ))

        equity = account.cash_balance + market_value_total
        
        # For realized PnL total, we'd need to aggregate from history or keep a running total.
        # For v1, let's just calculate it as equity - initial_balance - current_unrealized.
        realized_pnl_total = (equity - account.initial_balance) - unrealized_pnl_total

        return AccountSnapshotOut(
            account=AccountOut.model_validate(account),
            positions=positions_out,
            equity=equity,
            unrealized_pnl_total=unrealized_pnl_total,
            realized_pnl_total=realized_pnl_total
        )
