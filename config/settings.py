"""
Configuration settings for the Trend IT Post Crawler.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Settings
    anthropic_api_key: str
    model_name: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Notion Settings
    notion_api_key: str
    notion_parent_page_id: str

    # Scraping Settings
    scraping_timeout: int = 30  # seconds
    max_concurrent_scrapes: int = 5
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    # Retry Settings
    max_retry_attempts: int = 3
    retry_wait_seconds: int = 2

    # Output Settings
    output_dir: str = "output"
    output_format: str = "markdown"

    # Time Settings
    hours_lookback: int = 24  # 過去24時間以内の記事を対象


# Singleton instance
settings = Settings()
