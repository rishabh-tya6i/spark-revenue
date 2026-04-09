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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
