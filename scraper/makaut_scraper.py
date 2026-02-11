import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import logging
import time
from urllib.parse import urljoin
import urllib3

from core.sources import URLS
from scraper.date_extractor import extract_date

# Suppress SSL warnings for legacy university sites
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("SCRAPER")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
})

def generate_hash(title, url):
    return hashlib.sha256(f"{title}{url}".encode()).hexdigest()

def build_item(title, url, source_name):
    if not title or not url:
        return None
        
    # Filter junk links
    if any(x in url.lower() for x in ["javascript", "mailto", "tel:", "#"]):
        return None

    real_date = extract_date(title)
    pub_date = real_date if real_date else datetime.utcnow()

    return {
        "title": title.strip(),
        "source": source_name,
        "source_url": url,
        "pdf_url": url if ".pdf" in url.lower() else None,
        "content_hash": generate_hash(title, url),
        "published_date": pub_date,
        "scraped_at": datetime.utcnow()
    }

def parse_generic_links(base_url, source_name):
    data = []
    seen = set()

    # MAKAUT Exam portal often has SSL issues
    verify_ssl = False if "makautexam" in base_url else True
    
    # Allow loose validation for exam portal
    try:
        r = SESSION.get(base_url, timeout=30, verify=verify_ssl)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        
        tags = soup.find_all("a")
        
        for a in tags:
            title = a.get_text(" ", strip=True)
            href = a.get("href")

            if not title or len(title) < 5 or not href:
                continue

            full_url = urljoin(base_url, href)

            # Relaxed check: just ensure it has http/https
            if not full_url.startswith(("http:", "https:")):
                continue

            h = generate_hash(title, full_url)
            if h in seen:
                continue
            seen.add(h)

            item = build_item(title, full_url, source_name)
            if item:
                data.append(item)

    except Exception as e:
        # Re-raise to let scrape_source handle retries
        raise e

    return data

def scrape_source(source_key, source_config):
    url = source_config["url"]
    source_name = source_config["source"]

    for attempt in range(3):
        try:
            return parse_generic_links(url, source_name)
        except Exception as e:
            logger.warning(f"{source_key} attempt {attempt+1}/3 failed: {e}")
            time.sleep(2)

    logger.error(f"{source_key} FAILED AFTER 3 RETRIES")
    return []

def scrape_all_sources():
    all_data = []
    try:
        for key, config in URLS.items():
            logger.info(f"SCRAPING SOURCE {key}")
            source_data = scrape_source(key, config)
            logger.info(f"{key} -> {len(source_data)} items")
            all_data.extend(source_data)
        
        logger.info(f"TOTAL SCRAPED SAFE ITEMS {len(all_data)}")
        
    except Exception as e:
        logger.error(f"SCRAPE ALL ERROR {e}")

    return all_data