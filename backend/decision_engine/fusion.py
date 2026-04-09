from typing import List, Tuple, Optional

def normalize_price_signal(model_label: str, probabilities: dict) -> Tuple[str, float]:
    """
    Maps price model outputs to direction and confidence.
    Assume probabilities is a dict like {"UP": 0.7, "DOWN": 0.2, "FLAT": 0.1}
    """
    direction = model_label.upper()
    confidence = probabilities.get(direction, 0.0)
    return direction, confidence

def normalize_rl_signal(action: str, confidence: Optional[float] = None) -> Tuple[str, float]:
    """
    Maps RL action and optional confidence.
    """
    return action.upper(), confidence if confidence is not None else 1.0

def normalize_sentiment(sentiment_scores: List[float], sentiment_labels: List[str]) -> Tuple[Optional[float], Optional[str]]:
    """
    Aggregates sentiment from a list of recent items.
    """
    if not sentiment_scores:
        return None, None
    
    avg_score = sum(sentiment_scores) / len(sentiment_scores)
    # Most frequent label
    label_counts = {}
    for l in sentiment_labels:
        label_counts[l] = label_counts.get(l, 0) + 1
    majority_label = max(label_counts, key=label_counts.get)
    
    return avg_score, majority_label

def normalize_options_signal(options_signal_label: Optional[str], pcr: Optional[float], max_pain: Optional[float]) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """
    Extracts options metrics.
    """
    return options_signal_label, pcr, max_pain

def fuse_signals(
    price_direction: Optional[str], price_confidence: Optional[float],
    rl_action: Optional[str], rl_confidence: Optional[float],
    sentiment_score: Optional[float],
    options_signal_label: Optional[str], options_pcr: Optional[float]
) -> Tuple[str, float]:
    """
    Heuristic fusion of multiple signals into a single score [0, 1] and label.
    0.0 = Strong Bearish, 0.5 = Neutral, 1.0 = Strong Bullish
    """
    score = 0.5
    
    # Price weights
    if price_direction == "UP":
        score += (price_confidence or 0.5) * 0.4
    elif price_direction == "DOWN":
        score -= (price_confidence or 0.5) * 0.4
        
    # RL weights
    if rl_action == "BUY":
        score += (rl_confidence or 0.5) * 0.4
    elif rl_action == "SELL":
        score -= (rl_confidence or 0.5) * 0.4
        
    # Sentiment weights
    if sentiment_score is not None:
        score += sentiment_score * 0.2 # sentiment_score is [-1, 1]
        
    # Options weights
    if options_signal_label == "PUT_BUILDUP": # Bullish
        score += 0.2
    elif options_signal_label == "CALL_BUILDUP": # Bearish
        score -= 0.2
        
    # Clamp
    score = max(0.0, min(1.0, score))
    
    # Label mapping
    if score >= 0.75:
        label = "STRONG_BULLISH"
    elif score >= 0.6:
        label = "BULLISH"
    elif score <= 0.25:
        label = "STRONG_BEARISH"
    elif score <= 0.4:
        label = "BEARISH"
    else:
        label = "NEUTRAL"
        
    return label, score
