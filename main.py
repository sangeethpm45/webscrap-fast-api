# main.py
from fastapi import FastAPI
from loguru import logger as log
from parsel import Selector
from time import time
import httpx
import asyncio
from typing import Optional

# Configure HTTP client with proper headers to avoid bot detection
stock_client = httpx.AsyncClient(
    headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    },
    timeout=30.0,
    follow_redirects=True
)
STOCK_CACHE = {}  # NEW: establish global cache storage
CACHE_TIME = 60  # NEW: define how long do we want to keep cache in seconds

# create API app object
app = FastAPI()

async def scrape_yahoo_finance(symbol, max_retries=3):
    """scrapes stock data from yahoo finance with retry logic"""
    # NEW: check cache before we commit to scraping
    cache = STOCK_CACHE.get(symbol)
    if cache and time() - CACHE_TIME < cache["_scraped_on"]:
        log.debug(f"{symbol}: returning cached item")
        return cache

    log.info(f"{symbol}: scraping data")
    
    for attempt in range(max_retries):
        try:
            response = await stock_client.get(
                f"https://finance.yahoo.com/quote/{symbol}?p={symbol}"
            )
            
            # Check if we got blocked
            if response.status_code == 429:
                log.warning(f"{symbol}: Rate limited (429), attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            
            # Check for other HTTP errors
            response.raise_for_status()
            
            # Check if response contains error message
            if "Too Many Requests" in response.text or "Edge: Too Many Requests" in response.text:
                log.warning(f"{symbol}: Detected rate limiting in response, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise Exception("Rate limited by server")
            
            sel = Selector(response.text)
            parsed = {}
            
            # Check if we got valid content - look for price or summary data
            has_price = sel.css('[data-testid="qsp-price"]::text').get()
            has_summary = sel.xpath('//div[re:test(@data-test,"(left|right)-summary-table")]//td[@data-test]')
            
            if not has_price and not has_summary:
                log.warning(f"{symbol}: No price or summary data found in response, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    raise Exception("No stock data found in response")
            
            rows = sel.xpath('//div[re:test(@data-test,"(left|right)-summary-table")]//td[@data-test]')
            for row in rows:
                label = row.xpath("@data-test").get().split("-value")[0].lower()
                value = " ".join(row.xpath(".//text()").getall())
                parsed[label] = value
                
            # Try multiple ways to get the price
            # Method 1: Look for the main price display
            price = sel.css('[data-testid="qsp-price"]::text').get()
            if not price:
                # Method 2: Look for fin-streamer with regularMarketPrice
                price = sel.css(f'fin-streamer[data-field="regularMarketPrice"][data-symbol="{symbol}"]::attr(data-value)').get()
            if not price:
                # Method 3: Look for fin-streamer text content
                price = sel.css(f'fin-streamer[data-field="regularMarketPrice"][data-symbol="{symbol}"]::text').get()
            if not price:
                # Method 4: Look for any price element in the main quote area
                price = sel.css('.price::text').get()
            if not price:
                # Method 5: Fallback to any fin-streamer with the symbol
                price_elements = sel.css(f'fin-streamer[data-symbol="{symbol}"]')
                for elem in price_elements:
                    data_field = elem.css('::attr(data-field)').get()
                    if data_field and 'price' in data_field.lower():
                        price = elem.css('::attr(data-value)').get() or elem.css('::text').get()
                        if price:
                            break
            
            # Clean up the price (remove extra spaces)
            if price:
                price = price.strip()
            
            parsed["price"] = price
            parsed["_scraped_on"] = time()
            
            # NEW: store successful results to cache
            STOCK_CACHE[symbol] = parsed
            log.info(f"{symbol}: Successfully scraped data")
            return parsed
            
        except httpx.HTTPStatusError as e:
            log.error(f"{symbol}: HTTP error {e.response.status_code}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise
        except Exception as e:
            log.error(f"{symbol}: Error {str(e)}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise


# NEW: add webhook functionality
async def with_webhook(cor, webhook, retries=3):
    """execute corotine and send it to a webhook"""
    result = await cor
    async with httpx.AsyncClient(
        headers={"User-Agent": "scraper webhook"},
        timeout=httpx.Timeout(timeout=15.0),
    ) as client:
        for i in range(retries):
            try:
                response = await client.post(webhook, json=result)
                return
            except Exception as e:
                log.exception(f"Failed to send a webhook {i}/{retries}")
            await asyncio.sleep(5)  # wait between retries
        log.error(f"Failed to reach webhook in {retries} retries")

# attach route to our API app
@app.get("/scrape/stock/{symbol}")
async def scrape_stock(symbol: str, webhook: Optional[str] = None):
    symbol = symbol.upper()
    scrape_cor = scrape_yahoo_finance(symbol)
    if webhook:
        # run scrape coroutine in the background
        task = asyncio.create_task(with_webhook(scrape_cor, webhook))
        return {"success": True, "webhook": webhook}
    else:
        return await scrape_cor

# on API start - open up our scraper's http client connections
@app.on_event("startup")
async def app_startup():
    await stock_client.__aenter__()
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

# on API close - close our scraper's http client connections
@app.on_event("shutdown")
async def app_shutdown():
    await stock_client.__aexit__()