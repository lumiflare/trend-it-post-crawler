"""
Retry utilities using tenacity.
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from .logger import log
import httpx
from playwright.async_api import TimeoutError as PlaywrightTimeout


def create_retry_decorator(max_attempts: int = 3, wait_min: int = 1, wait_max: int = 10):
    """
    Create a retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_min: Minimum wait time in seconds
        wait_max: Maximum wait time in seconds

    Returns:
        Configured retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=wait_min, max=wait_max),
        retry=retry_if_exception_type((httpx.HTTPError, PlaywrightTimeout, ConnectionError)),
        before_sleep=before_sleep_log(log, "WARNING"),
        reraise=True,
    )


# Default retry decorator for scraping operations
scraping_retry = create_retry_decorator(max_attempts=3, wait_min=2, wait_max=10)

# Retry decorator for API calls
api_retry = create_retry_decorator(max_attempts=3, wait_min=1, wait_max=5)
