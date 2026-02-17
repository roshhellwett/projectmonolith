import os
import httpx
from typing import Optional
from core.logger import setup_logger

logger = setup_logger("SEARCH_TOOL")
_http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    """Singleton HTTP client to prevent TCP Socket Exhaustion."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_keepalive_connections=20))
    return _http_client

async def perform_web_search(query: str) -> str:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key: return ""

    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": 2} 
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        client = get_http_client()
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        snippets = []
        if "organic" in data:
            for idx, result in enumerate(data["organic"]):
                snippets.append(f"[{idx+1}] Source: {result.get('title', '')}\nURL: {result.get('link', '')}\nInfo: {result.get('snippet', '')}")
        return "\n\n".join(snippets)
    except Exception as e:
        logger.error(f"Search API failed: {e}")
        return ""

async def close_http_client():
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
