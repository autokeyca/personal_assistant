# Web Research Capabilities

Jarvis can now perform web research for you! Search the web, fetch content from URLs, and get AI-powered answers to questions requiring current information.

## Features

### 1. Web Search
Search the web with AI-powered summaries.

**Via Telegram:**
- "Search for best restaurants in Montreal"
- "Find information about Python async patterns"
- "Look up the latest AI news"

**Via API:**
```bash
curl -X POST http://localhost:8000/research/search \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "best Python frameworks 2025",
    "max_results": 5,
    "summarize": true
  }'
```

### 2. URL Fetching
Extract and summarize content from any webpage.

**Via Telegram:**
- "Fetch https://example.com/article"
- "Read this article: [URL]"
- "Summarize https://blog.example.com/post"

**Via API:**
```bash
curl -X POST http://localhost:8000/research/fetch \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "extract": "text",
    "summarize": true
  }'
```

### 3. Research Questions
Ask questions requiring current/real-time information.

**Via Telegram:**
- "What's the weather in Montreal today?"
- "Who won the game yesterday?"
- "What are the latest developments in AI?"

**Via API:**
```bash
curl -X POST http://localhost:8000/research/ask \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the current weather in Montreal?",
    "sources": ["web"],
    "return_citations": true
  }'
```

## How It Works

### Architecture

```
┌──────────────┐
│   You        │
│ (Telegram)   │
└──────┬───────┘
       │
       │ "Search for Python news"
       ▼
┌──────────────────────────────┐
│   Jarvis Bot                 │
│   - Parses intent            │
│   - Calls ResearchService    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   ResearchService            │
│   - DuckDuckGo search        │
│   - Web scraping             │
│   - LLM summarization        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Response                   │
│   - Search results           │
│   - AI summary               │
│   - Citations                │
└──────────────────────────────┘
```

### Components

**ResearchService** (`assistant/services/research.py`)
- Web search using DuckDuckGo (no API key required)
- Content extraction with BeautifulSoup
- LLM-powered summarization using Gemini
- Citation tracking

**API Endpoints** (`assistant/api/research.py`)
- `POST /research/search` - Web search
- `POST /research/fetch` - URL content fetching
- `POST /research/ask` - Question answering

**Telegram Handlers** (`assistant/bot/handlers/intelligent.py`)
- `handle_web_search` - Process search requests
- `handle_web_fetch` - Process URL fetching
- `handle_web_ask` - Process questions

## Examples

### Example 1: Search for Information

**You:**
```
Search for best AI tools 2025
```

**Jarvis:**
```
🔍 Search Results for: best AI tools 2025

Summary:
The top AI tools in 2025 include ChatGPT, Claude, Midjourney for
image generation, GitHub Copilot for coding, and various automation
platforms. These tools focus on productivity, creativity, and
development workflows.

---

Top 5 Results:

1. **Best AI Tools in 2025: Complete Guide**
   _Comprehensive review of leading AI tools including ChatGPT,
   Claude, and specialized platforms for different use cases..._
   🔗 https://example.com/ai-tools-2025

2. **Top 10 AI Productivity Tools**
   _Discover AI tools that enhance productivity across writing,
   coding, design, and automation..._
   🔗 https://techreview.com/ai-productivity

[... more results ...]
```

### Example 2: Fetch Article Content

**You:**
```
Fetch https://blog.example.com/understanding-async-python
```

**Jarvis:**
```
📄 Understanding Async Python: A Complete Guide

🔗 https://blog.example.com/understanding-async-python

Summary:
This article explains Python's async/await syntax and the asyncio
library. It covers event loops, coroutines, tasks, and best practices
for writing asynchronous code. The guide includes practical examples
of web scraping, API calls, and concurrent processing.

Key topics:
- Event loop fundamentals
- Coroutines vs threads
- asyncio library overview
- Common pitfalls and solutions
```

### Example 3: Research Question

**You:**
```
What's the current temperature in Montreal?
```

**Jarvis:**
```
**Question:** What's the current temperature in Montreal?

**Answer:**
Based on current weather reports, the temperature in Montreal is
approximately 2°C (36°F) with partly cloudy conditions. The forecast
shows temperatures ranging from -1°C to 4°C throughout the day with
a chance of light snow in the evening.

**Sources:**
1. [Montreal Weather - Environment Canada](https://weather.gc.ca/city/pages/qc-147_metric_e.html)
2. [Current Montreal Conditions - The Weather Network](https://www.theweathernetwork.com/ca/weather/quebec/montreal)
3. [Montreal Forecast - AccuWeather](https://www.accuweather.com/en/ca/montreal/h3a/weather-forecast/56186)
```

## API Integration for Other Agents

### Python Agent

```python
import requests

def search_web(query: str, api_key: str):
    """Search the web via Jarvis API."""
    response = requests.post(
        "http://localhost:8000/research/search",
        headers={"X-API-Key": api_key},
        json={
            "query": query,
            "max_results": 5,
            "summarize": True
        }
    )
    return response.json()

# Usage
results = search_web("Python best practices", "your-api-key")
print(results["summary"])
```

### Node.js Agent

