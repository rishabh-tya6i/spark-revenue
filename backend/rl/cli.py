import argparse
import sys
import logging
from .train import train_rl_agent
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Spark Revenue RL Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # RL Train command
    train_parser = subparsers.add_parser("rl-train", help="Train RL agent for a symbol")
    train_parser.add_argument("--symbol", required=True, help="Symbol to train on (e.g. NIFTY, BTCUSDT)")
    train_parser.add_argument("--interval", default="5m", help="Candle interval (e.g. 1m, 5m, day)")
    train_parser.add_argument("--episodes", type=int, help="Number of training episodes")

    args = parser.parse_args()

    if args.command == "rl-train":
        setup_logging()
        try:
            model_path = train_rl_agent(
                symbol=args.symbol,
                interval=args.interval,
                episodes=args.episodes
            )
            if model_path:
                print(f"Training completed. Model saved at: {model_path}")
            else:
                print("Training failed (likely due to missing data).")
                sys.exit(1)
        except Exception as e:
            logger.error(f"RL Training error: {str(e)}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
