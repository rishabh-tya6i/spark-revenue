import feedparser
import logging
from datetime import datetime
from typing import List, Optional
from time import mktime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from ..db import NewsItem, SessionLocal
from ..config import settings
from .schemas import NewsItemIn

logger = logging.getLogger(__name__)

class NewsIngestor:
    def __init__(self, session_factory=SessionLocal, rss_feeds: Optional[List[str]] = None):
        self.session_factory = session_factory
        if rss_feeds:
            self.rss_feeds = rss_feeds
        elif settings.NEWS_RSS_FEEDS:
            self.rss_feeds = [url.strip() for url in settings.NEWS_RSS_FEEDS.split(",")]
        else:
            self.rss_feeds = []

    def fetch_rss(self, feed_url: str) -> List[NewsItemIn]:
        """
        Fetches items from a single RSS feed.
        """
        logger.info(f"Fetching RSS feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        items = []
        source = feed.feed.get('title', feed_url)
        
        for entry in feed.entries:
            published_ts = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_ts = datetime.fromtimestamp(mktime(entry.published_parsed))
            
            item = NewsItemIn(
                source=source,
                title=entry.get('title', 'No Title'),
                summary=entry.get('summary', entry.get('description', '')),
                url=entry.get('link', ''),
                published_ts=published_ts
            )
            if item.url:
                items.append(item)
                
        return items

    def ingest_from_feeds(self) -> int:
        """
        Fetches all configured feeds and stores new items in DB.
        """
        total_new = 0
        now = datetime.utcnow()
        
        for url in self.rss_feeds:
            try:
                items = self.fetch_rss(url)
                logger.debug(f"Fetched {len(items)} items from {url}")
                
                with self.session_factory() as session:
                    new_in_feed = 0
                    for item in items:
                        # Check if URL exists (idempotency)
                        exists = session.query(NewsItem).filter(NewsItem.url == item.url).first()
                        if not exists:
                            db_item = NewsItem(
                                **item.model_dump(),
                                ingested_ts=now
                            )
                            session.add(db_item)
                            new_in_feed += 1
                    
                    session.commit()
                    total_new += new_in_feed
                    logger.info(f"Ingested {new_in_feed} new items from {url}")
                    
            except Exception as e:
                logger.error(f"Failed to ingest from {url}: {e}")
                
        return total_new
