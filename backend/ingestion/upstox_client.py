import httpx
import logging
from urllib.parse import quote
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from backend.config import settings
from backend.settings.token_store import get_upstox_token
from .schemas import BaseMarketDataClient, OhlcBarIn
from ..instruments.service import InstrumentService

logger = logging.getLogger(__name__)

class UpstoxHistoricalClient:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or get_upstox_token()
        if not self.access_token:
            raise ValueError("UPSTOX_ACCESS_TOKEN is missing. Please set it in .env or config.")
        
        self.base_url = settings.UPSTOX_API_BASE_URL.rstrip('/')
        self.api_version = settings.UPSTOX_HISTORICAL_API_VERSION or "v3"

    def _map_interval(self, interval: str) -> Tuple[str, int]:
        """
        Maps repo intervals (e.g. '1m', '5m', '1h', '1d') to Upstox (unit, interval).
        """
        mapping = {
            "1m": ("minutes", 1),
            "5m": ("minutes", 5),
            "15m": ("minutes", 15),
            "30m": ("minutes", 30),
            "1h": ("hours", 1),
            "1d": ("days", 1),
        }
        if interval not in mapping:
            raise ValueError(f"Unsupported interval: {interval}. Supported: {list(mapping.keys())}")
        return mapping[interval]

    def get_historical_candles(
        self,
        instrument_key: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> List[Dict]:
        """
        Fetches historical candles from Upstox V3 API.
        URL format: /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
        """
        unit, intv = self._map_interval(interval)
        
        to_date_str = end.strftime("%Y-%m-%d")
        from_date_str = start.strftime("%Y-%m-%d")
        
        # URL-encode instrument_key as it may contain characters like '|' or spaces
        encoded_key = quote(instrument_key)
        
        # Upstox V3 path: /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
        url = f"{self.base_url}/{self.api_version}/historical-candle/{encoded_key}/{unit}/{intv}/{to_date_str}/{from_date_str}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        logger.info(f"Fetching Upstox historical candles from {url}")
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                if data.get("status") != "success":
                    errors = data.get("errors", [])
                    error_msg = errors[0].get("message", "Unknown Upstox API error") if errors else "Unknown Upstox API error"
                    raise Exception(f"Upstox API Error: {error_msg}")
                
                candles = data.get("data", {}).get("candles", [])
                # Upstox returns candles as [timestamp, open, high, low, close, volume, open_interest]
                
                normalized = []
                for c in candles:
                    # Parse timestamp. Example: "2024-05-10T09:15:00+05:30"
                    ts_str = c[0]
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except ValueError:
                        # Fallback for some formats
                        ts = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")

                    normalized.append({
                        "start_ts": ts,
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5])
                    })
                
                # Sort by timestamp ascending
                normalized.sort(key=lambda x: x["start_ts"])
                
                return normalized
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching Upstox candles: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching Upstox historical candles: {str(e)}")
            raise

class UpstoxMarketDataClient(BaseMarketDataClient):
    def __init__(self, db_session, access_token: Optional[str] = None):
        self.historical_client = UpstoxHistoricalClient(access_token)
        self.instrument_service = InstrumentService(db_session)

    def _get_delta(self, interval: str) -> timedelta:
        if interval.endswith("m"):
            return timedelta(minutes=int(interval[:-1]))
        if interval.endswith("h"):
            return timedelta(hours=int(interval[:-1]))
        if interval == "1d":
            return timedelta(days=1)
        return timedelta(minutes=1)

    def fetch_historical_ohlc(
        self, 
        symbol: str, 
        start: datetime, 
        end: datetime, 
        interval: str
    ) -> List[OhlcBarIn]:
        # 1. Resolve symbol
        resolved = self.instrument_service.resolve_symbol(symbol)
        if not resolved:
            raise ValueError(f"Symbol {symbol} not found in instrument_master; run instrument sync first.")
        
        # 2. Fetch candles
        candles = self.historical_client.get_historical_candles(
            instrument_key=resolved.instrument_key,
            interval=interval,
            start=start,
            end=end
        )
        
        delta = self._get_delta(interval)
        
        # 3. Map to OhlcBarIn
        results = []
        for c in candles:
            results.append(OhlcBarIn(
                symbol=symbol,
                exchange=resolved.exchange,
                start_ts=c["start_ts"],
                end_ts=c["start_ts"] + delta,
                open=c["open"],
                high=c["high"],
                low=c["low"],
                close=c["close"],
                volume=c["volume"]
            ))
        return results
