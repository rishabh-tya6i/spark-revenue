from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Index, UniqueConstraint, ForeignKey
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
    interval = Column(String, index=True, nullable=False, default="5m")
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

class OptionSnapshot(Base):
    __tablename__ = "option_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    expiry = Column(DateTime(timezone=True), index=True, nullable=False)
    strike = Column(Float, index=True, nullable=False)
    option_type = Column(String, nullable=False) # "CE" or "PE"
    open_interest = Column(Float, nullable=False)
    change_in_oi = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    last_traded_price = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    __table_args__ = (
        Index("idx_opt_symbol_expiry_strike_type_ts", "symbol", "expiry", "strike", "option_type", "timestamp"),
    )

class OptionSignal(Base):
    __tablename__ = "option_signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    expiry = Column(DateTime(timezone=True), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    pcr = Column(Float, nullable=True)
    max_pain_strike = Column(Float, nullable=True)
    call_oi_total = Column(Float, nullable=True)
    put_oi_total = Column(Float, nullable=True)
    signal_label = Column(String, nullable=True)   # e.g., "CALL_BUILDUP", "PUT_BUILDUP", "NEUTRAL"
    signal_strength = Column(Float, nullable=True) # 0..1

class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    interval = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    decision_label = Column(String, nullable=False)     # e.g., STRONG_BULLISH / BEARISH / NEUTRAL
    decision_score = Column(Float, nullable=False)      # 0..1

    price_direction = Column(String, nullable=True)     # e.g., UP/DOWN/FLAT
    price_confidence = Column(Float, nullable=True)

    rl_action = Column(String, nullable=True)           # BUY/SELL/HOLD
    rl_confidence = Column(Float, nullable=True)

    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)

    options_signal_label = Column(String, nullable=True)
    options_pcr = Column(Float, nullable=True)
    options_max_pain_strike = Column(Float, nullable=True)

    raw_payload = Column(String, nullable=True)         # JSON string with full fused payload if needed

class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    interval = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    alert_type = Column(String, nullable=False)         # e.g., "HIGH_CONFIDENCE_BREAKOUT"
    message = Column(String, nullable=False)
    importance = Column(Float, nullable=False)          # 0..1
    delivered_channels = Column(String, nullable=True)  # e.g., "desktop"

class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    interval = Column(String, nullable=False)
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="PENDING")  # PENDING/RUNNING/COMPLETED/FAILED
    created_ts = Column(DateTime(timezone=True), nullable=False)
    completed_ts = Column(DateTime(timezone=True), nullable=True)
    details = Column(String, nullable=True)  # JSON string for extra config if needed

class BacktestMetric(Base):
    __tablename__ = "backtest_metrics"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False)
    metric_name = Column(String, nullable=False)  # e.g., "win_rate", "max_drawdown", "sharpe"
    metric_value = Column(Float, nullable=False)

class ExecutionAccount(Base):
    __tablename__ = "execution_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # e.g., "default"
    base_currency = Column(String, nullable=False, default="USD")
    initial_balance = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    created_ts = Column(DateTime(timezone=True), nullable=False)
    updated_ts = Column(DateTime(timezone=True), nullable=False)

class ExecutionPosition(Base):
    __tablename__ = "execution_positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("execution_accounts.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    quantity = Column(Float, nullable=False)       # long > 0, short < 0
    avg_price = Column(Float, nullable=False)      # average fill price
    updated_ts = Column(DateTime(timezone=True), nullable=False)

class ExecutionOrder(Base):
    __tablename__ = "execution_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("execution_accounts.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)          # "BUY" or "SELL"
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)          # executed price
    decision_id = Column(Integer, ForeignKey("decision_records.id"), nullable=True)
    created_ts = Column(DateTime(timezone=True), nullable=False)

class ExecutionPnL(Base):
    __tablename__ = "execution_pnl"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("execution_accounts.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)         # cash + sum(position market value)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
