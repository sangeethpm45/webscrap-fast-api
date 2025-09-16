# main.py
from fastapi import FastAPI, HTTPException
from loguru import logger as log
from time import time
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, HttpUrl
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

# Note: httpx client is now only used for webhook calls, not for scraping
# crawl4ai handles all web scraping with its own browser automation
STOCK_CACHE = {}  # NEW: establish global cache storage
CACHE_TIME = 60  # NEW: define how long do we want to keep cache in seconds
ACTIVE_TASKS = set()  # NEW: track active webhook tasks

# Pydantic models for dynamic scraping
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

# create API app object
app = FastAPI()

async def scrape_dynamic(request: ScrapeRequest) -> Dict[str, Any]:
    """Advanced web scraper with multiple extraction methods using crawl4ai"""
    # Generate cache key
    cache_key = request.cache_key or f"{request.url}_{hash(str(request.dict()))}"
    
    # Check cache first
    cache = STOCK_CACHE.get(cache_key)
    if cache and time() - CACHE_TIME < cache["_scraped_on"]:
        log.debug(f"Cache hit for {cache_key}")
        return cache

    log.info(f"Scraping {request.url} using crawl4ai with multiple extraction methods")
    
    for attempt in range(request.max_retries):
        try:
            # Create crawl4ai configuration with minimal settings
            config = CrawlerRunConfig(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                # Remove wait_for to avoid timeout issues
                delay_before_return_html=3.0,  # Give time for page to load
                cache_mode=CacheMode.BYPASS,
                # Conservative settings for reliability
                page_timeout=60000,  # 60 seconds max
                remove_overlay_elements=True,  # Remove overlays
                simulate_user=False,  # Skip user simulation for speed
                verbose=True,  # Enable logging to debug
            )
            
            # Use crawl4ai to scrape the page
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(url=str(request.url), config=config)
                
                if not result.success:
                    log.warning(f"crawl4ai failed: {result.error_message}, attempt {attempt + 1}/{request.max_retries}")
                    if attempt < request.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        raise HTTPException(status_code=500, detail=f"crawl4ai failed: {result.error_message}")
                
                parsed_data = {}
                
                # 1. Extract using custom selectors (if provided)
                if request.selectors:
                    from bs4 import BeautifulSoup
                    from lxml import html
                    soup = BeautifulSoup(result.html, 'html.parser')
                    
                    for selector_config in request.selectors:
                        try:
                            if selector_config.is_xpath:
                                # XPath extraction
                                tree = html.fromstring(result.html)
                                elements = tree.xpath(selector_config.selector)
                                
                                if elements:
                                    if selector_config.attribute:
                                        values = [elem.get(selector_config.attribute) for elem in elements if elem.get(selector_config.attribute)]
                                        parsed_data[selector_config.name] = values
                                    else:
                                        values = [elem.text_content().strip() for elem in elements if elem.text_content()]
                                        parsed_data[selector_config.name] = [v for v in values if v]
                                else:
                                    parsed_data[selector_config.name] = None
                            else:
                                # CSS selector extraction
                                elements = soup.select(selector_config.selector)
                                
                                if elements:
                                    if selector_config.attribute:
                                        values = [elem.get(selector_config.attribute) for elem in elements if elem.get(selector_config.attribute)]
                                        parsed_data[selector_config.name] = values
                                    else:
                                        values = [elem.get_text(strip=True) for elem in elements]
                                        parsed_data[selector_config.name] = [v for v in values if v]
                                else:
                                    parsed_data[selector_config.name] = None
                                    
                        except Exception as e:
                            log.warning(f"Failed to extract {selector_config.name}: {e}")
                            parsed_data[selector_config.name] = None
                
                # 2. Extract structured data (JSON-LD, microdata, etc.)
                if request.extract_structured_data:
                    try:
                        structured_data = result.structured_data if hasattr(result, 'structured_data') else {}
                        parsed_data["structured_data"] = structured_data
                    except Exception as e:
                        log.warning(f"Failed to extract structured data: {e}")
                        parsed_data["structured_data"] = None
                
                # 3. Extract links
                if request.extract_links:
                    try:
                        links = result.links if hasattr(result, 'links') else []
                        parsed_data["links"] = links
                    except Exception as e:
                        log.warning(f"Failed to extract links: {e}")
                        parsed_data["links"] = None
                
                # 4. Extract images
                if request.extract_images:
                    try:
                        images = result.images if hasattr(result, 'images') else []
                        parsed_data["images"] = images
                    except Exception as e:
                        log.warning(f"Failed to extract images: {e}")
                        parsed_data["images"] = None
                
                # 5. Extract clean text
                if request.extract_text:
                    try:
                        clean_text = result.cleaned_html if hasattr(result, 'cleaned_html') else result.html
                        parsed_data["clean_text"] = clean_text
                    except Exception as e:
                        log.warning(f"Failed to extract clean text: {e}")
                        parsed_data["clean_text"] = None
                
                # 6. AI-powered extraction
                if request.ai_extraction:
                    try:
                        ai_data = {}
                        
                        if request.ai_extraction.extract_entities:
                            # Extract named entities using crawl4ai's built-in capabilities
                            entities = result.entities if hasattr(result, 'entities') else []
                            ai_data["entities"] = entities
                        
                        if request.ai_extraction.extract_sentiment:
                            # Sentiment analysis
                            sentiment = result.sentiment if hasattr(result, 'sentiment') else None
                            ai_data["sentiment"] = sentiment
                        
                        if request.ai_extraction.extract_keywords:
                            # Keyword extraction
                            keywords = result.keywords if hasattr(result, 'keywords') else []
                            ai_data["keywords"] = keywords
                        
                        if request.ai_extraction.extract_summary:
                            # Content summary
                            summary = result.summary if hasattr(result, 'summary') else None
                            ai_data["summary"] = summary
                        
                        if request.ai_extraction.custom_prompt:
                            # Custom AI extraction using the prompt
                            custom_result = await crawler.arun(
                                url=str(request.url), 
                                config=config,
                                extraction_strategy=request.ai_extraction.custom_prompt
                            )
                            ai_data["custom_extraction"] = custom_result.extracted_content if hasattr(custom_result, 'extracted_content') else None
                        
                        parsed_data["ai_extraction"] = ai_data
                        
                    except Exception as e:
                        log.warning(f"Failed AI extraction: {e}")
                        parsed_data["ai_extraction"] = {"error": str(e)}
                
                # Add metadata
                parsed_data["_scraped_on"] = time()
                parsed_data["_url"] = str(request.url)
                parsed_data["_crawl4ai_used"] = True
                
                # Store in cache
                STOCK_CACHE[cache_key] = parsed_data
                log.info(f"Successfully scraped {request.url} using crawl4ai with advanced extraction")
                return parsed_data
                
        except Exception as e:
            log.error(f"Error {str(e)}, attempt {attempt + 1}/{request.max_retries}")
            if attempt < request.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")



