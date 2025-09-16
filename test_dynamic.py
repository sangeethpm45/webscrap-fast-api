#!/usr/bin/env python3
"""
Test script for the dynamic web scraper
"""
import asyncio
import httpx
import json

async def test_dynamic_scraper():
    """Test the dynamic scraper with different examples"""
    
    # Test 1: Scrape Yahoo Finance (same as before but with dynamic selectors)
    yahoo_request = {
        "url": "https://finance.yahoo.com/quote/AAPL?p=AAPL",
        "selectors": [
            {
                "name": "price",
                "selector": "[data-testid='qsp-price']",
                "is_xpath": False
            },
            {
                "name": "company_name",
                "selector": "h1",
                "is_xpath": False
            },
            {
                "name": "change",
                "selector": "[data-testid='qsp-price-change']",
                "is_xpath": False
            }
        ],
        "max_retries": 3
    }
    
    # Test 2: Scrape a news website
    news_request = {
        "url": "https://example.com",  # Replace with actual news site
        "selectors": [
            {
                "name": "headlines",
                "selector": "h1, h2, h3",
                "is_xpath": False
            },
            {
                "name": "links",
                "selector": "a",
                "attribute": "href",
                "is_xpath": False
            }
        ],
        "max_retries": 2
    }
    
    # Test 3: Scrape with webhook
    webhook_request = {
        "url": "https://finance.yahoo.com/quote/TSLA?p=TSLA",
        "selectors": [
            {
                "name": "price",
                "selector": "[data-testid='qsp-price']",
                "is_xpath": False
            }
        ],
        "webhook": "https://httpbin.org/post",  # Test webhook endpoint
        "max_retries": 2
    }
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Dynamic Web Scraper")
        print("=" * 50)
        
        # Test 1: Yahoo Finance
        print("\n1️⃣ Testing Yahoo Finance scraping...")
        try:
            response = await client.post(
                "http://localhost:8000/scrape",
                json=yahoo_request,
                timeout=30.0
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success: {result['success']}")
                if result.get('data'):
                    print(f"📊 Price: {result['data'].get('price')}")
                    print(f"🏢 Company: {result['data'].get('company_name')}")
                    print(f"📈 Change: {result['data'].get('change')}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        # Test 2: Webhook functionality
        print("\n2️⃣ Testing webhook functionality...")
        try:
            response = await client.post(
                "http://localhost:8000/scrape",
                json=webhook_request,
                timeout=30.0
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success: {result['success']}")
                print(f"🔗 Webhook: {result.get('webhook')}")
                print(f"🆔 Task ID: {result.get('task_id')}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print("\n🎉 Dynamic scraper testing completed!")

if __name__ == "__main__":
    asyncio.run(test_dynamic_scraper())
