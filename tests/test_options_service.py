import pytest
from datetime import datetime, timedelta
from backend.db import Base, engine, SessionLocal, OptionSnapshot, OptionSignal
from backend.options_intel.service import OptionsIntelService

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_signal_computation():
    now = datetime.utcnow()
    expiry = now + timedelta(days=7)
    
    # Seed snapshots manually
    with SessionLocal() as session:
        for strike in [100, 110]:
            session.add(OptionSnapshot(
                symbol="TEST", expiry=expiry, strike=strike, option_type="CE",
                open_interest=1000, timestamp=now
            ))
            session.add(OptionSnapshot(
                symbol="TEST", expiry=expiry, strike=strike, option_type="PE",
                open_interest=2000, timestamp=now
            ))
        session.commit()
        
    service = OptionsIntelService()
    signal = service.compute_and_store_signals("TEST", expiry, timestamp=now)
    
    assert signal is not None
    assert signal.symbol == "TEST"
    assert signal.pcr == 2.0
    assert signal.signal_label == "PUT_BUILDUP"
    
    # Retrieve latest
    latest = service.get_latest_signal("TEST", expiry)
    assert latest.id == signal.id
