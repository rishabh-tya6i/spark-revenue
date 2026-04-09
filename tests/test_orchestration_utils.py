import pytest
from datetime import datetime, timedelta
from backend.orchestration.utils import get_train_symbols, get_train_interval, get_training_window
from backend.config import settings

def test_get_train_symbols_default(mocker):
    mocker.patch.object(settings, "TRAIN_SYMBOLS", None)
    symbols = get_train_symbols()
    assert symbols == ["BTCUSDT"]

def test_get_train_symbols_custom(mocker):
    mocker.patch.object(settings, "TRAIN_SYMBOLS", "ETHUSDT, SOLUSDT ")
    symbols = get_train_symbols()
    assert symbols == ["ETHUSDT", "SOLUSDT"]

def test_get_train_interval(mocker):
    mocker.patch.object(settings, "TRAIN_DEFAULT_INTERVAL", "1h")
    assert get_train_interval() == "1h"

def test_get_training_window():
    start, end = get_training_window(days=7)
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert (end - start) == timedelta(days=7)