```javascript
const axios = require('axios');

async function researchQuestion(question, apiKey) {
    const response = await axios.post(
        'http://localhost:8000/research/ask',
        {
            question: question,
            sources: ['web'],
            return_citations: true
        },
        {
            headers: { 'X-API-Key': apiKey }
        }
    );
    return response.data;
}

// Usage
const answer = await researchQuestion(
    "What are microservices?",
    "your-api-key"
);
console.log(answer.answer);
```

### n8n Workflow

**HTTP Request Node:**
- Method: POST
- URL: `http://localhost:8000/research/search`
- Headers:
  - `X-API-Key`: `{{$node["Credentials"].json["api_key"]}}`
  - `Content-Type`: `application/json`
- Body:
  ```json
  {
    "query": "{{$json["search_query"]}}",
    "max_results": 5,
    "summarize": true
  }
  ```

### Make.com Scenario

**HTTP Module:**
- URL: `http://localhost:8000/research/ask`
- Method: POST
- Headers:
  - X-API-Key: `your-key`
- Body:
  ```json
  {
    "question": "{{question}}",
    "sources": ["web"]
  }
  ```

## Permissions

Control which API keys can access research features:

```bash
# Full research access
python scripts/manage_api_keys.py create "research-agent" \
  --permissions "research:search,research:fetch,research:ask"

# Search only
python scripts/manage_api_keys.py create "search-bot" \
  --permissions "research:search"

# All permissions
python scripts/manage_api_keys.py create "main-agent" \
  --permissions "*"
```

## Configuration

### Search Engine

Default: DuckDuckGo (no API key required)

To add Google Custom Search (optional):
1. Get API key from Google Cloud Console
2. Add to `config/config.yaml`:
   ```yaml
   research:
     search_engine: "google"
     google_api_key: "your-key"
     google_cx_id: "your-search-engine-id"
   ```

### LLM Summarization

Uses Gemini 2.5 Flash (configured in `config.yaml`):
```yaml
gemini:
  api_key: "your-gemini-api-key"
  model: "gemini-2.5-flash"
```

## Limitations

### Rate Limits

- **DuckDuckGo**: No official limit, but respect fair use
- **Web Scraping**: Respects robots.txt
- **LLM**: Gemini API limits apply (60 RPM free tier)

### Content Extraction

- JavaScript-heavy sites may not render fully
- Some sites block automated access
- Paywalled content cannot be accessed

### Accuracy

- Search results depend on web content availability
- LLM summaries are AI-generated (verify important info)
- Citations provided for fact-checking

## Troubleshooting

### "No results found"

**Cause**: Search query too specific or no matching results

**Solution**:
- Rephrase query
- Try broader terms
- Check spelling

### "Fetch error: 403 Forbidden"

**Cause**: Website blocks automated access

**Solution**:
- Site may require authentication
- Try alternative sources
- Use web_ask instead (searches multiple sources)

### "Error: timeout"

**Cause**: Website slow to respond

**Solution**:
- Try again
- Website may be down
- Use different source

### Research Not Working via Telegram

**Check**:
1. Bot is running: `sudo systemctl status personal-assistant`
2. Logs for errors: `tail -50 logs/assistant.log | grep -i research`
3. Try via API first to isolate issue

## Privacy & Security

### Data Handling

- ❌ Searches are NOT logged permanently
- ❌ Visited URLs are NOT stored
- ✅ Only research service logs (for debugging)
- ✅ No data sent to third parties (except search providers)

### API Security

- ✅ API key authentication required
- ✅ Permission-based access control
- ✅ Rate limiting prevents abuse
- ✅ Localhost-only by default (network isolated)

## Best Practices

### For Efficient Research

1. **Be specific**: "Python async best practices" > "Python tips"
2. **Use questions**: "What is X?" gets better answers than "X"
3. **Verify important info**: Check citations for critical data
4. **Combine approaches**:
   - Search first (overview)
   - Fetch specific articles (details)
   - Ask questions (synthesis)

### For API Integration

1. **Cache results**: Don't re-search the same query
2. **Handle errors**: Network issues happen
3. **Respect limits**: Don't spam requests
4. **Use summarization**: Reduces token usage

## Roadmap

**Future Enhancements:**
- [ ] PDF extraction and analysis
- [ ] Image search capabilities
- [ ] Video transcript fetching
- [ ] Multi-language support
- [ ] Search history and bookmarks
- [ ] Scheduled research reports
- [ ] Custom search engines

## API Reference

See full API documentation at: **http://localhost:8000/docs**

### Quick Reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/research/search` | POST | Required | Web search |
| `/research/fetch` | POST | Required | URL content |
| `/research/ask` | POST | Required | Q&A research |

### Response Formats

All endpoints return JSON with:
- Timestamp (ISO 8601)
- Request details
- Results/content
- Optional summary
- Error details (if failed)

## Support

**Issues?** Check logs:
```bash
# Bot logs
tail -100 logs/assistant.log | grep -i research

# API logs
tail -100 logs/api.log | grep -i research
```

**Questions?** The research system:
- Uses standard web technologies
- Falls back gracefully on errors
- Provides detailed error messages
- Logs all operations for debugging
