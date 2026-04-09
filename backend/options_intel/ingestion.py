import logging
import random
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from ..db import OptionSnapshot, SessionLocal
from ..config import settings
from .schemas import OptionSnapshotIn

logger = logging.getLogger(__name__)

class OptionsIngestor:
    def __init__(self, session_factory=SessionLocal, data_source: Optional[str] = None):
        self.session_factory = session_factory
        self.data_source = data_source or settings.OPTIONS_DATA_SOURCE

    def fetch_options_snapshot(self, symbol: str, expiry: datetime) -> List[OptionSnapshotIn]:
        """
        Fetches options chain snapshot. Currently supports a stubbed source.
        """
        if self.data_source == "stub":
            return self._fetch_stubbed_data(symbol, expiry)
        
        logger.warning(f"Data source {self.data_source} not implemented. Falling back to stub.")
        return self._fetch_stubbed_data(symbol, expiry)

    def _fetch_stubbed_data(self, symbol: str, expiry: datetime) -> List[OptionSnapshotIn]:
        """
        Generates synthetic options chain data.
        """
        now = datetime.utcnow()
        # Assume an underlying price
        underlying = 22000.0 if "NIFTY" in symbol else 450.0
        strike_step = 50.0 if "NIFTY" in symbol else 5.0
        
        # 10 strikes above and below
        strikes = [underlying + (i * strike_step) for i in range(-10, 11)]
        
        snapshots = []
        for strike in strikes:
            # Generate CE
            # OI higher naturally at round numbers or resistance levels
            ce_oi = random.uniform(5000, 50000)
            snapshots.append(OptionSnapshotIn(
                symbol=symbol,
                expiry=expiry,
                strike=strike,
                option_type="CE",
                open_interest=ce_oi,
                change_in_oi=ce_oi * random.uniform(-0.1, 0.2),
                volume=ce_oi * random.uniform(2, 10),
                last_traded_price=max(1.0, underlying * 0.05 * (1 - (strike-underlying)/underlying)),
                timestamp=now
            ))
            
            # Generate PE
            pe_oi = ce_oi * random.uniform(0.5, 1.5) # Varied PCR
            snapshots.append(OptionSnapshotIn(
                symbol=symbol,
                expiry=expiry,
                strike=strike,
                option_type="PE",
                open_interest=pe_oi,
                change_in_oi=pe_oi * random.uniform(-0.1, 0.2),
                volume=pe_oi * random.uniform(2, 10),
                last_traded_price=max(1.0, underlying * 0.05 * (1 + (strike-underlying)/underlying)),
                timestamp=now
            ))
            
        return snapshots

    def ingest_snapshot(self, symbol: str, expiry: datetime, timestamp: Optional[datetime] = None) -> int:
        """
        Fetches and stores a snapshot in the database.
        """
        logger.info(f"Ingesting options snapshot for {symbol} expiry {expiry}")
        snapshots = self.fetch_options_snapshot(symbol, expiry)
        
        if not snapshots:
            return 0
            
        ingest_ts = timestamp or snapshots[0].timestamp
        
        with self.session_factory() as session:
            for s in snapshots:
                db_item = OptionSnapshot(
                    **s.model_dump(exclude={"timestamp"}),
                    timestamp=ingest_ts
                )
                session.add(db_item)
            
            session.commit()
            return len(snapshots)
