import os
import httpx
from core.logger import setup_logger

logger = setup_logger("SEARCH_TOOL")

async def perform_web_search(query: str) -> str:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return ""

    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": 2} 
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            snippets = []
            if "organic" in data:
                for idx, result in enumerate(data["organic"]):
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    link = result.get("link", "")
                    snippets.append(f"[{idx+1}] Source: {title}\nURL: {link}\nInfo: {snippet}")
            
            return "\n\n".join(snippets)
    except Exception as e:
        logger.error(f"Search API failed: {e}")
        return ""