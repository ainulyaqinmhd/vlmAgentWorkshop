import arxiv
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def search_arxiv(query: str, max_results: int = 3) -> Dict[str, Any]:
    """
    Search ArXiv for academic papers related to the query.
    
    Args:
        query: Search string
        max_results: Max number of papers to retrieve
        
    Returns:
        Dict with 'results' list containing title, summary, authors, links.
    """
    try:
        logger.info(f"Searching ArXiv for: {query}")
        
        # Construct client
        client = arxiv.Client()
        
        # Perform search
        search = arxiv.Search(
            query = query,
            max_results = max_results,
            sort_by = arxiv.SortCriterion.Relevance
        )
        
        results = []
        for r in client.results(search):
            paper_info = {
                "title": r.title,
                "summary": r.summary.replace("\n", " "),
                "authors": ", ".join([a.name for a in r.authors]),
                "pdf_url": r.pdf_url,
                "published": r.published.strftime("%Y-%m-%d")
            }
            results.append(paper_info)
            
        logger.info(f"Found {len(results)} ArXiv papers.")
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Error searching ArXiv: {e}")
def search_openalex(query: str, max_results: int = 3) -> Dict[str, Any]:
    """
    Search OpenAlex for academic papers across all disciplines.
    
    OpenAlex is a fully open index of 250M+ works.
    Great coverage of humanities, architecture, and social sciences.
    API: https://api.openalex.org/works
    
    Args:
        query: Search string
        max_results: Max number of papers to retrieve
        
    Returns:
        Dict with 'results' list containing title, summary, authors, links.
    """
    try:
        logger.info(f"Searching OpenAlex for: {query}")
        
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per_page": max_results,
            "sort": "relevance_score:desc"
        }
        
        # Retry logic for rate limits
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 429:
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"OpenAlex rate limit (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)
        
        data = response.json()
        
        results = []
        for work in data.get("results", []):
            # Get authors
            authors = ", ".join([
                au.get("author", {}).get("display_name", "Unknown")
                for au in work.get("authorships", [])
            ])
            
            # Reconstruct abstract from inverted index if present
            abstract = "No abstract available."
            if work.get("abstract_inverted_index"):
                try:
                    index = work["abstract_inverted_index"]
                    # Create list of (word, position) tuples
                    word_pos = []
                    for word, positions in index.items():
                        for pos in positions:
                            word_pos.append((pos, word))
                    # Sort by position and join
                    word_pos.sort()
                    abstract = " ".join([w for _, w in word_pos])
                except Exception:
                    pass
            
            # Get PDF URL
            pdf_url = ""
            if work.get("open_access", {}).get("is_oa"):
                pdf_url = work["open_access"].get("oa_url", "")
            if not pdf_url:
                pdf_url = work.get("doi", "") or work.get("id", "")
            
            # Get Venue
            venue = ""
            if work.get("primary_location", {}).get("source"):
                venue = work["primary_location"]["source"].get("display_name", "")
            
            paper_info = {
                "title": work.get("title", "Untitled"),
                "summary": abstract[:1500].replace("\n", " "), # Limit abstract length
                "authors": authors,
                "pdf_url": pdf_url,
                "published": str(work.get("publication_year", "Unknown")),
                "venue": venue
            }
            results.append(paper_info)
        
        logger.info(f"Found {len(results)} OpenAlex papers.")
        return {"results": results}
        
    except requests.exceptions.Timeout:
        logger.warning("OpenAlex request timed out")
        return {"results": [], "error": "Request timed out"}
    except Exception as e:
        logger.error(f"Error searching OpenAlex: {e}")
        return {"results": [], "error": str(e)}


def download_and_extract_pdf(url: str, max_chars: int = 5000) -> str:
    """
    Downloads a PDF from a URL and extracts its text content.
    
    Args:
        url: URL of the PDF
        max_chars: Maximum number of characters to return (to avoid context overflow)
        
    Returns:
        Extracted text string, or empty string if failed.
    """
    try:
        if not url.lower().endswith(".pdf") and "arxiv.org/pdf" not in url:
            # Simple check, though some PDFs don't end in .pdf
            logger.warning(f"URL {url} does not look like a PDF. Skipping download.")
            return ""

        logger.info(f"Downloading PDF from: {url}")
        
        # Download with timeout
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Open PDF from memory
        from io import BytesIO
        from pypdf import PdfReader
        text = ""
        for page in PdfReader(BytesIO(response.content)).pages:
            text += (page.extract_text() or "") + "\n"
            if len(text) > max_chars:
                break
        
        # Clean text
        text = text[:max_chars].replace("\n", " ").strip()
        logger.info(f"Successfully extracted {len(text)} chars from PDF.")
        return text
        
    except Exception as e:
        logger.info(f"Couldn't read the PDF at {url}, skipping it ({type(e).__name__})")
        return ""

