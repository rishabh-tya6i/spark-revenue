from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class OhlcBar(Base):
    __tablename__ = "ohlc_bars"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    exchange = Column(String, index=True, nullable=False)
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    vwap = Column(Float, nullable=True)

    # Index on (symbol, start_ts) for faster historical queries
    __table_args__ = (
        Index('idx_symbol_start_ts', 'symbol', 'start_ts'),
    )

class PriceFeature(Base):
    __tablename__ = "price_features"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    ts = Column(DateTime(timezone=True), index=True, nullable=False)
    interval = Column(String, nullable=False)
    rsi_14 = Column(Float, nullable=True)
    vwap = Column(Float, nullable=True)
    ema_short = Column(Float, nullable=True)
    ema_long = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint('symbol', 'ts', 'interval', name='uq_symbol_ts_interval'),
    )

class NewsItem(Base):
    __tablename__ = "news_items"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=True)
    url = Column(String, nullable=False, unique=True)
    published_ts = Column(DateTime(timezone=True), nullable=True)
    ingested_ts = Column(DateTime(timezone=True), nullable=False)

class NewsSentiment(Base):
    __tablename__ = "news_sentiment"
    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, index=True, nullable=False) # ForeignKey omitted for simplicity in v1 migrations if needed, but instructed to add.
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    created_ts = Column(DateTime(timezone=True), nullable=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
