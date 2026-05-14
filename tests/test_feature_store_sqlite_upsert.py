from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, OhlcBar, PriceFeature
from backend.feature_store.service import FeatureStore


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_feature_store_upsert_sqlite(db_session):
    symbol = "TST"
    interval = "5m"

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(30):
        ts = start + timedelta(minutes=5 * i)
        db_session.add(
            OhlcBar(
                symbol=symbol,
                interval=interval,
                exchange="TEST",
                start_ts=ts,
                end_ts=ts + timedelta(minutes=5),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=10.0,
            )
        )
    db_session.commit()

    store = FeatureStore(session_factory=TestingSessionLocal, redis_client=None)

    count_1 = store.compute_and_store_price_features(
        symbol=symbol,
        start=start,
        end=start + timedelta(days=1),
        interval=interval,
    )
    assert count_1 > 0

    rows_1 = db_session.query(func.count(PriceFeature.id)).filter(
        PriceFeature.symbol == symbol,
        PriceFeature.interval == interval,
    ).scalar()
    assert rows_1 == count_1

    # Re-run to verify ON CONFLICT upsert works on SQLite (no duplicates).
    count_2 = store.compute_and_store_price_features(
        symbol=symbol,
        start=start,
        end=start + timedelta(days=1),
        interval=interval,
    )
    assert count_2 == count_1

    rows_2 = db_session.query(func.count(PriceFeature.id)).filter(
        PriceFeature.symbol == symbol,
        PriceFeature.interval == interval,
    ).scalar()
    assert rows_2 == rows_1

