import httpx
import gzip
import json
from typing import List, Dict
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class UpstoxInstrumentsClient:
    """
    Client to fetch Upstox instrument master data.
    
    The default URL points to the Beginning of Day (BOD) full instrument JSON 
    used in production by many Upstox integrations.
    """
    # Current practice downloadable BOD JSON source
    DEFAULT_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

    def fetch_instruments(self) -> List[Dict]:
        """
        Fetches the full instrument list. 
        Uses UPSTOX_INSTRUMENTS_JSON_URL from settings if provided as an override.
        """
        url = settings.UPSTOX_INSTRUMENTS_JSON_URL or self.DEFAULT_INSTRUMENTS_URL
        logger.info(f"Fetching Upstox instruments from: {url}")
        
        try:
            with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()
                
                content = response.content
                
                # Check if it's gzipped (by extension or magic bytes)
                if url.endswith(".gz") or content[:2] == b'\x1f\x8b':
                    logger.debug("Decompressing gzipped instrument content")
                    content = gzip.decompress(content)
                
                instruments = json.loads(content)
                logger.info(f"Successfully fetched {len(instruments)} instruments from Upstox")
                return instruments
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching instruments from {url}: {e.response.status_code}. "
                "Ensure UPSTOX_INSTRUMENTS_JSON_URL is correct if overridden."
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error fetching Upstox instruments from {url}: {str(e)}. "
                "You can override this URL via UPSTOX_INSTRUMENTS_JSON_URL in .env"
            )
            raise
