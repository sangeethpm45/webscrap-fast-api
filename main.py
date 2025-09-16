# main.py
import asyncio
from fastapi import FastAPI
from loguru import logger as log
from time import time

from config import STOCK_CACHE, CACHE_TIME, ACTIVE_TASKS
from routes import router

# Create API app object
app = FastAPI(title="Advanced Web Scraper API", version="2.0.0")

# Include all routes
app.include_router(router)

# Startup and shutdown event handlers
@app.on_event("startup")
async def app_startup():
    log.info("Starting web scraper API with crawl4ai")
    # Clear expired cache every minute to prevent memory build up
    async def clear_expired_cache(period=60.0):
        while True:
            global STOCK_CACHE
            log.debug(f"clearing expired cache")
            STOCK_CACHE = {
                k: v for k, v in STOCK_CACHE.items() if time() - CACHE_TIME < v["_scraped_on"]
            }
            await asyncio.sleep(period)
    clear_cache_task = asyncio.create_task(clear_expired_cache())


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
