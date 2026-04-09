import os
from backend.config import Settings

def test_config_loading():
    # Test default values
    settings = Settings(_env_file=None) # Don't load from .env
    assert settings.APP_NAME == "Spark Revenue AI Trading OS"
    
    # Test environment variable override
    os.environ["ZERODHA_API_KEY"] = "test_key"
    settings = Settings(_env_file=None)
    assert settings.ZERODHA_API_KEY == "test_key"
