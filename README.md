# Advanced Web Scraper API

A modern, modular web scraping API built with FastAPI and crawl4ai.

## 📁 Project Structure

```
web-scrap/
├── main.py          # FastAPI app entry point and configuration
├── models.py        # Pydantic models for request/response validation
├── config.py        # Configuration constants and settings
├── scraper.py       # Core scraping logic and crawl4ai integration
├── routes.py        # API endpoints and route handlers
├── examples.md      # API usage examples and documentation
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the API:**
   ```bash
   uvicorn main:app --reload
   ```

3. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Simple scraping: `POST /scrape/simple?url=https://example.com`
   - Advanced scraping: `POST /scrape`

## 📋 File Descriptions

### `main.py`
- FastAPI application entry point
- App configuration and metadata
- Startup/shutdown event handlers
- Cache cleanup background tasks

### `models.py`
- Pydantic models for data validation
- Request/response schemas
- Type definitions for scraping configurations

### `config.py`
- Global configuration constants
- Cache and task management
- Default crawler configurations
- Yahoo Finance selectors

### `scraper.py`
- Core scraping logic using crawl4ai
- Data extraction methods (CSS/XPath, AI, structured data)
- Webhook functionality
- Fast scraping optimizations

### `routes.py`
- FastAPI route definitions
- Endpoint handlers for all scraping methods
- Error handling and response formatting

## 🎯 Benefits of This Structure

✅ **Separation of Concerns**: Each file has a single responsibility  
✅ **Maintainability**: Easy to modify individual components  
✅ **Testability**: Each module can be tested independently  
✅ **Scalability**: Easy to add new features or endpoints  
✅ **Readability**: Clear organization and smaller files  
✅ **Reusability**: Components can be imported and reused  

## 🔧 Adding New Features

1. **New endpoints**: Add to `routes.py`
2. **New models**: Add to `models.py`
3. **New scraping logic**: Add to `scraper.py`
4. **New configuration**: Add to `config.py`

## 📚 API Documentation

See `examples.md` for detailed API usage examples and endpoint documentation.
