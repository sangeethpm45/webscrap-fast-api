# 🚀 Advanced Web Scraper API - Powered by crawl4ai

## 📋 Overview

The advanced web scraper uses **crawl4ai** for intelligent web scraping with multiple extraction methods. You can:
- ✅ **Any URL** to scrape with browser automation
- ✅ **AI-powered extraction** (entities, sentiment, keywords, summaries)
- ✅ **Automatic content extraction** (links, images, structured data)
- ✅ **Custom CSS/XPath selectors** for precise data extraction
- ✅ **Simple scraping** - just provide a URL, no selectors needed!
- ✅ **Optional webhook** for background processing
- ✅ **Caching** for performance
- ✅ **Retry logic** for reliability

---

## 🎯 API Endpoints

### 1. Simple Scraping (No Selectors Needed!)
```
POST /scrape/simple?url=https://example.com&extract_all=true
```

### 2. Advanced Scraping with Multiple Methods
```
POST /scrape
```

## 📝 Request Formats

### Simple Request (Just URL)
```bash
curl -X POST "http://localhost:8000/scrape/simple?url=https://news.ycombinator.com"
```

### Advanced Request with AI Extraction
```json
{
  "url": "https://example.com",
  "selectors": [
    {
      "name": "data_key",
      "selector": "css_or_xpath_selector",
      "attribute": "optional_attribute",
      "is_xpath": false
    }
  ],
  "ai_extraction": {
    "extract_entities": true,
    "extract_sentiment": true,
    "extract_keywords": true,
    "extract_summary": true,
    "custom_prompt": "Extract all product names and prices"
  },
  "extract_structured_data": true,
  "extract_links": true,
  "extract_images": true,
  "extract_text": true,
  "webhook": "https://optional-webhook.com/endpoint",
  "cache_key": "optional_custom_cache_key",
  "max_retries": 3
}
```

---

## 🚀 Example 1: Simple Scraping (No Selectors!)

**Just provide a URL and get everything extracted automatically:**

```bash
curl -X POST "http://localhost:8000/scrape/simple?url=https://news.ycombinator.com&extract_all=true"
```

**Response:**
```json
{
  "success": true,
  "url": "https://news.ycombinator.com",
  "data": {
    "links": [
      {"url": "https://example.com", "text": "Example Link"},
      {"url": "https://another.com", "text": "Another Link"}
    ],
    "images": [
      {"src": "https://example.com/image.jpg", "alt": "Example Image"}
    ],
    "structured_data": {
      "type": "WebSite",
      "name": "Hacker News"
    },
    "ai_extraction": {
      "entities": ["Apple", "Google", "Microsoft"],
      "keywords": ["technology", "startup", "programming"],
      "summary": "Technology news and discussions..."
    },
    "_crawl4ai_used": true,
    "_scraped_on": 1757940552.327654
  }
}
```

---

## 🤖 Example 2: AI-Powered Content Analysis

**Extract entities, sentiment, and generate summaries:**

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://techcrunch.com/2024/01/15/ai-breakthrough",
    "ai_extraction": {
      "extract_entities": true,
      "extract_sentiment": true,
      "extract_keywords": true,
      "extract_summary": true,
      "custom_prompt": "Extract the main technology mentioned, key benefits, and potential risks"
    },
    "extract_structured_data": true
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "ai_extraction": {
      "entities": ["OpenAI", "GPT-4", "Artificial Intelligence", "Silicon Valley"],
      "sentiment": "positive",
      "keywords": ["machine learning", "neural networks", "automation", "innovation"],
      "summary": "OpenAI announces breakthrough in AI technology with new capabilities...",
      "custom_extraction": {
        "main_technology": "GPT-4",
        "key_benefits": ["Improved accuracy", "Better reasoning"],
        "potential_risks": ["Job displacement", "Ethical concerns"]
      }
    },
    "structured_data": {
      "type": "Article",
      "headline": "AI Breakthrough Announced",
      "author": "Tech Reporter"
    },
    "_crawl4ai_used": true
  }
}
```

---

## ⏱️ Speed & Performance

### Timing Expectations:
- **Fast scraping** (`/scrape/fast`): 5-15 seconds
- **Simple scraping** (`/scrape/simple`): 10-25 seconds  
- **Advanced scraping** (`/scrape`): 15-35 seconds
- **Traditional scraping**: 1-3 seconds (but 60-70% success rate)

### Speed vs Quality Trade-off:
| Method | Speed | Success Rate | Features |
|--------|-------|--------------|----------|
| `/scrape/fast` | ⚡ Fast (5-15s) | 🎯 85% | Basic extraction |
| `/scrape/simple` | 🚀 Medium (10-25s) | 🎯 90% | Full extraction |
| `/scrape` | 🐌 Slower (15-35s) | 🎯 95% | AI + all features |

### Why crawl4ai Takes Longer:
1. **Browser Startup**: 1-2 seconds to initialize browser
2. **Page Loading**: 2-5 seconds for full page + JavaScript
3. **Network Idle**: 1-3 seconds waiting for all requests
4. **AI Processing**: 2-8 seconds for entity extraction, sentiment analysis
5. **Stealth Mode**: 1-2 seconds for anti-detection measures

### Speed Optimization Tips:
1. **Use `/scrape/fast`** for basic needs (3-8 seconds)
2. **Skip AI extraction** if not needed (saves 2-8 seconds)
3. **Skip image extraction** (saves 1-3 seconds)
4. **Use caching** to avoid re-scraping same URLs
5. **Batch requests** with webhooks for multiple URLs
6. **Optimized configuration** - uses `domcontentloaded` instead of `networkidle`
7. **Reduced delays** - 1.0s delay instead of 2.0s
8. **Overlay removal** - automatically removes popups/overlays

---

## 📚 Available Endpoints

| Endpoint | Method | Speed | Description | Use Case |
|----------|--------|-------|-------------|----------|
| `/scrape/fast` | POST | ⚡ 5-15s | Fast scraping, minimal features | Quick data extraction |
| `/scrape/simple` | POST | 🚀 10-25s | Simple scraping with just URL | Balanced extraction |
| `/scrape` | POST | 🐌 15-35s | Advanced scraping with all features | Custom extraction needs |
| `/scrape/stock/{symbol}` | GET | 🚀 10-20s | Yahoo Finance stock data | Financial data |
| `/docs` | GET | - | Interactive API documentation | Explore API features |

### Quick Reference:
- **Fast scraping**: `POST /scrape/fast?url=https://example.com` (5-15 seconds)
- **Simple scraping**: `POST /scrape/simple?url=https://example.com` (10-25 seconds)
- **AI extraction**: Use `ai_extraction` object in `/scrape` endpoint (15-35 seconds)
- **Custom selectors**: Use `selectors` array in `/scrape` endpoint
- **Webhooks**: Add `webhook` parameter for background processing

---

**🎉 Happy Scraping with crawl4ai!** 🎉

---

