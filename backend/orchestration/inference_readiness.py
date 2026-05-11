import logging
from typing import List, Tuple, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import TrainedModelRecord, PriceFeature, OhlcBar
from ..config import settings
from .model_registry import get_latest_active_model

logger = logging.getLogger(__name__)

def check_symbol_inference_readiness(session: Session, symbol: str, interval: str) -> dict:
    """
    Evaluates if a symbol is ready for inference based on:
    1. Presence of active Price Model.
    2. Presence of active RL Agent.
    3. Availability of enough recent joined features.
    """
    # 1. Price model check
    price_model = get_latest_active_model(session, symbol, interval, "price_model")
    price_ready = price_model is not None
    
    # 2. RL model check
    rl_model = get_latest_active_model(session, symbol, interval, "rl_agent")
    rl_ready = rl_model is not None
    
    # 3. Feature availability check
    # We reuse the logic from price_model/service.py: at least input_window joined rows.
    input_window = getattr(settings, "PRICE_MODEL_INPUT_WINDOW", 60)
    
    # Simple count of joined rows for (symbol, interval)
    feature_count = session.query(func.count(OhlcBar.id)).join(
        PriceFeature, 
        (OhlcBar.symbol == PriceFeature.symbol) & (OhlcBar.end_ts == PriceFeature.ts)
    ).filter(
        OhlcBar.symbol == symbol,
        OhlcBar.interval == interval,
        PriceFeature.interval == interval
    ).scalar()
    
    feature_ready = feature_count >= input_window
    
    # Final Readiness
    ready = price_ready and rl_ready and feature_ready
    
    # Determine reason if not ready
    reason = None
    if not ready:
        reasons = []
        if not price_ready: reasons.append("missing_price_model")
        if not rl_ready: reasons.append("missing_rl_model")
        if not feature_ready: reasons.append("missing_features")
        reason = "_and_".join(reasons)

    return {
        "symbol": symbol,
        "interval": interval,
        "price_model_ready": price_ready,
        "rl_model_ready": rl_ready,
        "feature_ready": feature_ready,
        "ready": ready,
        "reason": reason,
        "price_model_record_id": price_model.id if price_model else None,
        "rl_model_record_id": rl_model.id if rl_model else None,
    }

def get_inference_ready_symbols(session: Session, symbols: List[str], interval: str) -> Tuple[List[str], List[dict]]:
    """
    Evaluates readiness for a list of symbols.
    Returns (ready_symbols_list, all_details_list).
    """
    ready_symbols = []
    all_details = []
    
    for symbol in symbols:
        detail = check_symbol_inference_readiness(session, symbol, interval)
        all_details.append(detail)
        if detail["ready"]:
            ready_symbols.append(symbol)
            
    return ready_symbols, all_details
