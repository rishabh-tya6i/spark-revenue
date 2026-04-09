import argparse
import sys
import logging
from .train import train_price_model
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Spark Revenue Price Model CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Train command
    train_parser = subparsers.add_parser("price-model-train", help="Train LSTM model for a symbol")
    train_parser.add_argument("--symbol", required=True, help="Symbol to train on (e.g. NIFTY, BTCUSDT)")
    train_parser.add_argument("--interval", default="5m", help="Candle interval (e.g. 1m, 5m, day)")
    train_parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    train_parser.add_argument("--batch-size", type=int, default=32, help="Training batch size")

    args = parser.parse_args()

    if args.command == "price-model-train":
        setup_logging()
        try:
            model_path = train_price_model(
                symbol=args.symbol,
                interval=args.interval,
                epochs=args.epochs,
                batch_size=args.batch_size
            )
            if model_path:
                print(f"Training completed. Model saved at: {model_path}")
            else:
                print("Training failed.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Training error: {str(e)}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
