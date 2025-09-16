# routes.py
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException
from loguru import logger as log

from models import ScrapeRequest, ScrapeResponse, AIExtractionConfig
from scraper import scrape_dynamic, scrape_fast, with_webhook
from config import ACTIVE_TASKS

# Create router for all scraping endpoints
router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
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


@router.post("/scrape/simple")
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


@router.post("/scrape/fast")
async def scrape_fast_endpoint(url: str, extract_basic: bool = True):
    """Fast scraping endpoint - optimized for speed with minimal features"""
    try:
        result = await scrape_fast(url, extract_basic)
        return {
            "success": True,
            "url": url,
            "data": result,
            "scraped_on": result["_scraped_on"],
            "speed_optimized": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
