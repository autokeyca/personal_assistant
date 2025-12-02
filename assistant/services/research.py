"""Web research service for searching and fetching information."""

import logging
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ResearchService:
    """Service for conducting web research, searching, and fetching content."""

    def __init__(self, llm_service=None):
        """
        Initialize research service.

        Args:
            llm_service: Optional LLM service for summarization
        """
        self.llm_service = llm_service
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def search(self, query: str, max_results: int = 5, summarize: bool = False) -> Dict[str, Any]:
        """
        Search the web for a query.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            summarize: Whether to summarize results using LLM

        Returns:
            Dictionary with search results and optional summary
        """
        try:
            # Use DuckDuckGo's instant answer API (no key required)
            results = self._search_duckduckgo(query, max_results)

            response = {
                "query": query,
                "results": results,
                "count": len(results),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Generate summary if requested and LLM is available
            if summarize and self.llm_service and results:
                summary = self._summarize_results(query, results)
                response["summary"] = summary

            return response

        except Exception as e:
            logger.error(f"Search error for query '{query}': {e}")
            return {
                "query": query,
                "results": [],
                "count": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def fetch(self, url: str, extract: str = "text", summarize: bool = False) -> Dict[str, Any]:
        """
        Fetch and extract content from a URL.

        Args:
            url: URL to fetch
            extract: What to extract ("text", "html", "links")
            summarize: Whether to summarize content using LLM

        Returns:
            Dictionary with fetched content and metadata
        """
        try:
            # Fetch the page
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = soup.find('title')
            title_text = title.string if title else "No title"

            result = {
                "url": url,
                "title": title_text,
                "status_code": response.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Extract based on type
            if extract == "text":
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                result["content"] = text[:10000]  # Limit to 10k chars
                result["content_length"] = len(text)

            elif extract == "html":
                result["content"] = str(soup)[:10000]

            elif extract == "links":
                links = []
                for link in soup.find_all('a', href=True):
                    links.append({
                        "text": link.get_text().strip(),
                        "href": link['href']
                    })
                result["links"] = links[:100]  # Limit to 100 links

            # Generate summary if requested
            if summarize and self.llm_service and "content" in result:
                summary = self._summarize_content(url, title_text, result["content"])
                result["summary"] = summary

            return result

        except Exception as e:
            logger.error(f"Fetch error for URL '{url}': {e}")
            return {
                "url": url,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def ask(
        self,
        question: str,
        sources: List[str] = None,
        return_citations: bool = True
    ) -> Dict[str, Any]:
        """
        Answer a question using web research.

        Args:
            question: Question to answer
            sources: Optional list of specific URLs to search
            return_citations: Whether to include source citations

        Returns:
            Dictionary with answer and optional citations
        """
        try:
            # If no specific sources, search the web
            if not sources or sources == ["web"]:
                search_results = self.search(question, max_results=5, summarize=False)

                if not search_results.get("results"):
                    return {
                        "question": question,
                        "answer": "I couldn't find relevant information to answer this question.",
                        "timestamp": datetime.utcnow().isoformat()
                    }

                # Fetch content from top results
                contents = []
                citations = []

                for result in search_results["results"][:3]:  # Top 3 results
                    fetched = self.fetch(result["url"], extract="text", summarize=False)
                    if "content" in fetched:
                        contents.append({
                            "title": fetched["title"],
                            "url": result["url"],
                            "snippet": fetched["content"][:1000]
                        })
                        citations.append({
                            "title": fetched["title"],
                            "url": result["url"]
                        })

            else:
                # Fetch from specific sources
                contents = []
                citations = []
                for url in sources:
                    fetched = self.fetch(url, extract="text", summarize=False)
                    if "content" in fetched:
                        contents.append({
                            "title": fetched["title"],
                            "url": url,
                            "snippet": fetched["content"][:1000]
                        })
                        citations.append({
                            "title": fetched["title"],
                            "url": url
                        })

            # Use LLM to synthesize answer
            answer = self._synthesize_answer(question, contents)

            response = {
                "question": question,
                "answer": answer,
                "timestamp": datetime.utcnow().isoformat()
            }

            if return_citations:
                response["citations"] = citations

            return response

        except Exception as e:
            logger.error(f"Error answering question '{question}': {e}")
            return {
                "question": question,
                "answer": f"Error processing question: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search using DuckDuckGo HTML.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of search results
        """
        try:
            # DuckDuckGo HTML search
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            results = []

            # Parse results
            for result_div in soup.find_all('div', class_='result')[:max_results]:
                title_link = result_div.find('a', class_='result__a')
                snippet_div = result_div.find('a', class_='result__snippet')

                if title_link:
                    results.append({
                        "title": title_link.get_text().strip(),
                        "url": title_link.get('href', ''),
                        "snippet": snippet_div.get_text().strip() if snippet_div else ""
                    })

            return results

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    def _summarize_results(self, query: str, results: List[Dict]) -> str:
        """Summarize search results using LLM."""
        if not self.llm_service:
            return ""

        try:
            results_text = "\n\n".join([
                f"**{r['title']}**\n{r['snippet']}\nURL: {r['url']}"
                for r in results
            ])

            prompt = f"""Based on these search results for "{query}", provide a brief summary:

{results_text}

Summary:"""

            summary = self.llm_service.generate(prompt, max_tokens=500)
            return summary.strip()

        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return ""

    def _summarize_content(self, url: str, title: str, content: str) -> str:
        """Summarize fetched content using LLM."""
        if not self.llm_service:
            return ""

        try:
            prompt = f"""Summarize this web page content in 2-3 paragraphs:

Title: {title}
URL: {url}

Content:
{content[:3000]}

Summary:"""

            summary = self.llm_service.generate(prompt, max_tokens=500)
            return summary.strip()

        except Exception as e:
            logger.error(f"Content summarization error: {e}")
            return ""

    def _synthesize_answer(self, question: str, contents: List[Dict]) -> str:
        """Synthesize an answer from multiple sources using LLM."""
        if not self.llm_service:
            # Fallback: return snippets
            snippets = "\n\n".join([c["snippet"] for c in contents])
            return f"Based on available sources:\n\n{snippets}"

        try:
            sources_text = "\n\n---\n\n".join([
                f"Source: {c['title']}\n{c['snippet']}"
                for c in contents
            ])

            prompt = f"""Answer this question based on the provided sources:

Question: {question}

Sources:
{sources_text}

Provide a clear, concise answer based on the sources above:"""

            answer = self.llm_service.generate(prompt, max_tokens=800)
            return answer.strip()

        except Exception as e:
            logger.error(f"Answer synthesis error: {e}")
            return "Error synthesizing answer from sources."
