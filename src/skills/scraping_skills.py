"""
Scraping skills for collecting articles from various sources.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import asyncio
import feedparser
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser
from urllib.parse import urljoin

from ..models.article import RawArticle
from ..utils.logger import log
from ..utils.retry import scraping_retry
from config.settings import settings


class ScrapingSkills:
    """Collection of scraping skills for different content types."""

    def __init__(self):
        self.timeout = settings.scraping_timeout * 1000  # Convert to milliseconds
        self.user_agent = settings.user_agent
        self._browser: Optional[Browser] = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close browser if open."""
        if self._browser:
            await self._browser.close()
            self._browser = None

    @scraping_retry
    async def scrape_with_playwright(
        self,
        source_config: Dict[str, Any]
    ) -> List[RawArticle]:
        """
        Scrape articles using Playwright (for dynamic content).

        Args:
            source_config: Source configuration dict

        Returns:
            List of RawArticle objects
        """
        articles = []
        source_name = source_config["name"]
        url = source_config["url"]
        selectors = source_config.get("selectors", {})
        max_articles = source_config.get("max_articles", 10)

        log.info(f"Starting Playwright scraping for {source_name}: {url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=self.user_agent)

                await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                await asyncio.sleep(5)  # Wait longer for dynamic React content

                # Try to find any links first to debug
                all_links = await page.query_selector_all("a")
                log.debug(f"Total links on page: {len(all_links)}")

                # Extract articles
                article_list_selector = selectors.get("article_list", "article")
                article_elements = await page.query_selector_all(article_list_selector)

                log.info(f"Found {len(article_elements)} article elements using selector: '{article_list_selector}'")

                # If no articles found, try alternative selector: find all links containing /items/ or /articles/
                if len(article_elements) == 0:
                    log.warning(f"No articles found with selector '{article_list_selector}', trying direct link search")
                    link_selector = selectors.get("article_link", "a")
                    article_elements = await page.query_selector_all(link_selector)
                    log.info(f"Found {len(article_elements)} elements with link selector: '{link_selector}'")

                for element in article_elements[:max_articles]:
                    try:
                        # If element is already a link (when using direct link search)
                        if await element.evaluate("el => el.tagName") == "A":
                            link_element = element
                            article_url = await link_element.get_attribute("href")
                            if not article_url:
                                continue

                            # Make URL absolute
                            article_url = urljoin(url, article_url)

                            # Try to get title from link text or find nearby title
                            title = await link_element.inner_text()
                            if not title or len(title.strip()) == 0:
                                # Try to find title in parent elements
                                parent = await element.evaluate_handle("el => el.parentElement")
                                title_element = await parent.query_selector(selectors.get("article_title", "h2, h3"))
                                title = await title_element.inner_text() if title_element else "No Title"
                            title = title.strip()
                        else:
                            # Original logic: element is article container
                            link_element = await element.query_selector(
                                selectors.get("article_link", "a")
                            )
                            if not link_element:
                                continue

                            article_url = await link_element.get_attribute("href")
                            if not article_url:
                                continue

                            # Make URL absolute
                            article_url = urljoin(url, article_url)

                            # Extract title
                            title_element = await element.query_selector(
                                selectors.get("article_title", "h2, h3")
                            )
                            title = await title_element.inner_text() if title_element else "No Title"
                            title = title.strip()

                        articles.append(
                            RawArticle(
                                source=source_name,
                                url=article_url,
                                title=title,
                                collected_at=datetime.now()
                            )
                        )

                    except Exception as e:
                        log.warning(f"Error extracting article from {source_name}: {e}")
                        continue

                await browser.close()

            log.info(f"Collected {len(articles)} articles from {source_name}")
            return articles

        except Exception as e:
            log.error(f"Playwright scraping failed for {source_name}: {e}")
            return []

    @scraping_retry
    async def scrape_with_requests(
        self,
        source_config: Dict[str, Any]
    ) -> List[RawArticle]:
        """
        Scrape articles using httpx + BeautifulSoup (for static content).

        Args:
            source_config: Source configuration dict

        Returns:
            List of RawArticle objects
        """
        articles = []
        source_name = source_config["name"]
        url = source_config["url"]
        selectors = source_config.get("selectors", {})
        max_articles = source_config.get("max_articles", 10)

        log.info(f"Starting static scraping for {source_name}: {url}")

        try:
            async with httpx.AsyncClient(timeout=settings.scraping_timeout) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                # Find article elements
                article_elements = soup.select(selectors.get("article_list", "article"))

                for element in article_elements[:max_articles]:
                    try:
                        # Extract link
                        link_element = element.select_one(selectors.get("article_link", "a"))
                        if not link_element or not link_element.get("href"):
                            continue

                        article_url = urljoin(url, link_element["href"])

                        # Extract title
                        title_element = element.select_one(
                            selectors.get("article_title", "h2, h3")
                        )
                        title = title_element.get_text(strip=True) if title_element else "No Title"

                        articles.append(
                            RawArticle(
                                source=source_name,
                                url=article_url,
                                title=title,
                                collected_at=datetime.now()
                            )
                        )

                    except Exception as e:
                        log.warning(f"Error extracting article from {source_name}: {e}")
                        continue

            log.info(f"Collected {len(articles)} articles from {source_name}")
            return articles

        except Exception as e:
            log.error(f"Static scraping failed for {source_name}: {e}")
            return []

    @scraping_retry
    async def scrape_rss_feed(
        self,
        source_config: Dict[str, Any]
    ) -> List[RawArticle]:
        """
        Scrape articles from RSS feed using feedparser.

        Args:
            source_config: Source configuration dict

        Returns:
            List of RawArticle objects
        """
        articles = []
        source_name = source_config["name"]
        url = source_config["url"]
        max_articles = source_config.get("max_articles", 10)

        log.info(f"Starting RSS scraping for {source_name}: {url}")

        try:
            # Run feedparser in thread pool (it's synchronous)
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)

            # Check if feed is valid
            if feed.bozo and not feed.entries:
                log.error(f"Invalid RSS feed for {source_name}: {feed.bozo_exception}")
                return []

            # Extract articles
            for entry in feed.entries[:max_articles]:
                try:
                    article_url = entry.get("link", "")
                    title = entry.get("title", "No Title")

                    # Parse published date (feedparser returns UTC time)
                    published_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                    # Get content/summary
                    content = None
                    if hasattr(entry, "content") and entry.content:
                        content = entry.content[0].get("value", "")
                    elif hasattr(entry, "summary"):
                        content = entry.summary

                    articles.append(
                        RawArticle(
                            source=source_name,
                            url=article_url,
                            title=title,
                            content=content,
                            published_at=published_at,
                            collected_at=datetime.now()
                        )
                    )

                except Exception as e:
                    log.warning(f"Error extracting entry from {source_name}: {e}")
                    continue

            log.info(f"Collected {len(articles)} articles from {source_name}")
            return articles

        except Exception as e:
            log.error(f"RSS scraping failed for {source_name}: {e}")
            return []

    @scraping_retry
    async def scrape_qiita_api(
        self,
        source_config: Dict[str, Any]
    ) -> List[RawArticle]:
        """
        Scrape articles from Qiita API v2.

        Args:
            source_config: Source configuration dict

        Returns:
            List of RawArticle objects
        """
        articles = []
        source_name = source_config["name"]
        max_articles = source_config.get("max_articles", 20)

        # Qiita API v2 endpoint
        api_url = "https://qiita.com/api/v2/items"

        log.info(f"Starting Qiita API scraping for {source_name}")

        try:
            import httpx

            # API parameters
            params = {
                "page": 1,
                "per_page": min(max_articles, 100)  # API max is 100
            }

            # Optional: add query if specified in config
            if "query" in source_config:
                params["query"] = source_config["query"]

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(api_url, params=params)
                response.raise_for_status()

                items = response.json()

                for item in items[:max_articles]:
                    try:
                        # Parse published date (ISO8601 format)
                        published_at = None
                        if "created_at" in item:
                            published_at = datetime.fromisoformat(
                                item["created_at"].replace("Z", "+00:00")
                            )

                        articles.append(
                            RawArticle(
                                source=source_name,
                                url=item.get("url", ""),
                                title=item.get("title", "No Title"),
                                content=None,  # API doesn't return full content in list
                                published_at=published_at,
                                collected_at=datetime.now()
                            )
                        )

                    except Exception as e:
                        log.warning(f"Error extracting item from Qiita API: {e}")
                        continue

            log.info(f"Collected {len(articles)} articles from {source_name}")
            return articles

        except Exception as e:
            log.error(f"Qiita API scraping failed for {source_name}: {e}")
            return []

    async def scrape_source(self, source_config: Dict[str, Any]) -> List[RawArticle]:
        """
        Scrape a single source based on its configuration.

        Args:
            source_config: Source configuration dict

        Returns:
            List of RawArticle objects
        """
        if not source_config.get("enabled", True):
            log.info(f"Skipping disabled source: {source_config['name']}")
            return []

        method = source_config.get("method", "requests").lower()
        source_type = source_config.get("type", "html").lower()

        if source_type == "api" or method == "qiita_api":
            return await self.scrape_qiita_api(source_config)
        elif source_type == "rss" or method == "feedparser":
            return await self.scrape_rss_feed(source_config)
        elif method == "playwright":
            return await self.scrape_with_playwright(source_config)
        else:
            return await self.scrape_with_requests(source_config)
