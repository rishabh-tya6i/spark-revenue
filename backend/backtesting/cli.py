import sys
import argparse
import logging
from datetime import datetime
from .service import BacktestingService
from .schemas import BacktestRequest
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Backtesting Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # backtest-run
    run_parser = subparsers.add_parser("backtest-run", help="Run a manual backtest")
    run_parser.add_argument("--strategy-name", default="rule_based", help="Strategy name")
    run_parser.add_argument("--symbol", required=True, help="Symbol (e.g. BTCUSDT)")
    run_parser.add_argument("--interval", default="5m", help="Interval")
    run_parser.add_argument("--start-ts", required=True, help="Start date (YYYY-MM-DD)")
    run_parser.add_argument("--end-ts", required=True, help="End date (YYYY-MM-DD)")
    
    # backtest-show
    show_parser = subparsers.add_parser("backtest-show", help="Show backtest results")
    show_parser.add_argument("--run-id", type=int, required=True, help="Run ID")
    
    return parser.parse_args()

def main():
    setup_logging()
    args = parse_args()
    service = BacktestingService()
    
    if args.command == "backtest-run":
        try:
            start_dt = datetime.strptime(args.start_ts, "%Y-%m-%d")
            end_dt = datetime.strptime(args.end_ts, "%Y-%m-%d")
            
            request = BacktestRequest(
                strategy_name=args.strategy_name,
                symbol=args.symbol,
                interval=args.interval,
                start_ts=start_dt,
                end_ts=end_dt
            )
            
            print(f"Starting backtest for {args.symbol}...")
            run, metrics = service.run_backtest(request)
            
            print("\n" + "="*40)
            print(f"BACKTEST COMPLETED (ID: {run.id})")
            print("="*40)
            print(f"Strategy:   {run.strategy_name}")
            print(f"Period:     {run.start_ts.date()} to {run.end_ts.date()}")
            print(f"Initial:    ${run.initial_capital:.2f}")
            print(f"Final:      ${run.final_capital:.2f}")
            print(f"Return:     {((run.final_capital/run.initial_capital)-1)*100:.2f}%")
            print("-"*40)
            for name, val in metrics.metrics.items():
                print(f"{name:12}: {val:.4f}")
            print("="*40)
            
        except Exception as e:
            print(f"Error running backtest: {e}")
            sys.exit(1)
            
    elif args.command == "backtest-show":
        run = service.get_backtest_run(args.run_id)
        if not run:
            print(f"Run {args.run_id} not found.")
            return
        
        metrics = service.get_backtest_metrics(args.run_id)
        print(f"Run ID {run.id} Status: {run.status}")
        if run.final_capital:
            print(f"PnL: ${run.final_capital - run.initial_capital:.2f}")
        if metrics:
            print("Metrics:", metrics.metrics)
            
    else:
        print("Use --help for available commands.")

if __name__ == "__main__":
    main()
