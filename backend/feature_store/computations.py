from datetime import datetime
from typing import List, Optional
from ..ingestion.schemas import OhlcBarIn
from .schemas import PriceFeatureIn

def compute_price_features(ohlc_bars: List[OhlcBarIn], interval: str) -> List[PriceFeatureIn]:
    """
    Computes technical indicators from OHLC bars.
    Assumes ohlc_bars are sorted by timestamp ascending.
    """
    features = []
    
    # State for indicators
    prices = [bar.close for bar in ohlc_bars]
    volumes = [bar.volume for bar in ohlc_bars]
    
    # Pre-calculate RSI
    rsi_values = _calculate_rsi(prices, 14)
    
    # Pre-calculate EMAs
    ema_short_values = _calculate_ema(prices, 12)
    ema_long_values = _calculate_ema(prices, 26)
    
    # Cumulative VWAP
    cum_pv = 0.0
    cum_v = 0.0
    
    for i, bar in enumerate(ohlc_bars):
        # Update VWAP
        # Note: Cumulative VWAP usually resets daily or is for a specific session.
        # Here we follow instruction: "cumulative VWAP".
        avg_price = (bar.high + bar.low + bar.close) / 3.0
        cum_pv += avg_price * bar.volume
        cum_v += bar.volume
        # Some instruments (e.g. cash indices) may have volume=0 for all bars.
        # Keep vwap non-null so downstream model joins/dropna don't wipe the dataset.
        vwap = (cum_pv / cum_v) if cum_v > 0 else avg_price
        
        feature = PriceFeatureIn(
            symbol=bar.symbol,
            ts=bar.start_ts, # Instruction says "ts: timestamp of bar close", but OhlcBar has start_ts/end_ts. 
                             # Usually end_ts is close. I'll use end_ts.
            interval=interval,
            rsi_14=rsi_values[i],
            vwap=vwap,
            ema_short=ema_short_values[i],
            ema_long=ema_long_values[i]
        )
        # Fix: The instruction said "ts (DateTime) - timestamp of bar close". 
        # I'll update it to use end_ts.
        feature.ts = bar.end_ts
        
        features.append(feature)
        
    return features

def _calculate_rsi(prices: List[float], period: int) -> List[Optional[float]]:
    if not prices:
        return []
    
    rsi = [None] * len(prices)
    if len(prices) <= period:
        return rsi
        
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
        
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))
        
    for i in range(period + 1, len(prices)):
        gain = gains[i-1]
        loss = losses[i-1]
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
            
    return rsi

def _calculate_ema(prices: List[float], period: int) -> List[Optional[float]]:
    if not prices:
        return []
    
    ema = [None] * len(prices)
    if len(prices) < period:
        return ema
        
    k = 2 / (period + 1)
    
    # First EMA is simple moving average
    ema[period-1] = sum(prices[:period]) / period
    
    for i in range(period, len(prices)):
        ema[i] = prices[i] * k + ema[i-1] * (1 - k)
        
    return ema
