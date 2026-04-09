from typing import List, Tuple, Optional
from .schemas import OptionSnapshotIn

def compute_pcr(snapshots: List[OptionSnapshotIn]) -> Tuple[float, float, float]:
    """
    Computes Put-Call Ratio (PCR) by Open Interest.
    Returns (pcr, call_oi_total, put_oi_total).
    """
    call_oi = sum(s.open_interest for s in snapshots if s.option_type == "CE")
    put_oi = sum(s.open_interest for s in snapshots if s.option_type == "PE")
    
    pcr = put_oi / call_oi if call_oi > 0 else 0.0
    return pcr, call_oi, put_oi

def compute_max_pain_strike(snapshots: List[OptionSnapshotIn]) -> Optional[float]:
    """
    Estimates the Max Pain strike price.
    Returns the strike where total option pain is minimized.
    """
    if not snapshots:
        return None
        
    strikes = sorted(list(set(s.strike for s in snapshots)))
    min_pain = float('inf')
    max_pain_strike = strikes[0]
    
    for spot in strikes:
        current_pain = 0
        for s in snapshots:
            if s.option_type == "CE":
                # Calls are in pain if spot > strike
                pain = max(0, spot - s.strike) * s.open_interest
            else:
                # Puts are in pain if spot < strike
                pain = max(0, s.strike - spot) * s.open_interest
            current_pain += pain
            
        if current_pain < min_pain:
            min_pain = current_pain
            max_pain_strike = spot
            
    return max_pain_strike

def derive_option_signal(pcr: float, call_oi: float, put_oi: float) -> Tuple[str, float]:
    """
    Derives a simple directional signal based on PCR thresholds.
    """
    if pcr > 1.3:
        label = "PUT_BUILDUP" # Usually interpreted as bullish/overbought support
        strength = min(1.0, (pcr - 1.3) / 0.7) # 1.3 -> 0.0, 2.0 -> 1.0
    elif pcr < 0.7:
        label = "CALL_BUILDUP" # Bearish resistance
        strength = min(1.0, (0.7 - pcr) / 0.4) # 0.7 -> 0.0, 0.3 -> 1.0
    else:
        label = "NEUTRAL"
        strength = 0.0
        
    return label, strength