# NEW: add webhook functionality
async def with_webhook(scrape_request: ScrapeRequest, retries=3):
    """execute scraping and send result to webhook"""
    try:
        result = await scrape_dynamic(scrape_request)
        async with httpx.AsyncClient(
            headers={"User-Agent": "scraper webhook"},
            timeout=httpx.Timeout(timeout=15.0),
        ) as client:
            for i in range(retries):
                try:
                    response = await client.post(str(scrape_request.webhook), json=result)
                    log.info(f"Webhook sent successfully to {scrape_request.webhook}")
                    return
                except Exception as e:
                    log.exception(f"Failed to send webhook {i}/{retries}: {e}")
                await asyncio.sleep(5)  # wait between retries
            log.error(f"Failed to reach webhook in {retries} retries")
    except Exception as e:
        log.error(f"Scraping failed for webhook: {e}")
        # Send error to webhook if possible
        if scrape_request.webhook:
            try:
                error_data = {"error": str(e), "url": str(scrape_request.url)}
                async with httpx.AsyncClient(timeout=15.0) as client:
                    await client.post(str(scrape_request.webhook), json=error_data)
            except:
                pass

# NEW: Advanced scraping endpoint with multiple extraction methods
@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_dynamic_endpoint(request: ScrapeRequest):
    """Advanced web scraper endpoint - multiple extraction methods with crawl4ai"""
    try:
        if request.webhook:
            # Run scraping in background and send to webhook
            task = asyncio.create_task(with_webhook(request))
            ACTIVE_TASKS.add(task)
            task.add_done_callback(ACTIVE_TASKS.discard)
            return ScrapeResponse(
                success=True,
                webhook=str(request.webhook),
                task_id=id(task)
            )
        else:
            # Direct scraping
            result = await scrape_dynamic(request)
            return ScrapeResponse(
                success=True,
                data=result,
                scraped_on=result.get("_scraped_on")
            )
    except HTTPException as e:
        return ScrapeResponse(
            success=False,
            error=e.detail
        )
    except Exception as e:
        return ScrapeResponse(
            success=False,
            error=f"Unexpected error: {str(e)}"
        )

