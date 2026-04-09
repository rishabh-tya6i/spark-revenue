import os
import pytest

# Set this before any other imports to ensure settings are loaded with mock values
os.environ["DATABASE_URL"] = "sqlite:///file:memdb1?mode=memory&cache=shared"
os.environ["SENTIMENT_STUB_MODE"] = "true"
