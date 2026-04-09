import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from ..db import OhlcBar, PriceFeature
import logging
import random
import torch

logger = logging.getLogger(__name__)

def load_rl_data(session: Session, symbol: str, interval: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Loads features and corresponding close prices for RL environment.
    """
    logger.info(f"Loading RL data for {symbol} ({interval})")
    
    query = session.query(
        OhlcBar.close,
        PriceFeature.rsi_14,
        PriceFeature.vwap,
        PriceFeature.ema_short,
        PriceFeature.ema_long,
        OhlcBar.end_ts
    ).join(
        PriceFeature, 
        (OhlcBar.symbol == PriceFeature.symbol) & (OhlcBar.end_ts == PriceFeature.ts)
    ).filter(
        OhlcBar.symbol == symbol,
        PriceFeature.interval == interval
    ).order_by(OhlcBar.end_ts.asc())

    data = query.all()
    if not data:
        return np.array([]), np.array([])

    df = pd.DataFrame(data, columns=['close', 'rsi_14', 'vwap', 'ema_short', 'ema_long', 'ts'])
    df = df.dropna()
    
    if df.empty:
        return np.array([]), np.array([])

    # Feature Engineering (Identical to Price Model for consistency)
    df['rsi_14_scaled'] = df['rsi_14'] / 100.0
    df['vwap_ratio'] = df['vwap'] / df['close']
    df['ema_short_ratio'] = df['ema_short'] / df['close']
    df['ema_long_ratio'] = df['ema_long'] / df['close']
    df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
    
    df = df.dropna()
    
    feature_cols = ['log_ret', 'rsi_14_scaled', 'vwap_ratio', 'ema_short_ratio', 'ema_long_ratio']
    features = df[feature_cols].values
    prices = df['close'].values
    
    return features, prices

def set_global_seeds(seed: int):
    """
    Sets seeds for reproducibility.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
