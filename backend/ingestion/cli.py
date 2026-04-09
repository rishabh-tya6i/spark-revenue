import argparse
import sys
from datetime import datetime
import logging

from .ohlc_ingestor import OhlcIngestor
from .zerodha_client import ZerodhaClient
from .binance_client import BinanceClient
from ..config import settings
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Spark Revenue Data Ingestion CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Backfill command
    backfill_parser = subparsers.add_parser("backfill", help="Backfill historical OHLC data")
    backfill_parser.add_argument("--source", choices=["zerodha", "binance"], required=True, help="Data source")
    backfill_parser.add_argument("--symbol", required=True, help="Symbol to backfill (e.g. NIFTY, BTCUSDT)")
    backfill_parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    backfill_parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    backfill_parser.add_argument("--interval", default="5m", help="Candle interval (e.g. 1m, 5m, day)")

    args = parser.parse_args()

    if args.command == "backfill":
        setup_logging()
        
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d")
            end_date = datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)

        # Initialize client
        if args.source == "zerodha":
            client = ZerodhaClient(
                api_key=settings.ZERODHA_API_KEY,
                api_secret=settings.ZERODHA_API_SECRET,
                access_token=settings.ZERODHA_ACCESS_TOKEN
            )
        elif args.source == "binance":
            client = BinanceClient(
                api_key=settings.BINANCE_API_KEY,
                api_secret=settings.BINANCE_API_SECRET
            )
        else:
            logger.error(f"Unsupported source: {args.source}")
            sys.exit(1)

        ingestor = OhlcIngestor(client=client)
        
        try:
            ingestor.ingest_historical(
                symbol=args.symbol,
                start=start_date,
                end=end_date,
                interval=args.interval
            )
        except Exception as e:
            logger.error(f"Ingestion failed: {str(e)}")
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
