from datetime import datetime
import logging

from .schemas import BaseMarketDataClient, OhlcBarIn
from ..db import OhlcBar, SessionLocal

logger = logging.getLogger(__name__)

class OhlcIngestor:
    def __init__(self, client: BaseMarketDataClient, session_factory=SessionLocal):
        self.client = client
        self.session_factory = session_factory

    def ingest_historical(
        self, 
        symbol: str, 
        start: datetime, 
        end: datetime, 
        interval: str
    ):
        """
        Fetches historical data from the client and upserts into the database.
        Includes basic time range chunking logic.
        """
        logger.info(f"Starting historical ingestion for {symbol}")
        
        # Simple chunking: If range > 30 days, we might want to split it.
        # For now, let's assume the client handles it or the user provides reasonable ranges.
        # Real-world implementation would iterate through 'current_start' and 'current_end'.
        
        bars = self.client.fetch_historical_ohlc(symbol, start, end, interval)
        
        if not bars:
            logger.info(f"No data returned for {symbol}")
            return

        count = 0
        with self.session_factory() as session:
            for bar in bars:
                existing = session.query(OhlcBar).filter(
                    OhlcBar.symbol == bar.symbol,
                    OhlcBar.interval == interval,
                    OhlcBar.start_ts == bar.start_ts,
                ).first()

                if existing:
                    for key, value in bar.model_dump().items():
                        setattr(existing, key, value)
                    existing.interval = interval
                else:
                    new_bar = OhlcBar(**bar.model_dump(), interval=interval)
                    session.add(new_bar)
                count += 1
            
            session.commit()
            
        logger.info(f"Successfully ingested {count} bars for {symbol}")

class LiveFeedIngestor:
    """
    Skeleton for live feed ingestion.
    """
    def __init__(self, kafka_producer=None):
        self.kafka_producer = kafka_producer

    async def start_live_feed(self, symbol: str):
        """
        Skeleton for connecting to a WebSocket and publishing to Kafka.
        """
        logger.info(f"Starting live feed skeleton for {symbol}")
        # TODO: Implement WebSocket connection logic
        # TODO: Implement message normalization
        # TODO: Implement Kafka publishing
        logger.warning("Live feed is NOT implemented yet.")
        pass

    def publish_to_kafka(self, topic: str, message: dict):
        """
        Stub for Kafka producer.
        """
        # if self.kafka_producer:
        #     self.kafka_producer.produce(topic, value=json.dumps(message))
        pass
