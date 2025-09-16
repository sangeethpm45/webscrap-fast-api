# models.py
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, HttpUrl


class ScrapeSelector(BaseModel):
    """Individual selector configuration"""
    name: str  # Key name for the extracted data
    selector: str  # CSS or XPath selector
    attribute: Optional[str] = None  # Optional attribute to extract (e.g., 'href', 'src')
    is_xpath: bool = False  # True if selector is XPath, False for CSS


class AIExtractionConfig(BaseModel):
    """AI-powered content extraction configuration"""
    extract_entities: bool = False  # Extract named entities (people, places, etc.)
    extract_sentiment: bool = False  # Analyze sentiment
    extract_keywords: bool = False  # Extract key topics/keywords
    extract_summary: bool = False  # Generate content summary
    custom_prompt: Optional[str] = None  # Custom extraction prompt


class ScrapeRequest(BaseModel):
    """Request model for dynamic scraping with multiple extraction methods"""
    url: HttpUrl  # Target URL to scrape
    selectors: Optional[List[ScrapeSelector]] = None  # List of selectors to extract data
    ai_extraction: Optional[AIExtractionConfig] = None  # AI-powered extraction
    extract_structured_data: bool = False  # Extract JSON-LD, microdata, etc.
    extract_links: bool = False  # Extract all links
    extract_images: bool = False  # Extract all images
    extract_text: bool = False  # Extract clean text content
    webhook: Optional[HttpUrl] = None  # Optional webhook URL
    cache_key: Optional[str] = None  # Optional custom cache key
    max_retries: int = 3  # Number of retry attempts


class ScrapeResponse(BaseModel):
    """Response model for scraping results"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    webhook: Optional[str] = None
    task_id: Optional[int] = None
    scraped_on: Optional[float] = None
