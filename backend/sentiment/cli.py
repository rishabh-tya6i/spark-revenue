import argparse
import sys
import logging
from .ingestion import NewsIngestor
from .service import SentimentService
from ..logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Spark Revenue News Sentiment CLI")
    subparsers = parser.add_subparsers(dest="command")

    # news-fetch command
    subparsers.add_parser("news-fetch", help="Fetch items from RSS feeds")

    # sentiment-score command
    score_parser = subparsers.add_parser("sentiment-score", help="Compute sentiment for unscored news")
    score_parser.add_argument("--batch-size", type=int, help="Number of items to score in this run")

    args = parser.parse_args()

    setup_logging()
    
    if args.command == "news-fetch":
        try:
            ingestor = NewsIngestor()
            count = ingestor.ingest_from_feeds()
            print(f"Successfully ingested {count} new items.")
        except Exception as e:
            logger.error(f"News fetch failed: {str(e)}")
            sys.exit(1)

    elif args.command == "sentiment-score":
        try:
            service = SentimentService()
            count = service.score_unscored_news(batch_size=args.batch_size)
            print(f"Successfully scored {count} news items.")
        except Exception as e:
            logger.error(f"Sentiment scoring failed: {str(e)}")
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
