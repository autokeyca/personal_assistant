"""Research API endpoints for web search and content fetching."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from assistant.api.auth import verify_api_key, check_permission
from assistant.services import ResearchService, LLMService
from assistant.config import get as get_config
from assistant.db import APIKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


# Request/Response Models
class SearchRequest(BaseModel):
    """Request model for web search."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results (1-20)")
    summarize: bool = Field(False, description="Whether to generate an LLM summary of results")


class FetchRequest(BaseModel):
    """Request model for fetching URL content."""
    url: str = Field(..., description="URL to fetch")
    extract: str = Field("text", description="What to extract: 'text', 'html', or 'links'")
    summarize: bool = Field(False, description="Whether to generate an LLM summary")


class AskRequest(BaseModel):
    """Request model for research-based Q&A."""
    question: str = Field(..., description="Question to answer")
    sources: Optional[List[str]] = Field(None, description="Specific URLs to use, or ['web'] to search")
    return_citations: bool = Field(True, description="Whether to include source citations")


class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str
    results: List[dict]
    count: int
    summary: Optional[str] = None
    timestamp: str


class FetchResponse(BaseModel):
    """Response model for fetched content."""
    url: str
    title: str
    content: Optional[str] = None
    links: Optional[List[dict]] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


class AskResponse(BaseModel):
    """Response model for research Q&A."""
    question: str
    answer: str
    citations: Optional[List[dict]] = None
    error: Optional[str] = None
    timestamp: str


def get_research_service():
    """Get ResearchService instance with LLM support."""
    try:
        api_key = get_config("gemini.api_key")
        model = get_config("gemini.model", "gemini-2.5-flash")
        llm = LLMService(api_key, model)
        return ResearchService(llm_service=llm)
    except:
        # If LLM not available, return service without it
        return ResearchService()


@router.post("/search", response_model=SearchResponse)
async def search_web(
    request: SearchRequest,
    api_key: APIKey = Depends(verify_api_key)
):
    """
    Search the web for information.

    Requires permission: `research:search` or `*`

    Example:
    ```json
    {
      "query": "best Python frameworks 2025",
      "max_results": 5,
      "summarize": true
    }
    ```

    Returns search results with titles, URLs, snippets, and optional LLM summary.
    """
    # Check permission
    if not check_permission(api_key, "research:search"):
        raise HTTPException(status_code=403, detail="Insufficient permissions for research:search")

    logger.info(f"Web search request from {api_key.name}: '{request.query}'")

    research = get_research_service()
    result = research.search(
        query=request.query,
        max_results=request.max_results,
        summarize=request.summarize
    )

    if "error" in result:
        logger.error(f"Search error: {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/fetch", response_model=FetchResponse)
async def fetch_url(
    request: FetchRequest,
    api_key: APIKey = Depends(verify_api_key)
):
    """
    Fetch and extract content from a URL.

    Requires permission: `research:fetch` or `*`

    Example:
    ```json
    {
      "url": "https://example.com/article",
      "extract": "text",
      "summarize": true
    }
    ```

    Extract options:
    - `text`: Extract clean text content
    - `html`: Get raw HTML
    - `links`: Extract all links from the page

    Returns the requested content with optional LLM summary.
    """
    # Check permission
    if not check_permission(api_key, "research:fetch"):
        raise HTTPException(status_code=403, detail="Insufficient permissions for research:fetch")

    logger.info(f"URL fetch request from {api_key.name}: {request.url}")

    # Validate extract type
    if request.extract not in ["text", "html", "links"]:
        raise HTTPException(status_code=400, detail="extract must be 'text', 'html', or 'links'")

    research = get_research_service()
    result = research.fetch(
        url=request.url,
        extract=request.extract,
        summarize=request.summarize
    )

    if "error" in result:
        logger.error(f"Fetch error: {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/ask", response_model=AskResponse)
async def research_question(
    request: AskRequest,
    api_key: APIKey = Depends(verify_api_key)
):
    """
    Answer a question using web research.

    Requires permission: `research:ask` or `*`

    Example:
    ```json
    {
      "question": "What's the weather in Montreal today?",
      "sources": ["web"],
      "return_citations": true
    }
    ```

    This endpoint:
    1. Searches the web for relevant information (or uses provided sources)
    2. Fetches content from top results
    3. Uses LLM to synthesize a comprehensive answer
    4. Returns answer with source citations

    Sources:
    - `["web"]` or `null`: Search the web automatically
    - `["url1", "url2"]`: Use specific URLs as sources
    """
    # Check permission
    if not check_permission(api_key, "research:ask"):
        raise HTTPException(status_code=403, detail="Insufficient permissions for research:ask")

    logger.info(f"Research question from {api_key.name}: '{request.question}'")

    research = get_research_service()
    result = research.ask(
        question=request.question,
        sources=request.sources,
        return_citations=request.return_citations
    )

    if "error" in result and not result.get("answer"):
        logger.error(f"Research error: {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])

    return result
