import argparse
import logging
from sqlalchemy.orm import Session
from ..db import SessionLocal
from .service import ExecutionService
from ..logging_config import setup_logging

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Spark Revenue Execution CLI")
    subparsers = parser.add_subparsers(dest="command", help="Execution commands")

    # execution-status
    subparsers.add_parser("execution-status", help="Show current paper trading account status")

    # execution-apply-decision
    apply_parser = subparsers.add_parser("execution-apply-decision", help="Execute trade for a decision")
    apply_parser.add_argument("--decision-id", type=int, required=True, help="ID of the decision to execute")

    args = parser.parse_args()

    db = SessionLocal()
    service = ExecutionService(db)
    account = service.get_or_create_default_account()

    try:
        if args.command == "execution-status":
            snapshot = service.get_account_snapshot(account.id)
            print(f"\n--- Execution Account Status ({snapshot.account.name}) ---")
            print(f"Base Currency: {snapshot.account.base_currency}")
            print(f"Equity:        {snapshot.equity:,.2f}")
            print(f"Cash Balance:  {snapshot.account.cash_balance:,.2f}")
            print(f"Realized PnL:  {snapshot.realized_pnl_total:,.2f}")
            print(f"Unrealized PnL: {snapshot.unrealized_pnl_total:,.2f}")
            
            if snapshot.positions:
                print("\n--- Positions ---")
                print(f"{'Symbol':<10} {'Qty':<10} {'Avg Price':<12} {'Mkt Price':<12} {'UPnL':<10}")
                for p in snapshot.positions:
                    print(f"{p.symbol:<10} {p.quantity:<10.4f} {p.avg_price:<12.2f} {p.market_price:<12.2f} {p.unrealized_pnl:<10.2f}")
            else:
                print("\nNo open positions.")
            print("")

        elif args.command == "execution-apply-decision":
            order = service.execute_decision(account.id, args.decision_id)
            if order:
                print(f"Order Executed: {order.side} {order.quantity} {order.symbol} @ {order.price}")
            else:
                print("No order executed for this decision.")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
