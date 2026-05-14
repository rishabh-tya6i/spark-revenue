import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Spark Revenue AI Trading OS"
    DEBUG: bool = False
    # CORS
    # Use "*" to allow any origin (useful for local dev / Electron).
    # Otherwise provide a comma-separated list of allowed origins.
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/trading_db"

    # Zerodha Settings
    ZERODHA_API_KEY: str = "placeholder_key"
    ZERODHA_API_SECRET: str = "placeholder_secret"
    ZERODHA_ACCESS_TOKEN: Optional[str] = None

    # Upstox Settings
    UPSTOX_ACCESS_TOKEN: Optional[str] = None
    UPSTOX_API_BASE_URL: str = "https://api.upstox.com"
    UPSTOX_INSTRUMENTS_JSON_URL: Optional[str] = None
    UPSTOX_UNIVERSE_SEGMENTS: Optional[str] = "NSE_INDEX,BSE_INDEX"
    UPSTOX_DEFAULT_SYMBOLS: Optional[str] = "NIFTY,SENSEX"
    UPSTOX_HISTORICAL_API_VERSION: str = "v3"
    UPSTOX_UNIVERSE_INSTRUMENT_TYPES: Optional[str] = "INDEX"

    # Binance Settings
    BINANCE_API_KEY: str = "placeholder_key"
    BINANCE_API_SECRET: str = "placeholder_secret"

    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_MARKET_TICKS_TOPIC: str = "market_ticks"

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_FEATURE_TTL_SECONDS: int = 300

    # Price Prediction Model Settings
    PRICE_MODEL_DIR: str = "models/price_model"
    PRICE_MODEL_INPUT_WINDOW: int = 60
    PRICE_MODEL_PREDICTION_HORIZON: int = 12

    # RL Agent Settings
    RL_AGENT_MODEL_DIR: str = "models/rl_agent"
    RL_TRAINING_EPISODES: int = 50
    RL_MAX_STEPS_PER_EPISODE: int = 500
    RL_INITIAL_CAPITAL: float = 100000.0
    RL_TRANSACTION_COST_BPS: float = 10.0

    # News / Sentiment Settings
    NEWS_RSS_FEEDS: Optional[str] = None # Comma-separated list of URLs
    SENTIMENT_MODEL_NAME: str = "ProsusAI/finbert"
    SENTIMENT_BATCH_SIZE: int = 16

    # Options / Derivatives Settings
    OPTIONS_DATA_SOURCE: str = "stub" # e.g. "nse", "stub"
    OPTIONS_DEFAULT_EXCHANGE: str = "NSE"

    # Decision Engine Settings
    DECISION_MIN_CONFIDENCE: float = 0.6

    # Alerts Settings
    ALERT_MIN_IMPORTANCE: float = 0.7
    ALERT_MIN_IMPORTANCE: float = 0.7
    ALERT_CHANNELS: Optional[str] = None # Comma-separated, e.g. "desktop,telegram"

    # Backtesting Settings
    BACKTEST_INITIAL_CAPITAL: float = 100000.0
    BACKTEST_TRANSACTION_COST_BPS: float = 10.0
    BACKTEST_DEFAULT_INTERVAL: str = "5m"
    
    # Training / Orchestration Settings
    TRAIN_SYMBOLS: Optional[str] = None  # Comma-separated, e.g. "BTCUSDT,ETHUSDT"
    TRAIN_UNIVERSE_MODE: str = "explicit"   # "explicit" or "catalog_filter"
    TRAIN_MAX_SYMBOLS: int = 10
    TRAIN_LOOKBACK_DAYS: int = 30
    TRAIN_PREPARE_INTERVAL: Optional[str] = None
    TRAIN_DEFAULT_INTERVAL: str = "5m"
    TRAIN_DAILY_RUN_HOUR_UTC: int = 3  # e.g., run at 03:00 UTC
    TRAINABILITY_MIN_BUFFER_BARS: int = 5

    # Execution / Paper Trading Settings
    EXECUTION_MODE: str = "paper"  # "paper" or "live"
    EXECUTION_DEFAULT_SYMBOLS: Optional[str] = None
    EXECUTION_BASE_CURRENCY: str = "USD"
    EXECUTION_MAX_POSITION_PER_SYMBOL: float = 1.0        # Max units (e.g., 1 BTC)
    EXECUTION_MAX_NOTIONAL_PER_SYMBOL: float = 20000.0    # In base currency
    
    # Global Operational Guardrails
    EXECUTION_ENABLED: bool = True
    EXECUTION_MAX_SYMBOLS_PER_RUN: int = 5
    EXECUTION_ALLOWED_ACTIONS: Optional[str] = "BUY,SELL"
    
    # Staleness Controls
    EXECUTION_MAX_DECISION_AGE_MINUTES: int = 30
    EXECUTION_MAX_OVERRIDE_AGE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
