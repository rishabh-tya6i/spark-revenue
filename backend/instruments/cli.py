import argparse
import sys
from backend.db import SessionLocal
import logging
from backend.instruments.service import InstrumentService
from backend.logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Upstox Instruments CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Sync Command
    sync_parser = subparsers.add_parser("sync-upstox-instruments", help="Sync instruments from Upstox")
    sync_parser.add_argument("--segments", type=str, help="Comma-separated segments (e.g. NSE_INDEX,BSE_INDEX)")

    # List Command
    list_parser = subparsers.add_parser("list-instruments", help="List synced instruments")
    list_parser.add_argument("--segment", type=str, help="Filter by segment")
    list_parser.add_argument("--instrument-type", type=str, help="Filter by instrument type")
    list_parser.add_argument("--limit", type=int, default=10, help="Limit results")

    # Resolve Command
    resolve_parser = subparsers.add_parser("resolve-symbol", help="Resolve symbol to instrument key")
    resolve_parser.add_argument("--symbol", type=str, required=True, help="Symbol to resolve (e.g. NIFTY)")

    args = parser.parse_args()

    db = SessionLocal()
    service = InstrumentService(db)

    try:
        if args.command == "sync-upstox-instruments":
            segments = args.segments.split(",") if args.segments else None
            count = service.sync_upstox_instruments(segments=segments)
            print(f"Successfully synced {count} instruments")

        elif args.command == "list-instruments":
            instruments = service.list_instruments(
                segment=args.segment,
                instrument_type=args.instrument_type,
                limit=args.limit
            )
            for inst in instruments:
                print(f"{inst.instrument_key} | {inst.segment} | {inst.trading_symbol} | {inst.name}")

        elif args.command == "resolve-symbol":
            res = service.resolve_symbol(args.symbol)
            if res:
                print(f"Resolved {args.symbol}:")
                print(f"  Instrument Key: {res.instrument_key}")
                print(f"  Segment: {res.segment}")
                print(f"  Exchange: {res.exchange}")
                print(f"  Type: {res.instrument_type}")
                print(f"  Trading Symbol: {res.trading_symbol}")
                print(f"  Name: {res.name}")
            else:
                print(f"Could not resolve symbol: {args.symbol}")
                sys.exit(1)
        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"CLI command failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
