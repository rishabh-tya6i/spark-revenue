import argparse
import sys
from datetime import datetime
import logging

from .service import FeatureStore
from ..config import settings
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Spark Revenue Feature Store CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Features Backfill command
    backfill_parser = subparsers.add_parser("features-backfill", help="Compute and store price features")
    backfill_parser.add_argument("--symbol", required=True, help="Symbol to backfill (e.g. NIFTY, BTCUSDT)")
    backfill_parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    backfill_parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    backfill_parser.add_argument("--interval", default="5m", help="Candle interval (e.g. 1m, 5m, day)")

    args = parser.parse_args()

    if args.command == "features-backfill":
        setup_logging()
        
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d")
            end_date = datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)

        feature_store = FeatureStore()
        
        try:
            count = feature_store.compute_and_store_price_features(
                symbol=args.symbol,
                start=start_date,
                end=end_date,
                interval=args.interval
            )
            print(f"Successfully processed {count} feature rows.")
        except Exception as e:
            logger.error(f"Feature processing failed: {str(e)}")
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
