import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from .universe import get_training_universe

logger = logging.getLogger(__name__)

def get_train_symbols(session: Optional[Session] = None) -> List[str]:
    """
    Returns the training universe symbols.
    Supports both explicit configured symbols and dynamic catalog-driven selection.
    """
    # If mode is 'explicit' and no session is provided, we can skip DB connectivity
    if settings.TRAIN_UNIVERSE_MODE == "explicit" and session is None:
        try:
            from .universe import get_training_universe
            return get_training_universe(None) # type: ignore
        except Exception as e:
            logger.error(f"Failed to get explicit training universe: {e}")
            return ["BTCUSDT"] # Safe fallback

    # Otherwise, we need a session for 'catalog_filter' or if one was provided
    if session:
        return get_training_universe(session)
    else:
        with SessionLocal() as db:
            return get_training_universe(db)

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

def get_prepare_interval() -> str:
    """
    Returns the interval used during data preparation.
    Falls back to TRAIN_DEFAULT_INTERVAL then "5m".
    """
    return settings.TRAIN_PREPARE_INTERVAL or settings.TRAIN_DEFAULT_INTERVAL or "5m"

def get_prepare_window(days: Optional[int] = None) -> Tuple[datetime, datetime]:
    """
    Returns the data preparation window.
    Defaults to last TRAIN_LOOKBACK_DAYS.
    """
    lookback = days or settings.TRAIN_LOOKBACK_DAYS or 30
    end = datetime.utcnow()
    start = end - timedelta(days=lookback)
    return start, end
