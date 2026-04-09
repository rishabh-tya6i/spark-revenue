import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Spark Revenue AI Trading OS"
    DEBUG: bool = False

    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/trading_db"

    # Zerodha Settings
    ZERODHA_API_KEY: str = "placeholder_key"
    ZERODHA_API_SECRET: str = "placeholder_secret"
    ZERODHA_ACCESS_TOKEN: Optional[str] = None

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
