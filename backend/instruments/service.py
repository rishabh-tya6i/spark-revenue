from datetime import datetime
import json
from typing import List, Optional
import logging

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.db import InstrumentMaster
from backend.instruments.schemas import InstrumentRecordIn, InstrumentRecordOut, InstrumentResolveResult
from backend.instruments.upstox_client import UpstoxInstrumentsClient
from backend.config import settings
from backend.logging_config import setup_logging

logger = logging.getLogger(__name__)

class InstrumentService:
    def __init__(self, db: Session):
        self.db = db
        self.client = UpstoxInstrumentsClient()

    def parse_upstox_instruments(self, raw_items: List[dict]) -> List[InstrumentRecordIn]:
        parsed = []
        for item in raw_items:
            try:
                expiry = item.get("expiry")
                expiry_dt = None
                if expiry:
                    # Upstox usually provides expiry as timestamp (ms) or YYYY-MM-DD
                    try:
                        if isinstance(expiry, (int, float)):
                            expiry_dt = datetime.fromtimestamp(expiry / 1000.0)
                        elif isinstance(expiry, str):
                            if "-" in expiry:
                                expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                            else:
                                # Try timestamp as string
                                expiry_dt = datetime.fromtimestamp(int(expiry) / 1000.0)
                    except Exception as e:
                        logger.debug(f"Failed to parse expiry {expiry}: {e}")

                record = InstrumentRecordIn(
                    broker="upstox",
                    instrument_key=item["instrument_key"],
                    segment=item["segment"],
                    exchange=item["exchange"],
                    instrument_type=item["instrument_type"],
                    trading_symbol=item.get("trading_symbol"),
                    name=item.get("name"),
                    short_name=item.get("short_name"),
                    underlying_symbol=item.get("underlying_symbol"),
                    underlying_key=item.get("underlying_key"),
                    expiry=expiry_dt,
                    strike_price=float(item["strike"]) if item.get("strike") else None,
                    tick_size=float(item["tick_size"]) if item.get("tick_size") else None,
                    lot_size=float(item["lot_size"]) if item.get("lot_size") else None,
                    raw_json=json.dumps(item),
                    is_active=1
                )
                parsed.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse instrument item: {item.get('instrument_key')}, error: {e}")
                continue
        return parsed

    def sync_upstox_instruments(self, segments: List[str] | None = None) -> int:
        """
        Fetches and upserts Upstox instruments. 
        Supports both PostgreSQL (optimized batch) and SQLite (portable loop) for cross-DB compatibility.
        """
        if segments is None and settings.UPSTOX_UNIVERSE_SEGMENTS:
            segments = [s.strip() for s in settings.UPSTOX_UNIVERSE_SEGMENTS.split(",")]

        raw_items = self.client.fetch_instruments()
        parsed_records = self.parse_upstox_instruments(raw_items)
        
        if segments:
            parsed_records = [r for r in parsed_records if r.segment in segments]
            
        logger.info(f"Upserting {len(parsed_records)} instruments into database")
        
        processed_count = 0
        now = datetime.now()
        
        # Determine dialect for optimized sync
        dialect_name = self.db.get_bind().dialect.name
        
        # Batch size for processing
        batch_size = 500
        for i in range(0, len(parsed_records), batch_size):
            batch = parsed_records[i:i+batch_size]
            
            if dialect_name == "postgresql":
                # Use PostgreSQL ON CONFLICT DO UPDATE for performance
                values = []
                for r in batch:
                    d = r.model_dump()
                    d["created_ts"] = now
                    d["updated_ts"] = now
                    values.append(d)
                
                stmt = pg_insert(InstrumentMaster).values(values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['instrument_key'],
                    set_={
                        "segment": stmt.excluded.segment,
                        "exchange": stmt.excluded.exchange,
                        "instrument_type": stmt.excluded.instrument_type,
                        "trading_symbol": stmt.excluded.trading_symbol,
                        "name": stmt.excluded.name,
                        "short_name": stmt.excluded.short_name,
                        "underlying_symbol": stmt.excluded.underlying_symbol,
                        "underlying_key": stmt.excluded.underlying_key,
                        "expiry": stmt.excluded.expiry,
                        "strike_price": stmt.excluded.strike_price,
                        "tick_size": stmt.excluded.tick_size,
                        "lot_size": stmt.excluded.lot_size,
                        "raw_json": stmt.excluded.raw_json,
                        "is_active": stmt.excluded.is_active,
                        "updated_ts": now
                    }
                )
                self.db.execute(stmt)
            else:
                # Portable fallback (SQLite and others) - IDEMPOTENT sync
                for r in batch:
                    existing = self.db.query(InstrumentMaster).filter_by(instrument_key=r.instrument_key).first()
                    if existing:
                        # Update existing record
                        existing.segment = r.segment
                        existing.exchange = r.exchange
                        existing.instrument_type = r.instrument_type
                        existing.trading_symbol = r.trading_symbol
                        existing.name = r.name
                        existing.short_name = r.short_name
                        existing.underlying_symbol = r.underlying_symbol
                        existing.underlying_key = r.underlying_key
                        existing.expiry = r.expiry
                        existing.strike_price = r.strike_price
                        existing.tick_size = r.tick_size
                        existing.lot_size = r.lot_size
                        existing.raw_json = r.raw_json
                        existing.is_active = r.is_active
                        existing.updated_ts = now
                    else:
                        # Insert new record
                        new_inst = InstrumentMaster(
                            **r.model_dump(exclude={"expiry"}),
                            expiry=r.expiry,
                            created_ts=now,
                            updated_ts=now
                        )
                        self.db.add(new_inst)
            
            processed_count += len(batch)
            # Flush periodically for non-batch to keep memory low if needed, 
            # though commit at end is fine for 500-1000 items.
            if dialect_name != "postgresql":
                self.db.flush()
        
        self.db.commit()
        logger.info(f"Successfully synced {processed_count} instruments")
        return processed_count

    def list_instruments(self, segment: str | None = None, instrument_type: str | None = None, limit: int = 100) -> List[InstrumentRecordOut]:
        query = self.db.query(InstrumentMaster)
        if segment:
            query = query.filter(InstrumentMaster.segment == segment)
        if instrument_type:
            query = query.filter(InstrumentMaster.instrument_type == instrument_type)
        
        results = query.limit(limit).all()
        return [InstrumentRecordOut.model_validate(r) for r in results]

    def resolve_symbol(self, symbol: str) -> InstrumentResolveResult | None:
        """
        V1 Alias Resolution Layer.
        Translates human-friendly symbols to broker-specific instrument keys via DB lookup.
        The DB remains the source of truth; no instrument_key values are hardcoded here.
        """
        symbol_upper = symbol.upper()
        
        # Base query for active instruments
        query = self.db.query(InstrumentMaster).filter(InstrumentMaster.is_active == 1)
        
        # 1. Handle explicit common aliases
        if symbol_upper == "NIFTY":
            # Upstox index names are typically "NIFTY 50"
            res = query.filter(
                InstrumentMaster.segment == "NSE_INDEX",
                (InstrumentMaster.trading_symbol == "NIFTY 50") | 
                (InstrumentMaster.trading_symbol == "NIFTY_50") | 
                (InstrumentMaster.name == "NIFTY 50")
            ).first()
        elif symbol_upper == "SENSEX":
            res = query.filter(
                InstrumentMaster.segment == "BSE_INDEX",
                (InstrumentMaster.trading_symbol == "SENSEX") | 
                (InstrumentMaster.name == "SENSEX")
            ).first()
        else:
            # 2. Generic lookup: Exact match first (case-insensitive)
            res = query.filter(
                (sa.func.upper(InstrumentMaster.trading_symbol) == symbol_upper) | 
                (sa.func.upper(InstrumentMaster.name) == symbol_upper)
            ).first()
            
            # 3. Fallback to ilike if exact match fails
            if not res:
                res = query.filter(
                    (InstrumentMaster.trading_symbol.ilike(f"%{symbol_upper}%")) | 
                    (InstrumentMaster.name.ilike(f"%{symbol_upper}%"))
                ).first()

        if res:
            return InstrumentResolveResult(
                symbol=symbol_upper,
                instrument_key=res.instrument_key,
                segment=res.segment,
                exchange=res.exchange,
                instrument_type=res.instrument_type,
                trading_symbol=res.trading_symbol,
                name=res.name
            )
        return None

    def get_default_training_universe(self) -> List[InstrumentResolveResult]:
        symbols_str = settings.UPSTOX_DEFAULT_SYMBOLS or "NIFTY,SENSEX"
        symbols = [s.strip() for s in symbols_str.split(",")]
        
        results = []
        for sym in symbols:
            resolved = self.resolve_symbol(sym)
            if resolved:
                results.append(resolved)
        return results
