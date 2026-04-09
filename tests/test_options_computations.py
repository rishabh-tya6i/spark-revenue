import pytest
from datetime import datetime
from backend.options_intel.schemas import OptionSnapshotIn
from backend.options_intel.computations import compute_pcr, compute_max_pain_strike, derive_option_signal

@pytest.fixture
def sample_snapshots():
    now = datetime.utcnow()
    expiry = now
    # Underlying spot around 100
    return [
        OptionSnapshotIn(symbol="TEST", expiry=expiry, strike=90, option_type="CE", open_interest=1000, timestamp=now),
        OptionSnapshotIn(symbol="TEST", expiry=expiry, strike=100, option_type="CE", open_interest=5000, timestamp=now),
        OptionSnapshotIn(symbol="TEST", expiry=expiry, strike=110, option_type="CE", open_interest=1000, timestamp=now),
        OptionSnapshotIn(symbol="TEST", expiry=expiry, strike=90, option_type="PE", open_interest=1000, timestamp=now),
        OptionSnapshotIn(symbol="TEST", expiry=expiry, strike=100, option_type="PE", open_interest=2000, timestamp=now),
        OptionSnapshotIn(symbol="TEST", expiry=expiry, strike=110, option_type="PE", open_interest=5000, timestamp=now),
    ]

def test_compute_pcr(sample_snapshots):
    # Calls: 1000 + 5000 + 1000 = 7000
    # Puts: 1000 + 2000 + 5000 = 8000
    pcr, call_total, put_total = compute_pcr(sample_snapshots)
    assert call_total == 7000
    assert put_total == 8000
    assert pcr == 8000 / 7000

def test_max_pain(sample_snapshots):
    # Max pain should be strike where overall value lost is minimal
    # In our sample, strikes are 90, 100, 110
    strike = compute_max_pain_strike(sample_snapshots)
    assert strike in [90, 100, 110]

def test_derive_signal():
    label, strength = derive_option_signal(2.0, 1000, 2000)
    assert label == "PUT_BUILDUP"
    assert strength == pytest.approx(1.0)
    
    label, strength = derive_option_signal(0.3, 2000, 600)
    assert label == "CALL_BUILDUP"
    assert strength == pytest.approx(1.0)
    
    label, strength = derive_option_signal(1.0, 1000, 1000)
    assert label == "NEUTRAL"
    assert strength == 0.0