# NEW: Simple scraping endpoint - no selectors needed!
@app.post("/scrape/simple")
async def scrape_simple(url: str, extract_all: bool = True):
    """Simple scraping endpoint - just provide a URL and get everything extracted"""
    try:
        request = ScrapeRequest(
            url=url,
            extract_structured_data=extract_all,
            extract_links=extract_all,
            extract_images=extract_all,
            extract_text=extract_all,
            ai_extraction=AIExtractionConfig(
                extract_entities=extract_all,
                extract_keywords=extract_all,
                extract_summary=extract_all
            ) if extract_all else None
        )
        
        result = await scrape_dynamic(request)
        return {
            "success": True,
            "url": url,
            "data": result,
            "scraped_on": result.get("_scraped_on")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# NEW: Fast scraping endpoint - optimized for speed
@app.post("/scrape/fast")
async def scrape_fast(url: str, extract_basic: bool = True):
    """Fast scraping endpoint - optimized for speed with minimal features"""
    try:
        # Use a faster configuration for the fast endpoint
        config = CrawlerRunConfig(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Remove wait_for to avoid timeout issues
            delay_before_return_html=2.0,  # Give time for page to load
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,  # 30 seconds max
            remove_overlay_elements=True,
            simulate_user=False,
            verbose=False,
        )
        
        # Direct crawl4ai call for speed
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config)
            
            if not result.success:
                return {
                    "success": False,
                    "error": f"crawl4ai failed: {result.error_message}"
                }
            
            # Basic extraction
            parsed_data = {}
            if extract_basic:
                parsed_data["html"] = result.html[:1000] + "..." if len(result.html) > 1000 else result.html
                parsed_data["title"] = result.title if hasattr(result, 'title') else None
                parsed_data["url"] = result.url if hasattr(result, 'url') else url
            
            parsed_data["_scraped_on"] = time()
            parsed_data["_crawl4ai_used"] = True
            parsed_data["_fast_mode"] = True
            
            return {
                "success": True,
                "url": url,
                "data": parsed_data,
                "scraped_on": parsed_data["_scraped_on"],
                "speed_optimized": True
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Legacy endpoint for Yahoo Finance (kept for backward compatibility)
@app.get("/scrape/stock/{symbol}")
async def scrape_stock(symbol: str, webhook: Optional[str] = None):
    """Legacy Yahoo Finance endpoint - now uses crawl4ai with specific selectors"""
    symbol = symbol.upper()
    url = f"https://finance.yahoo.com/quote/{symbol}?p={symbol}"
    
    # Create selectors for Yahoo Finance data
    selectors = [
        ScrapeSelector(name="price", selector='[data-testid="qsp-price"]', is_xpath=False),
        ScrapeSelector(name="previous_close", selector='//td[@data-test="PREV_CLOSE-value"]', is_xpath=True),
        ScrapeSelector(name="open", selector='//td[@data-test="OPEN-value"]', is_xpath=True),
        ScrapeSelector(name="volume", selector='//td[@data-test="TD_VOLUME-value"]', is_xpath=True),
        ScrapeSelector(name="market_cap", selector='//td[@data-test="MARKET_CAP-value"]', is_xpath=True),
    ]
    
    request = ScrapeRequest(
        url=url,
        selectors=selectors,
        webhook=webhook
    )
    
    if webhook:
        # run scrape coroutine in the background
        task = asyncio.create_task(with_webhook(request))
        # Store task reference to prevent garbage collection
        ACTIVE_TASKS.add(task)
        # Remove task from set when it completes
        task.add_done_callback(ACTIVE_TASKS.discard)
        return {"success": True, "webhook": webhook, "task_id": id(task)}
    else:
        result = await scrape_dynamic(request)
        return result

# on API start - initialize cache cleanup
@app.on_event("startup")
async def app_startup():
    log.info("Starting web scraper API with crawl4ai")
    # NEW: optionally we can clear expired cache every minute to prevent
    # memory build up. 
    async def clear_expired_cache(period=60.0):
        while True:
            global STOCK_CACHE
            log.debug(f"clearing expired cache")
            STOCK_CACHE = {
                k: v for k, v in STOCK_CACHE.items() if time() - CACHE_TIME < v["_scraped_on"]
            }
            await asyncio.sleep(period)
    clear_cache_task = asyncio.create_task(clear_expired_cache())

# on API close - cleanup tasks
@app.on_event("shutdown")
async def app_shutdown():
    log.info("Shutting down web scraper API")
    # Cancel all active webhook tasks
    for task in ACTIVE_TASKS:
        if not task.done():
            task.cancel()
    # Wait for tasks to complete
    if ACTIVE_TASKS:
        await asyncio.gather(*ACTIVE_TASKS, return_exceptions=True)