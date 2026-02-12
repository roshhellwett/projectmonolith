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

# Military-Grade User Agents to bypass university firewalls 
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
]

source_health = {key: 0 for key in URLS.keys()}

def get_source_health():
    """Returns the failure count for each source for admin monitoring[cite: 38]."""
    return source_health

async def build_item(title, url, source_name, date_context=None):
    """Refines and validates notice data before database entry[cite: 17, 18]."""
    if not title or not url: 
        return None
    
    BLOCKLIST = ["about us", "contact", "directory", "staff", "home", "back"]
    if any(k in title.lower() for k in BLOCKLIST): 
        return None

    # 1. Primary Date Extraction (Text/Context) [cite: 13, 17]
    real_date = extract_date(title) or (extract_date(date_context) if date_context else None)
    
    # 2. Forensic PDF Date Extraction (If text extraction fails) 
    if not real_date and ".pdf" in url.lower():
        real_date = await get_date_from_pdf(url)

    # 3. Gatekeeper Logic: Only accept notices from the current year [cite: 14, 18]
    if real_date and real_date.year == TARGET_YEAR:
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
    """Securely fetches and parses university webpages[cite: 19, 20]."""
    data = []
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    # Targeted SSL verification bypass for specific university domains 
    verify = not any(domain in base_url for domain in SSL_VERIFY_EXEMPT)
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=verify) as client:
            r = await client.get(base_url, headers=headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Context-aware scraping for tables and main content areas [cite: 20]
            container = soup.find("div", {"id": "content"}) or soup.find("table") or soup
            for a in container.find_all("a"):
                title = a.get_text(" ", strip=True)
                href = a.get("href")
                if not title or not href: 
                    continue
                
                full_url = urljoin(base_url, href)
                item = await build_item(title, full_url, source_name, a.parent.get_text())
                if item: 
                    data.append(item)
    except Exception as e:
        logger.error(f"Scrape Failed: {base_url} | {e}")
        raise e 
    return data

async def scrape_source(source_key, source_config):
    """Main entry point for scraping with Stealth Jitter delay[cite: 31, 32]."""
    try:
        # Zenith Stealth Upgrade: Random jitter (1-5s) to mimic human behavior
        await asyncio.sleep(random.uniform(1, 5)) 
        
        results = await parse_generic_links(source_config["url"], source_config["source"])
        source_health[source_key] = 0
        return results
    except Exception as e:
        source_health[source_key] += 1
        logger.error(f"Source {source_key} failure count: {source_health[source_key]}")
        return []