import logging
from typing import List, Tuple, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import OhlcBar, PriceFeature
from ..config import settings

logger = logging.getLogger(__name__)

def get_min_required_ohlc_bars() -> int:
    """
    Returns the minimum number of OHLC bars required for training.
    Derived from PRICE_MODEL_INPUT_WINDOW and PRICE_MODEL_PREDICTION_HORIZON.
    v1: max(window + horizon + buffer, 50)
    """
    window = settings.PRICE_MODEL_INPUT_WINDOW or 60
    horizon = settings.PRICE_MODEL_PREDICTION_HORIZON or 12
    buffer = settings.TRAINABILITY_MIN_BUFFER_BARS or 5
    
    threshold = max(window + horizon + buffer, 50)
    return threshold

def get_min_required_feature_rows() -> int:
    """
    Returns the minimum number of feature rows required for training.
    Currently follows the same threshold as OHLC.
    """
    return get_min_required_ohlc_bars()

def check_symbol_trainability(session: Session, symbol: str, interval: str) -> dict:
    """
    Checks if a symbol has enough data in DB to be trainable.
    Returns a dict with counts, thresholds, and trainability status.
    """
    min_ohlc = get_min_required_ohlc_bars()
    min_feat = get_min_required_feature_rows()
    
    # Query OHLC count
    ohlc_count = session.query(func.count(OhlcBar.id)).filter(
        OhlcBar.symbol == symbol,
        OhlcBar.interval == interval
    ).scalar() or 0
    
    # Query Feature count
    feat_count = session.query(func.count(PriceFeature.id)).filter(
        PriceFeature.symbol == symbol,
        PriceFeature.interval == interval
    ).scalar() or 0
    
    trainable = True
    reason = None
    
    if ohlc_count < min_ohlc and feat_count < min_feat:
        trainable = False
        reason = "missing_ohlc_and_features"
    elif ohlc_count < min_ohlc:
        trainable = False
        reason = "insufficient_ohlc"
    elif feat_count < min_feat:
        trainable = False
        reason = "insufficient_features"
        
    return {
        "symbol": symbol,
        "interval": interval,
        "ohlc_count": ohlc_count,
        "feature_count": feat_count,
        "min_ohlc_required": min_ohlc,
        "min_feature_required": min_feat,
        "trainable": trainable,
        "reason": reason,
    }

def get_trainable_symbols(session: Session, symbols: List[str], interval: str) -> Tuple[List[str], List[dict]]:
    """
    Evaluates trainability for a list of symbols.
    Returns: (list of trainable symbol strings, list of full detail dicts)
    """
    trainable_symbols = []
    details = []
    
    for symbol in symbols:
        res = check_symbol_trainability(session, symbol, interval)
        details.append(res)
        if res["trainable"]:
            trainable_symbols.append(symbol)
            
    return trainable_symbols, details
