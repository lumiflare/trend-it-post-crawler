"""
Scraper Agent - Collects articles from configured sources.
"""
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import yaml

from ..models.article import RawArticle, now_jst
from ..skills.scraping_skills import ScrapingSkills
from ..utils.logger import log
from config.settings import settings


class ScraperAgent:
    """
    Scraper Agent responsible for collecting articles from various sources.

    Skills:
    - Playwright (dynamic content)
    - BeautifulSoup (static content)
    - FeedParser (RSS feeds)
    """

    def __init__(self, sources_config_path: str = "config/sources.yaml"):
        self.sources_config_path = Path(sources_config_path)
        self.sources = self._load_sources_config()
        self.scraping_skills = ScrapingSkills()

    def _load_sources_config(self) -> List[Dict[str, Any]]:
        """
        Load sources configuration from YAML file.

        Returns:
            List of source configuration dicts
        """
        try:
            with open(self.sources_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                sources = config.get("sources", [])
                log.info(f"Loaded {len(sources)} sources from configuration")
                return sources
        except Exception as e:
            log.error(f"Failed to load sources configuration: {e}")
            return []

    async def collect_from_source(self, source_config: Dict[str, Any]) -> List[RawArticle]:
        """
        Collect articles from a single source.

        Args:
            source_config: Source configuration dict

        Returns:
            List of RawArticle objects
        """
        source_name = source_config.get("name", "Unknown")

        try:
            log.info(f"Starting collection from source: {source_name}")
            articles = await self.scraping_skills.scrape_source(source_config)
            log.info(f"Collected {len(articles)} articles from {source_name}")
            return articles

        except Exception as e:
            log.error(f"Error collecting from {source_name}: {e}")
            return []

    async def collect_all(self, max_concurrent: int = None) -> List[RawArticle]:
        """
        Collect articles from all configured sources concurrently.

        Args:
            max_concurrent: Maximum concurrent scraping tasks (defaults to settings)

        Returns:
            List of all collected RawArticle objects
        """
        if max_concurrent is None:
            max_concurrent = settings.max_concurrent_scrapes

        log.info(f"Starting collection from {len(self.sources)} sources (max concurrent: {max_concurrent})")

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def collect_with_semaphore(source_config: Dict[str, Any]) -> List[RawArticle]:
            async with semaphore:
                return await self.collect_from_source(source_config)

        # Collect from all sources concurrently
        results = await asyncio.gather(
            *[collect_with_semaphore(source) for source in self.sources],
            return_exceptions=True
        )

        # Flatten results and filter out errors
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                log.error(f"Source collection failed with exception: {result}")

        # Filter articles by published date (last 24 hours)
        cutoff_time = now_jst() - timedelta(hours=settings.hours_lookback)
        filtered_articles = []

        for article in all_articles:
            if article.published_at is None:
                # If no published date, include the article (e.g., from RSS feeds without dates)
                filtered_articles.append(article)
            elif article.published_at >= cutoff_time:
                # Include articles published within the last 24 hours
                filtered_articles.append(article)
            else:
                log.debug(f"Filtered out old article: {article.title} (published: {article.published_at})")

        log.info(
            f"Total articles collected: {len(all_articles)}, "
            f"After 24h filter: {len(filtered_articles)} "
            f"(cutoff: {cutoff_time.strftime('%Y-%m-%d %H:%M %Z')})"
        )
        return filtered_articles

    async def run(self) -> List[RawArticle]:
        """
        Run the scraper agent to collect all articles.

        Returns:
            List of collected RawArticle objects
        """
        log.info("Scraper Agent started")
        articles = await self.collect_all()
        log.info(f"Scraper Agent completed. Collected {len(articles)} articles")
        return articles

    async def close(self):
        """Clean up resources."""
        await self.scraping_skills.close()
