import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from ..db import OhlcBar, PriceFeature
import logging

logger = logging.getLogger(__name__)

def build_price_model_dataset(
    session: Session, 
    symbol: str, 
    interval: str, 
    input_window: int = 60, 
    prediction_horizon: int = 12,
    flat_threshold: float = 0.001 # 0.1% for classification
) -> tuple[np.ndarray, np.ndarray]:
    """
    Builds a dataset for the LSTM model.
    Target: 3-class classification (0: DOWN, 1: FLAT, 2: UP)
    """
    logger.info(f"Building dataset for {symbol} ({interval})")

    # 1. Query data
    # Join OhlcBar and PriceFeature
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
        OhlcBar.interval == interval,
        PriceFeature.interval == interval
    ).order_by(OhlcBar.end_ts.asc())

    data = query.all()
    if not data:
        return np.array([]), np.array([])

    df = pd.DataFrame(data, columns=['close', 'rsi_14', 'vwap', 'ema_short', 'ema_long', 'ts'])
    
    # Handle NaNs (e.g. from early indicator bars)
    df = df.dropna()
    
    if len(df) < input_window + prediction_horizon:
        logger.warning("Not enough data to create any sequences.")
        return np.array([]), np.array([])

    # 2. Add features
    # Standardize or normalize? For v1, let's just use log returns for features too where applicable, 
    # but the user asked for these specific ones. 
    # We'll normalize indicators by close price or use them as is if they are bounded (RSI).
    
    # Simple feature engineering:
    df['rsi_14'] = df['rsi_14'] / 100.0 # Scale to [0, 1]
    df['vwap_ratio'] = df['vwap'] / df['close']
    df['ema_short_ratio'] = df['ema_short'] / df['close']
    df['ema_long_ratio'] = df['ema_long'] / df['close']
    
    # Use log returns for the close price itself to make it stationary
    df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
    df = df.dropna()

    feature_cols = ['log_ret', 'rsi_14', 'vwap_ratio', 'ema_short_ratio', 'ema_long_ratio']
    X_raw = df[feature_cols].values
    close_prices = df['close'].values

    num_samples = len(df) - input_window - prediction_horizon + 1
    
    X = []
    y = []

    for i in range(num_samples):
        # Input sequence
        X.append(X_raw[i : i + input_window])
        
        # Target: Log return between close_t and close_{t+horizon}
        # index t is i + input_window - 1
        current_close = close_prices[i + input_window - 1]
        future_close = close_prices[i + input_window - 1 + prediction_horizon]
        log_return = np.log(future_close / current_close)
        
        # Classification
        if log_return > flat_threshold:
            label = 2 # UP
        elif log_return < -flat_threshold:
            label = 0 # DOWN
        else:
            label = 1 # FLAT
        
        y.append(label)

    return np.array(X), np.array(y)
