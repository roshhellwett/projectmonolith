import httpx
from cachetools import TTLCache

from core.circuit_breaker import get_breaker
from core.config import SERPER_API_KEY
from core.logger import setup_logger

logger = setup_logger("SEARCH_TOOL")
_http_client: httpx.AsyncClient | None = None
_search_cache: TTLCache = TTLCache(maxsize=300, ttl=300)


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_keepalive_connections=20))
    return _http_client


async def perform_web_search(query: str, num_results: int = 2) -> str:
    api_key = SERPER_API_KEY
    if not api_key:
        return ""

    cache_key = f"web_{query.lower().strip()}_{num_results}"
    cached = _search_cache.get(cache_key)

    breaker = get_breaker("serper")
    if not breaker.can_execute():
        if cached:
            logger.debug("Serving cached search results (circuit open)")
            return cached
        return "[Search service temporarily unavailable — serving AI knowledge only]"

    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": num_results}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        client = get_http_client()
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 429:
            breaker.record_failure()
            logger.warning("Serper API rate limit hit (429)")
            return cached or "[Live web search quota exceeded temporarily]"
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
        result_str = "\n\n".join(snippets)
        breaker.record_success()
        if result_str:
            _search_cache[cache_key] = result_str
        return result_str
    except Exception as e:
        breaker.record_failure()
        logger.error(f"Search API failed: {e}")
        return cached or ""


async def perform_deep_research(topic: str) -> str:
    api_key = SERPER_API_KEY
    if not api_key:
        return ""

    cache_key = f"deep_{topic.lower().strip()}"
    cached = _search_cache.get(cache_key)

    breaker = get_breaker("serper")
    if not breaker.can_execute():
        if cached:
            return cached
        return "[Deep search service temporarily unavailable]"

    client = get_http_client()
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    sections = []

    try:
        resp = await client.post(
            "https://google.serper.dev/search",
            json={"q": topic, "num": 5},
            headers=headers,
        )
        if resp.status_code == 429:
            breaker.record_failure()
            return cached or "[Live research quota exceeded temporarily]"
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
        breaker.record_success()
    except Exception as e:
        breaker.record_failure()
        logger.error(f"Deep research web search failed: {e}")

    try:
        if breaker.can_execute():
            resp = await client.post(
                "https://google.serper.dev/news",
                json={"q": topic, "num": 3},
                headers=headers,
            )
            if resp.status_code != 429:
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
                breaker.record_success()
    except Exception as e:
        breaker.record_failure()
        logger.error(f"Deep research news search failed: {e}")

    final_str = "\n\n".join(sections)
    if final_str:
        _search_cache[cache_key] = final_str
    return final_str or cached or ""


async def close_http_client():
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
