# config.py
from typing import Set
import asyncio
from time import time

# Global cache and task management
STOCK_CACHE = {}  # Global cache storage
CACHE_TIME = 60  # Cache duration in seconds
ACTIVE_TASKS: Set[asyncio.Task] = set()  # Track active webhook tasks

# Default crawl4ai configuration
DEFAULT_CRAWLER_CONFIG = {
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "delay_before_return_html": 3.0,
    "page_timeout": 60000,  # 60 seconds max
    "remove_overlay_elements": True,
    "simulate_user": False,
    "verbose": True,
}

# Fast crawler configuration for speed-optimized endpoints
FAST_CRAWLER_CONFIG = {
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "delay_before_return_html": 2.0,
    "page_timeout": 30000,  # 30 seconds max
    "remove_overlay_elements": True,
    "simulate_user": False,
    "verbose": False,
}
