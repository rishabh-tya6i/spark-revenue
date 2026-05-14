from datetime import datetime
from typing import List, Dict, Optional
import logging

from ..db import SessionLocal
from ..instruments.service import InstrumentService
from ..ingestion.upstox_client import UpstoxMarketDataClient
from ..ingestion.binance_client import BinanceClient
from ..ingestion.ohlc_ingestor import OhlcIngestor
from ..feature_store.service import FeatureStore
from .universe import get_training_universe
from .utils import get_prepare_window, get_prepare_interval
from .trainability import get_trainable_symbols

logger = logging.getLogger(__name__)

def _select_market_data_client(db_session, symbol: str):
    """
    Selects a market data client based on symbol convention.
    - Binance for common crypto quote pairs like BTCUSDT.
    - Upstox otherwise (requires instrument resolution).
    """
    sym = (symbol or "").upper().strip()
    if sym.endswith("USDT") or sym.endswith("BUSD") or sym.endswith("USDC"):
        return BinanceClient()
    return UpstoxMarketDataClient(db_session=db_session)

def sync_instruments_core(segments: Optional[List[str]] = None) -> int:
    """
    Syncs Upstox instruments into the database.
    """
    logger.info("Starting instrument sync for data preparation")
    with SessionLocal() as db:
        service = InstrumentService(db)
        count = service.sync_upstox_instruments(segments=segments)
        return count

def backfill_ohlc_for_universe_core(
    symbols: List[str], 
    start: datetime, 
    end: datetime, 
    interval: str
) -> Dict[str, str]:
    """
    Backfills OHLC data for a list of symbols from Upstox.
    Does not abort the whole loop on a single symbol failure.
    """
    logger.info(f"Starting OHLC backfill for universe: {symbols}")
    status = {}
    
    with SessionLocal() as db:
        for symbol in symbols:
            try:
                client = _select_market_data_client(db_session=db, symbol=symbol)
                ingestor = OhlcIngestor(client=client, session_factory=SessionLocal)
                ingestor.ingest_historical(
                    symbol=symbol,
                    start=start,
                    end=end,
                    interval=interval
                )
                status[symbol] = "ok"
            except Exception as e:
                logger.error(f"OHLC backfill failed for {symbol}: {str(e)}")
                status[symbol] = f"error: {str(e)}"
                
    return status

def backfill_features_for_universe_core(
    symbols: List[str], 
    start: datetime, 
    end: datetime, 
    interval: str
) -> Dict[str, str]:
    """
    Backfills features for a list of symbols using FeatureStore.
    """
    logger.info(f"Starting feature backfill for universe: {symbols}")
    status = {}
    
    feature_store = FeatureStore()
    
    for symbol in symbols:
        try:
            count = feature_store.compute_and_store_price_features(
                symbol=symbol,
                start=start,
                end=end,
                interval=interval
            )
            status[symbol] = "ok" if count > 0 else "no_ohlc"
        except Exception as e:
            logger.error(f"Feature backfill failed for {symbol}: {str(e)}")
            status[symbol] = f"error: {str(e)}"
            
    return status

def prepare_training_data_core(
    mode: Optional[str] = None,
    interval: Optional[str] = None,
    lookback_days: Optional[int] = None,
    sync_first: bool = True,
) -> dict:
    """
    Prepares training data for the selected universe:
    1. Syncs instruments (optional)
    2. Selects training universe
    3. Backfills OHLC data
    4. Backfills features
    5. Evaluates trainability
    """
    # 1. Optionally sync instruments first
    sync_count = 0
    if sync_first:
        sync_count = sync_instruments_core()
        
    # 2. Select universe
    with SessionLocal() as db:
        symbols = get_training_universe(db, mode=mode)
    
    # 3. Determine window and interval
    prep_interval = interval or get_prepare_interval()
    start, end = get_prepare_window(days=lookback_days)
    
    summary = {
        "mode": mode or "default",
        "symbols": symbols,
        "interval": prep_interval,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "instrument_sync_count": sync_count,
        "ohlc": {},
        "features": {},
        "trainability": [],
        "trainable_symbols": []
    }
    
    if not symbols:
        logger.warning("No symbols found in the training universe. Skipping data preparation.")
        return summary
    
    # 4. Backfill OHLC for the selected universe
    summary["ohlc"] = backfill_ohlc_for_universe_core(symbols, start, end, prep_interval)
    
    # 5. Backfill Features for the selected universe
    summary["features"] = backfill_features_for_universe_core(symbols, start, end, prep_interval)
    
    # 6. Evaluate Trainability
    logger.info("Evaluating trainability for the prepared universe")
    with SessionLocal() as db:
        trainable_symbols, trainability_details = get_trainable_symbols(db, symbols, prep_interval)
        summary["trainability"] = trainability_details
        summary["trainable_symbols"] = trainable_symbols
    
    return summary
