from typing import List, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import asc

from backend.db import InstrumentMaster
from backend.config import settings

logger = logging.getLogger(__name__)

def parse_csv_setting(value: str | None) -> List[str]:
    """
    Parses a comma-separated string into a list of trimmed strings.
    Trims whitespace, ignores empties, and returns [] for null/blank.
    """
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]

def normalize_repo_symbol(value: str) -> str:
    """
    Normalizes catalog names/trading symbols into repo symbols used elsewhere.
    v1: NIFTY 50 -> NIFTY, SENSEX -> SENSEX.
    Does not hardcode instrument keys.
    """
    if not value:
        return ""
    
    val = value.upper().strip()
    # v1 specific mappings
    if val in ["NIFTY 50", "NIFTY_50", "NIFTY"]:
        return "NIFTY"
    if val == "SENSEX":
        return "SENSEX"
    
    # Fallback to original value if no mapping found
    return val

def select_explicit_symbols() -> List[str]:
    """
    Selects symbols from explicit configuration: TRAIN_SYMBOLS or UPSTOX_DEFAULT_SYMBOLS.
    Returns normalized repo symbols, deduplicated while preserving order.
    """
    symbols = parse_csv_setting(settings.TRAIN_SYMBOLS)
    if not symbols:
        symbols = parse_csv_setting(settings.UPSTOX_DEFAULT_SYMBOLS)
    
    normalized = []
    seen = set()
    for s in symbols:
        norm = normalize_repo_symbol(s)
        if norm and norm not in seen:
            normalized.append(norm)
            seen.add(norm)
    return normalized

def select_catalog_symbols(session: Session, max_symbols: Optional[int] = None) -> List[str]:
    """
    Selects symbols dynamically from InstrumentMaster.
    Filters by broker, active status, segments, and instrument types.
    """
    segments = parse_csv_setting(settings.UPSTOX_UNIVERSE_SEGMENTS)
    types = parse_csv_setting(settings.UPSTOX_UNIVERSE_INSTRUMENT_TYPES)
    limit = max_symbols or settings.TRAIN_MAX_SYMBOLS
    
    query = session.query(InstrumentMaster).filter(
        InstrumentMaster.broker == "upstox",
        InstrumentMaster.is_active == 1
    )
    
    if segments:
        query = query.filter(InstrumentMaster.segment.in_(segments))
    if types:
        query = query.filter(InstrumentMaster.instrument_type.in_(types))
    
    # Stable ordering: segment, then trading_symbol, then id
    query = query.order_by(
        asc(InstrumentMaster.segment),
        asc(InstrumentMaster.trading_symbol),
        asc(InstrumentMaster.id)
    )
    
    results = query.all()
    
    normalized = []
    seen = set()
    for res in results:
        # Normalize from trading_symbol (fallback to name if empty)
        catalog_val = res.trading_symbol or res.name
        if not catalog_val:
            continue
            
        norm = normalize_repo_symbol(catalog_val)
        if norm and norm not in seen:
            normalized.append(norm)
            seen.add(norm)
            if len(normalized) >= limit:
                break
                
    return normalized

def get_training_universe(session: Session, mode: Optional[str] = None) -> List[str]:
    """
    Main entry point for training universe selection.
    Supports 'explicit' and 'catalog_filter' modes.
    """
    sel_mode = mode or settings.TRAIN_UNIVERSE_MODE
    
    if sel_mode == "explicit":
        return select_explicit_symbols()
    elif sel_mode == "catalog_filter":
        return select_catalog_symbols(session)
    else:
        raise ValueError(f"Invalid universe selection mode: {sel_mode}. Expected 'explicit' or 'catalog_filter'.")
