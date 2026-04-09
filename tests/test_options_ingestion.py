import pytest
from datetime import datetime, timedelta
from backend.db import Base, engine, SessionLocal, OptionSnapshot
from backend.options_intel.ingestion import OptionsIngestor

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(OptionSnapshot).delete()
        session.commit()
    yield
    # Base.metadata.drop_all(bind=engine) # Usually handled by conftest

def test_stub_ingestion():
    ingestor = OptionsIngestor()
    expiry = datetime.utcnow() + timedelta(days=7)
    count = ingestor.ingest_snapshot("NIFTY_TEST", expiry)
    assert count > 0
    
    with SessionLocal() as session:
        rows = session.query(OptionSnapshot).filter(OptionSnapshot.symbol == "NIFTY_TEST").all()
        assert len(rows) == count
        assert rows[0].symbol == "NIFTY_TEST"
        assert rows[0].option_type in ["CE", "PE"]
        assert rows[0].open_interest >= 0
