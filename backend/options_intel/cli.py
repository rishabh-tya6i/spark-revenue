import sys
import argparse
import logging
from datetime import datetime
from ..logging_config import setup_logging
from .ingestion import OptionsIngestor
from .service import OptionsIntelService

logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Options Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # options-snapshot
    snap_parser = subparsers.add_parser("options-snapshot", help="Ingest options chain snapshot")
    snap_parser.add_argument("--symbol", required=True, help="Symbol (e.g., NIFTY)")
    snap_parser.add_argument("--expiry", required=True, help="Expiry date (YYYY-MM-DD)")
    
    # options-signal
    sig_parser = subparsers.add_parser("options-signal", help="Compute and store options signals")
    sig_parser.add_argument("--symbol", required=True, help="Symbol")
    sig_parser.add_argument("--expiry", required=True, help="Expiry date (YYYY-MM-DD)")
    
    return parser.parse_args()

def main():
    setup_logging()
    args = parse_args()
    
    try:
        expiry_dt = datetime.strptime(args.expiry, "%Y-%m-%d")
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD.")
        sys.exit(1)
        
    if args.command == "options-snapshot":
        ingestor = OptionsIngestor()
        count = ingestor.ingest_snapshot(args.symbol, expiry_dt)
        logger.info(f"Ingested {count} option snapshots for {args.symbol}")
        
    elif args.command == "options-signal":
        service = OptionsIntelService()
        signal = service.compute_and_store_signals(args.symbol, expiry_dt)
        if signal:
            print(f"--- Options Signal for {args.symbol} [{args.expiry}] ---")
            print(f"Timestamp: {signal.timestamp}")
            print(f"PCR:       {signal.pcr:.4f}")
            print(f"Max Pain:  {signal.max_pain_strike}")
            print(f"Signal:    {signal.signal_label} ({signal.signal_strength:.1%})")
        else:
            logger.error("No data found to compute signal.")
            sys.exit(1)
    else:
        print("Use --help for available commands.")

if __name__ == "__main__":
    main()
