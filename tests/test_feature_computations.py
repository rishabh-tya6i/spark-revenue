import pytest
from datetime import datetime, timedelta
from backend.ingestion.schemas import OhlcBarIn
from backend.feature_store.computations import compute_price_features

def test_compute_price_features_length():
    bars = [
        OhlcBarIn(symbol="TEST", exchange="EX", start_ts=datetime(2024, 1, 1, 10, 0), end_ts=datetime(2024, 1, 1, 10, 5),
                  open=100, high=105, low=95, close=102, volume=1000)
        for i in range(30)
    ]
    features = compute_price_features(bars, "5m")
    assert len(features) == len(bars)

def test_rsi_trend():
    # Consistently rising price should increase RSI
    bars = []
    base_ts = datetime(2024, 1, 1, 10, 0)
    for i in range(30):
        bars.append(OhlcBarIn(
            symbol="TEST", exchange="EX",
            start_ts=base_ts + timedelta(minutes=5*i),
            end_ts=base_ts + timedelta(minutes=5*(i+1)),
            open=100+i, high=105+i, low=95+i, close=100+i+1, volume=1000
        ))
    
    features = compute_price_features(bars, "5m")
    
    # First 14 bars might have None or partial RSI
    # After that, it should be high
    valid_rsi = [f.rsi_14 for f in features if f.rsi_14 is not None]
    assert len(valid_rsi) > 0
    assert valid_rsi[-1] > 70 # Should be overbought

def test_vwap_calculation():
    bars = [
        OhlcBarIn(symbol="TEST", exchange="EX", 
                  start_ts=datetime(2024, 1, 1, 10, 0), end_ts=datetime(2024, 1, 1, 10, 5),
                  open=100, high=110, low=90, close=100, volume=100), # Typical = 100
        OhlcBarIn(symbol="TEST", exchange="EX", 
                  start_ts=datetime(2024, 1, 1, 10, 5), end_ts=datetime(2024, 1, 1, 10, 10),
                  open=100, high=120, low=110, close=115, volume=200) # Typical = 115
    ]
    # VWAP = (100*100 + 115*200) / (100+200) = (10000 + 23000) / 300 = 33000 / 300 = 110
    features = compute_price_features(bars, "5m")
    assert features[0].vwap == 100.0
    assert features[1].vwap == 110.0
