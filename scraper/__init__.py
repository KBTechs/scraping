"""
robots.txt を尊重し、サイトに負荷をかけないスクレイピングツール
"""

from scraper.core import (
    can_fetch,
    fetch_page,
    scrape_url,
    ScraperError,
    RobotsDisallowedError,
)

__all__ = [
    "can_fetch",
    "fetch_page",
    "scrape_url",
    "ScraperError",
    "RobotsDisallowedError",
]
