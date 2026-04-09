import pytest
from backend.decision_engine import fusion

def test_normalize_price():
    label, conf = fusion.normalize_price_signal("UP", {"UP": 0.8, "DOWN": 0.1})
    assert label == "UP"
    assert conf == 0.8

def test_normalize_rl():
    action, conf = fusion.normalize_rl_signal("BUY", 0.9)
    assert action == "BUY"
    assert conf == 0.9
    
    action, conf = fusion.normalize_rl_signal("SELL")
    assert action == "SELL"
    assert conf == 1.0

def test_normalize_sentiment():
    scores = [0.5, 0.7, -0.2]
    labels = ["POSITIVE", "POSITIVE", "NEGATIVE"]
    avg, maj = fusion.normalize_sentiment(scores, labels)
    assert avg == pytest.approx(1.0 / 3.0)
    assert maj == "POSITIVE"

def test_fuse_signals_strong_bullish():
    # Price UP, RL BUY, Sent POS, Options PUT_BUILDUP
    label, score = fusion.fuse_signals(
        "UP", 0.9,
        "BUY", 0.9,
        0.5,
        "PUT_BUILDUP", 1.2
    )
    # base 0.5 + 0.9*0.4 + 0.9*0.4 + 0.5*0.2 + 0.2 = 0.5 + 0.36 + 0.36 + 0.1 + 0.2 = 1.52 -> clamp to 1.0
    assert label == "STRONG_BULLISH"
    assert score == 1.0

def test_fuse_signals_neutral():
    label, score = fusion.fuse_signals(
        "UP", 0.5,
        "SELL", 0.5,
        0.0,
        None, None
    )
    # base 0.5 + 0.5*0.4 - 0.5*0.4 + 0.0 = 0.5
    assert label == "NEUTRAL"
    assert score == pytest.approx(0.5)
