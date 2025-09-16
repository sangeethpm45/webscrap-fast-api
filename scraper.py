# scraper.py
import asyncio
import httpx
from time import time
from typing import Dict, Any, Optional
from loguru import logger as log
from fastapi import HTTPException

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from bs4 import BeautifulSoup
from lxml import html

from models import ScrapeRequest
from config import STOCK_CACHE, CACHE_TIME, DEFAULT_CRAWLER_CONFIG, FAST_CRAWLER_CONFIG


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
            # Create crawl4ai configuration
            config = CrawlerRunConfig(
                user_agent=DEFAULT_CRAWLER_CONFIG["user_agent"],
                delay_before_return_html=DEFAULT_CRAWLER_CONFIG["delay_before_return_html"],
                cache_mode=CacheMode.BYPASS,
                page_timeout=DEFAULT_CRAWLER_CONFIG["page_timeout"],
                remove_overlay_elements=DEFAULT_CRAWLER_CONFIG["remove_overlay_elements"],
                simulate_user=DEFAULT_CRAWLER_CONFIG["simulate_user"],
                verbose=DEFAULT_CRAWLER_CONFIG["verbose"],
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
                
                parsed_data = await _extract_data_from_result(result, request)
                
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


async def scrape_fast(url: str, extract_basic: bool = True) -> Dict[str, Any]:
    """Fast scraping with minimal features for speed optimization"""
    try:
        # Use fast configuration
        config = CrawlerRunConfig(
            user_agent=FAST_CRAWLER_CONFIG["user_agent"],
            delay_before_return_html=FAST_CRAWLER_CONFIG["delay_before_return_html"],
            cache_mode=CacheMode.BYPASS,
            page_timeout=FAST_CRAWLER_CONFIG["page_timeout"],
            remove_overlay_elements=FAST_CRAWLER_CONFIG["remove_overlay_elements"],
            simulate_user=FAST_CRAWLER_CONFIG["simulate_user"],
            verbose=FAST_CRAWLER_CONFIG["verbose"],
        )
        
        # Direct crawl4ai call for speed
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail=f"crawl4ai failed: {result.error_message}")
            
            # Basic extraction
            parsed_data = {}
            if extract_basic:
                parsed_data["html"] = result.html[:1000] + "..." if len(result.html) > 1000 else result.html
                parsed_data["title"] = result.title if hasattr(result, 'title') else None
                parsed_data["url"] = result.url if hasattr(result, 'url') else url
            
            parsed_data["_scraped_on"] = time()
            parsed_data["_crawl4ai_used"] = True
            parsed_data["_fast_mode"] = True
            
            return parsed_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fast scraping failed: {str(e)}")


async def _extract_data_from_result(result, request: ScrapeRequest) -> Dict[str, Any]:
    """Extract data from crawl4ai result based on request configuration"""
    parsed_data = {}
    
    # 1. Extract using custom selectors (if provided)
    if request.selectors:
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
                entities = result.entities if hasattr(result, 'entities') else []
                ai_data["entities"] = entities
            
            if request.ai_extraction.extract_sentiment:
                sentiment = result.sentiment if hasattr(result, 'sentiment') else None
                ai_data["sentiment"] = sentiment
            
            if request.ai_extraction.extract_keywords:
                keywords = result.keywords if hasattr(result, 'keywords') else []
                ai_data["keywords"] = keywords
            
            if request.ai_extraction.extract_summary:
                summary = result.summary if hasattr(result, 'summary') else None
                ai_data["summary"] = summary
            
            if request.ai_extraction.custom_prompt:
                # Custom AI extraction using the prompt
                config = CrawlerRunConfig(
                    user_agent=DEFAULT_CRAWLER_CONFIG["user_agent"],
                    delay_before_return_html=DEFAULT_CRAWLER_CONFIG["delay_before_return_html"],
                    cache_mode=CacheMode.BYPASS,
                    page_timeout=DEFAULT_CRAWLER_CONFIG["page_timeout"],
                    remove_overlay_elements=DEFAULT_CRAWLER_CONFIG["remove_overlay_elements"],
                    simulate_user=DEFAULT_CRAWLER_CONFIG["simulate_user"],
                    verbose=DEFAULT_CRAWLER_CONFIG["verbose"],
                )
                async with AsyncWebCrawler(verbose=True) as crawler:
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
    
    return parsed_data


async def with_webhook(scrape_request: ScrapeRequest, retries=3):
    """Execute scraping and send result to webhook"""
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
