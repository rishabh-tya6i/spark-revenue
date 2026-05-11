from datetime import datetime, timezone
from typing import List
import logging
import httpx
from .schemas import BaseMarketDataClient, OhlcBarIn

logger = logging.getLogger(__name__)

class BinanceClient(BaseMarketDataClient):
    INTERVAL_MAP = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "6h": "6h",
        "8h": "8h",
        "12h": "12h",
        "1d": "1d",
        "1w": "1w",
        "1M": "1M",
    }

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com"

    def fetch_historical_ohlc(
        self, 
        symbol: str, 
        start: datetime, 
        end: datetime, 
        interval: str
    ) -> List[OhlcBarIn]:
        """
        Fetches historical data from Binance Spot public klines API.
        """
        logger.info(f"Fetching historical OHLC from Binance for {symbol} ({interval}) from {start} to {end}")

        binance_interval = self.INTERVAL_MAP.get(interval)
        if not binance_interval:
            raise ValueError(f"Unsupported Binance interval: {interval}")

        start_ms = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)

        bars: List[OhlcBarIn] = []
        current_start = start_ms

        try:
            with httpx.Client(base_url=self.base_url, timeout=30.0) as client:
                while current_start < end_ms:
                    params = {
                        "symbol": symbol,
                        "interval": binance_interval,
                        "startTime": current_start,
                        "endTime": end_ms,
                        "limit": 1000,
                    }
                    response = client.get("/api/v3/klines", params=params)
                    response.raise_for_status()
                    data = response.json()

                    if not data:
                        break

                    for item in data:
                        open_time = datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc)
                        close_time = datetime.fromtimestamp(item[6] / 1000, tz=timezone.utc)
                        bars.append(
                            OhlcBarIn(
                                symbol=symbol,
                                exchange="BINANCE",
                                start_ts=open_time,
                                end_ts=close_time,
                                open=float(item[1]),
                                high=float(item[2]),
                                low=float(item[3]),
                                close=float(item[4]),
                                volume=float(item[5]),
                                vwap=None,
                            )
                        )

                    current_start = int(data[-1][6]) + 1

                    if len(data) < 1000:
                        break

            logger.info(f"Fetched {len(bars)} Binance candles for {symbol}")
            return bars
        except Exception as e:
            logger.error(f"Error fetching historical data from Binance: {str(e)}")
            raise
