# Web Scraper API Setup Guide

## Free APIs Integrated

### 1. MyScheme Official API (Recommended)
- **Source**: API Setu (Government of India)
- **Cost**: FREE
- **Limit**: Generous (government API)
- **Setup**:
  1. Visit https://apisetu.gov.in
  2. Register/Login
  3. Subscribe to "MyScheme API"
  4. Copy API key
  5. Set environment variable:
     ```bash
     export MYSCHEME_API_KEY=your_api_key_here
     ```

### 2. API Setu Public Endpoint
- **Source**: apisetu.gov.in
- **Cost**: FREE
- **Limit**: Public access
- **Setup**: No API key required! Works out of the box.

### 3. ScraperAPI (Fallback)
- **Source**: scraperapi.com
- **Cost**: FREE tier
- **Limit**: 1,000 requests/month
- **Features**: JavaScript rendering, proxy rotation, CAPTCHA handling
- **Setup**:
  1. Visit https://www.scraperapi.com
  2. Sign up (no credit card required)
  3. Get API key from dashboard
  4. Set environment variable:
     ```bash
     export SCRAPER_API_KEY=your_api_key_here
     ```

### 4. Mock Data (Always Available)
- **Source**: Built-in
- **Cost**: FREE
- **Limit**: None
- **Setup**: No setup required

## Priority Order

The service tries APIs in this order:
1. **MyScheme Official API** (if key configured)
2. **API Setu Public** (always available)
3. **ScraperAPI** (if key configured)
4. **Mock Data** (fallback)

## Testing

### Check API Status
```bash
curl http://localhost:8008/api-status
```

### Get Setup Guide
```bash
curl http://localhost:8008/setup-guide
```

### Test Search
```bash
curl -X POST http://localhost:8008/scrape/schemes \
  -H "Content-Type: application/json" \
  -d '{"query":"widow pension","max_results":5}'
```

## Environment Variables

Add to `.env` file:
```env
# Optional: MyScheme Official API
MYSCHEME_API_KEY=your_myscheme_api_key

# Optional: ScraperAPI
SCRAPER_API_KEY=your_scraper_api_key
```

## Docker Compose

Update `docker-compose.yml`:
```yaml
web-scraper:
  build:
    context: ./backend/services/web-scraper
  container_name: zelia-scraper
  ports:
    - "8008:8008"
  environment:
    - MYSCHEME_API_KEY=${MYSCHEME_API_KEY}
    - SCRAPER_API_KEY=${SCRAPER_API_KEY}
  env_file: .env
  networks:
    - zelia-network
  restart: unless-stopped
```

## Notes

- **API Setu** works without any setup (public access)
- **Mock data** ensures service always returns results
- **ScraperAPI** free tier is generous (1000 req/month)
- **MyScheme API** is official government data (most reliable)
