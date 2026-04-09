import argparse
import logging
from .flows import train_price_models_flow, train_rl_agents_flow, daily_training_flow
from ..logging_config import setup_logging

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Spark Revenue Orchestration CLI")
    subparsers = parser.add_subparsers(dest="command", help="Orchestration commands")

    # train-price-models
    price_parser = subparsers.add_parser("train-price-models", help="Train price prediction models")
    price_parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    price_parser.add_argument("--interval", type=str, help="Data interval")
    price_parser.add_argument("--epochs", type=int, default=10, help="Number of epochs")

    # train-rl-agents
    rl_parser = subparsers.add_parser("train-rl-agents", help="Train RL agents")
    rl_parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    rl_parser.add_argument("--interval", type=str, help="Data interval")
    rl_parser.add_argument("--episodes", type=int, help="Number of episodes")

    # run-daily
    subparsers.add_parser("run-daily", help="Run the daily master training flow")

    args = parser.parse_args()

    if args.command == "train-price-models":
        symbols = args.symbols.split(",") if args.symbols else None
        train_price_models_flow(symbols=symbols, interval=args.interval, epochs=args.epochs)
    elif args.command == "train-rl-agents":
        symbols = args.symbols.split(",") if args.symbols else None
        train_rl_agents_flow(symbols=symbols, interval=args.interval, episodes=args.episodes)
    elif args.command == "run-daily":
        daily_training_flow()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
