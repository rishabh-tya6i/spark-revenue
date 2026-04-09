import logging
from datetime import datetime, timedelta
from typing import List, Tuple
from ..config import settings

logger = logging.getLogger(__name__)

def get_train_symbols() -> List[str]:
    """
    Reads TRAIN_SYMBOLS from settings.
    Defaults to ["BTCUSDT"] if not set.
    """
    if not settings.TRAIN_SYMBOLS:
        logger.warning("TRAIN_SYMBOLS not set, defaulting to ['BTCUSDT']")
        return ["BTCUSDT"]
    
    symbols = [s.strip() for s in settings.TRAIN_SYMBOLS.split(",") if s.strip()]
    if not symbols:
        logger.warning("TRAIN_SYMBOLS was empty after parsing, defaulting to ['BTCUSDT']")
        return ["BTCUSDT"]
        
    return symbols

def get_train_interval() -> str:
    """
    Returns the default training interval.
    """
    return settings.TRAIN_DEFAULT_INTERVAL or "5m"

def get_training_window(days: int = 30) -> Tuple[datetime, datetime]:
    """
    Returns a training window for the last N days.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end
