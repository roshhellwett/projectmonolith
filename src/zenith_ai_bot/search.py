import httpx

from core.config import SERPER_API_KEY
from core.logger import setup_logger

logger = setup_logger("SEARCH_TOOL")
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_keepalive_connections=20))
    return _http_client


async def perform_web_search(query: str, num_results: int = 2) -> str:
    api_key = SERPER_API_KEY
    if not api_key:
        return ""

    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": num_results}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        client = get_http_client()
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        snippets = []
        if "organic" in data:
            for idx, result in enumerate(data["organic"]):
                snippets.append(
                    f"[{idx+1}] Source: {result.get('title', '')}\n"
                    f"URL: {result.get('link', '')}\n"
                    f"Info: {result.get('snippet', '')}"
                )
        return "\n\n".join(snippets)
    except Exception as e:
        logger.error(f"Search API failed: {e}")
        return ""


async def perform_deep_research(topic: str) -> str:
    api_key = SERPER_API_KEY
    if not api_key:
        return ""

    client = get_http_client()
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    sections = []

    try:
        resp = await client.post(
            "https://google.serper.dev/search",
            json={"q": topic, "num": 5},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

        if "organic" in data:
            web_results = []
            for idx, r in enumerate(data["organic"]):
                web_results.append(
                    f"[WEB {idx+1}] {r.get('title', '')}\n"
                    f"URL: {r.get('link', '')}\n"
                    f"Snippet: {r.get('snippet', '')}"
                )
            sections.append("=== WEB RESULTS ===\n" + "\n\n".join(web_results))

        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            kg_text = f"[KNOWLEDGE GRAPH]\nTitle: {kg.get('title', '')}\nType: {kg.get('type', '')}\nDescription: {kg.get('description', '')}"
            sections.append(kg_text)
    except Exception as e:
        logger.error(f"Deep research web search failed: {e}")

    try:
        resp = await client.post(
            "https://google.serper.dev/news",
            json={"q": topic, "num": 3},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

        if "news" in data:
            news_results = []
            for idx, n in enumerate(data["news"]):
                news_results.append(
                    f"[NEWS {idx+1}] {n.get('title', '')}\n"
                    f"Source: {n.get('source', '')} | Date: {n.get('date', '')}\n"
                    f"URL: {n.get('link', '')}\n"
                    f"Snippet: {n.get('snippet', '')}"
                )
            sections.append("=== NEWS RESULTS ===\n" + "\n\n".join(news_results))
    except Exception as e:
        logger.error(f"Deep research news search failed: {e}")

    return "\n\n".join(sections)


async def close_http_client():
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
