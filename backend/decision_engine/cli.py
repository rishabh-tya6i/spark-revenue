import sys
import argparse
import logging
from .service import DecisionEngineService
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Decision Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # decision-compute
    compute_parser = subparsers.add_parser("decision-compute", help="Compute fused decision")
    compute_parser.add_argument("--symbol", required=True, help="Symbol")
    compute_parser.add_argument("--interval", default="5m", help="Interval (default: 5m)")
    
    # alerts-recent
    alerts_parser = subparsers.add_parser("alerts-recent", help="Show recent alerts")
    alerts_parser.add_argument("--symbol", help="Filter by symbol")
    alerts_parser.add_argument("--limit", type=int, default=20, help="Limit (default: 20)")
    
    return parser.parse_args()

def main():
    setup_logging()
    args = parse_args()
    service = DecisionEngineService()
    
    if args.command == "decision-compute":
        decision = service.compute_and_store_decision(args.symbol, args.interval)
        print(f"--- Decision for {args.symbol} ({args.interval}) ---")
        print(f"Label: {decision.decision_label}")
        print(f"Score: {decision.decision_score:.4f}")
        
    elif args.command == "alerts-recent":
        alerts = service.get_recent_alerts(args.limit)
        print(f"--- Recent Alerts (limit: {args.limit}) ---")
        for a in alerts:
            if args.symbol and a.symbol != args.symbol:
                continue
            print(f"[{a.timestamp}] {a.symbol} | {a.alert_type} | {a.message}")
            
    else:
        print("Use --help for available commands.")

if __name__ == "__main__":
    main()
