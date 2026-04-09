import json
import logging
from datetime import datetime
from typing import List, Optional
import redis
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from ..db import PriceFeature, OhlcBar, SessionLocal
from ..config import settings
from ..ingestion.schemas import OhlcBarIn
from .schemas import PriceFeatureIn, PriceFeatureOut
from .computations import compute_price_features

logger = logging.getLogger(__name__)

class FeatureStore:
    def __init__(self, session_factory=SessionLocal, redis_client: Optional[redis.Redis] = None):
        self.session_factory = session_factory
        self.redis = redis_client or (
            redis.from_url(settings.REDIS_URL, decode_responses=True) if settings.REDIS_URL else None
        )

    def compute_and_store_price_features(
        self, 
        symbol: str, 
        start: datetime, 
        end: datetime, 
        interval: str
    ) -> int:
        """
        Fetches OHLC bars, computes features, and stores them in Postgres.
        """
        logger.info(f"Computing features for {symbol} ({interval}) from {start} to {end}")
        
        with self.session_factory() as session:
            # 1. Fetch OHLC bars
            bars = session.query(OhlcBar).filter(
                OhlcBar.symbol == symbol,
                OhlcBar.end_ts >= start,
                OhlcBar.end_ts <= end
            ).order_by(OhlcBar.start_ts.asc()).all()
            
            if not bars:
                logger.warning(f"No OHLC bars found for {symbol} in range")
                return 0

            # 2. Convert to schemas
            ohlc_ins = [OhlcBarIn.model_validate(bar) for bar in bars]
            
            # 3. Compute features
            feature_list = compute_price_features(ohlc_ins, interval)
            
            # 4. Upsert into database
            count = 0
            for feat in feature_list:
                stmt = insert(PriceFeature).values(**feat.model_dump())
                
                # PostgreSQL on conflict update
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_symbol_ts_interval',
                    set_={
                        'rsi_14': feat.rsi_14,
                        'vwap': feat.vwap,
                        'ema_short': feat.ema_short,
                        'ema_long': feat.ema_long
                    }
                )
                session.execute(stmt)
                count += 1
            
            session.commit()
            logger.info(f"Stored {count} features for {symbol}")
            return count

    def get_latest_price_features(self, symbol: str, interval: str) -> Optional[PriceFeatureOut]:
        """
        Retrieves the latest price features from Redis, falling back to Postgres.
        """
        redis_key = f"feature:price:{symbol}:{interval}"
        
        # 1. Try Redis
        if self.redis:
            try:
                cached = self.redis.get(redis_key)
                if cached:
                    logger.debug(f"Cache HIT for {redis_key}")
                    return PriceFeatureOut.model_validate(json.loads(cached))
            except Exception as e:
                logger.error(f"Redis error: {e}")

        # 2. Fallback to Postgres
        logger.debug(f"Cache MISS for {redis_key}")
        with self.session_factory() as session:
            feat = session.query(PriceFeature).filter(
                PriceFeature.symbol == symbol,
                PriceFeature.interval == interval
            ).order_by(PriceFeature.ts.desc()).first()
            
            if feat:
                out = PriceFeatureOut.model_validate(feat)
                # 3. Store in Redis
                if self.redis:
                    try:
                        self.redis.setex(
                            redis_key,
                            settings.REDIS_FEATURE_TTL_SECONDS,
                            json.dumps(out.model_dump(mode='json'))
                        )
                    except Exception as e:
                        logger.error(f"Redis set error: {e}")
                return out
        
        return None
