import httpx
import random
import logging
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

from utils.hash_util import generate_hash
from core.sources import URLS
from core.config import SSL_VERIFY_EXEMPT, TARGET_YEAR
from scraper.date_extractor import extract_date
from scraper.pdf_processor import get_date_from_pdf

logger = logging.getLogger("SCRAPER")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

source_health = {key: 0 for key in URLS.keys()}

def get_source_health():
    return source_health

async def build_item(title, url, source_name, date_context=None):
    if not title or not url: return None
    
    BLOCKLIST = ["about us", "contact", "directory", "staff", "home"]
    if any(k in title.lower() for k in BLOCKLIST): return None

    # Sync date extraction from text
    real_date = extract_date(title) or (extract_date(date_context) if date_context else None)
    
    # Async date extraction from PDF
    if not real_date and ".pdf" in url.lower():
        real_date = await get_date_from_pdf(url)

    if real_date and real_date.year == TARGET_YEAR: [cite: 89, 90]
        return {
            "title": title.strip(),
            "source": source_name,
            "source_url": url,
            "pdf_url": url if ".pdf" in url.lower() else None,
            "content_hash": generate_hash(title, url),
            "published_date": real_date,
            "scraped_at": datetime.utcnow()
        }
    return None

async def parse_generic_links(base_url, source_name):
    data = []
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    verify = not any(domain in base_url for domain in SSL_VERIFY_EXEMPT) [cite: 94]
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=verify) as client:
            r = await client.get(base_url, headers=headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            container = soup.find("div", {"id": "content"}) or soup.find("table") or soup
            for a in container.find_all("a"):
                title = a.get_text(" ", strip=True)
                href = a.get("href")
                if not title or not href: continue
                
                full_url = urljoin(base_url, href)
                item = await build_item(title, full_url, source_name, a.parent.get_text())
                if item: data.append(item)
    except Exception as e:
        logger.error(f"Scrape Failed: {base_url} | {e}")
        raise e # Raise to let scrape_source handle health
    return data

async def scrape_source(source_key, source_config):
    """Isolated exception handler for source-specific failures."""
    try:
        results = await parse_generic_links(source_config["url"], source_config["source"])
        source_health[source_key] = 0
        return results
    except Exception as e:
        source_health[source_key] += 1
        return []