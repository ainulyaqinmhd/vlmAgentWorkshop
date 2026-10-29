"""
Web Search Module
Searches the web with DuckDuckGo and fetches page text
Provides Ollama-compatible tool functions for web search and content fetching
"""

import time
from typing import Dict, List, Any
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from .config import logger


def perform_web_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Perform a web search using DuckDuckGo, fetch content from top results.
    Returns a list of dictionaries, each containing a URL and its text content.
    """
    logger.info(f"Performing web search for query: {query} using DuckDuckGo")
    results_with_content = []

    try:
        # Use DuckDuckGo search
        with DDGS() as ddgs:
            # ddgs.text() returns a generator of dicts: {'title':..., 'href':..., 'body':...}
            ddg_results = list(ddgs.text(query, max_results=max_results))
            
        urls = [r['href'] for r in ddg_results if 'href' in r]
        logger.info(f"Found {len(urls)} URLs for the query.")

        # Filter out invalid URLs
        valid_urls = [
            url for url in urls
            if url.startswith("http://") or url.startswith("https://")
        ]

        for url in valid_urls:
            try:
                # Use headers to mimic a browser
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 403:
                    time.sleep(1)
                    headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"
                    response = requests.get(url, headers=headers, timeout=10)
                
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Remove script/style
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()

                # Get text
                text = soup.get_text(separator=" ", strip=True)
                
                # Chunk content
                max_chunk_size = 8000
                chunks = [
                    text[i : i + max_chunk_size]
                    for i in range(0, len(text), max_chunk_size)
                ]

                if chunks:
                    for chunk in chunks:
                        results_with_content.append({"url": url, "content": chunk})
                    logger.info(f"Successfully scraped content from: {url}")
                else:
                    logger.warning(f"No text content found at: {url}")

            except Exception as e:
                logger.error(f"Failed to scrape {url}. Reason: {e}")

        logger.info(f"Web search returned content from {len(results_with_content)} results")
        return results_with_content

    except Exception as e:
        logger.error(f"Exception during web search: {e}")
        return []


def web_search_tool(query: str, max_results: int = 3) -> Dict[str, Any]:
    """
    Ollama-compatible web search tool.
    Searches the web and returns top results with content.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        Dictionary with search results and citations
    """
    try:
        results = perform_web_search(query, max_results)
        citations = [result["url"] for result in results]

        # Format results for tool response
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "url": result["url"],
                    "content": result["content"][:4000],  # Limit content per result
                }
            )

        return {
            "query": query,
            "results": formatted_results,
            "citations": citations,
            "total_results": len(results),
        }
    except Exception as e:
        logger.error(f"Error in web_search_tool: {e}")
        return {"error": str(e), "query": query, "results": [], "citations": []}


def web_fetch_tool(url: str) -> Dict[str, Any]:
    """
    Ollama-compatible web fetch tool.
    Fetches and extracts content from a specific URL.

    Args:
        url: URL to fetch content from

    Returns:
        Dictionary with URL content and metadata
    """
    try:
        # Validate URL
        if not url.startswith(("http://", "https://")):
            return {"error": "Invalid URL format", "url": url}

        # Use headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse content
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "aside"]):
            element.decompose()

        # Extract title
        title = soup.title.string if soup.title else "No title"

        # Extract main content
        # Try to find main content areas
        content_selectors = [
            "main",
            "article",
            ".content",
            "#content",
            ".post",
            ".entry",
        ]
        content_text = ""

        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                content_text = content_area.get_text(separator=" ", strip=True)
                break

        # Fallback to body text if no specific content area found
        if not content_text:
            content_text = (
                soup.body.get_text(separator=" ", strip=True)
                if soup.body
                else soup.get_text(separator=" ", strip=True)
            )

        # Limit content length
        content_text = content_text[:8000]

        return {
            "url": url,
            "title": title,
            "content": content_text,
            "status_code": response.status_code,
            "citations": [url],
        }

    except requests.RequestException as e:
        logger.error(f"Request error fetching {url}: {e}")
        return {"error": f"Failed to fetch URL: {str(e)}", "url": url}
    except Exception as e:
        logger.error(f"Error in web_fetch_tool: {e}")
        return {"error": str(e), "url": url}
