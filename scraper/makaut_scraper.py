import httpx
import random
import logging
import asyncio
import time
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

from utils.hash_util import generate_hash
from core.sources import URLS
from core.config import SSL_VERIFY_EXEMPT, TARGET_YEARS, REQUEST_TIMEOUT
from scraper.date_extractor import extract_date
from scraper.pdf_processor import get_date_from_pdf

logger = logging.getLogger("SCRAPER")

# Robust User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/121.0.0.0 Safari/537.36"
]

# CIRCUIT BREAKER STATE
source_health = {}
MAX_FAILURES = 3
COOLDOWN_SECONDS = 1800  # 30 Minutes


def _parse_html_sync(html_content, source_config):
    """
    CPU-BOUND TASK: Universal Link Extractor with Deep Sibling Scanning.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    items = []
    
    def get_contextual_text(a_tag, max_siblings=10, max_chars=150):
        """Walks backwards through siblings to collect surrounding text."""
        text_parts = []
        char_count = 0
        current = a_tag.previous_sibling
        sibling_count = 0
        
        while current and sibling_count < max_siblings and char_count < max_chars:
            if hasattr(current, 'name') and current.name:
                current = current.previous_sibling
                sibling_count += 1
                continue
            
            text = str(current).strip()
            if text and len(text) < 100:
                text_parts.insert(0, text)
                char_count += len(text)
            
            current = current.previous_sibling
            sibling_count += 1
        
        link_text = a_tag.get_text(" ", strip=True)
        text_parts.append(link_text)
        
        return " ".join(text_parts).strip()
    
    for a in soup.find_all("a", href=True):
        full_url = urljoin(source_config["url"], a["href"])
        
        if a.parent and len(a.parent.find_all("a")) == 1:
            parent_text = a.parent.get_text(" ", strip=True)
            if parent_text and len(parent_text) < 300:
                final_text = parent_text
            else:
                final_text = get_contextual_text(a)
        else:
            final_text = get_contextual_text(a)
        
        items.append({
            "text": final_text,
            "url": full_url
        })
            
    return items


async def build_item(raw_data, source_name):
    """🔍 DIAGNOSTIC VERSION - Ultra-verbose logging"""
    title = raw_data["text"]
    url = raw_data["url"]

    # 🔍 LOG 1: Raw extraction
    logger.info(f"🔍 RAW EXTRACT: {title[:120]}")

    if not title or not url: 
        logger.warning(f"❌ REJECTED: Empty title or URL")
        return None
    
    # 1. Blocklist check
    BLOCKLIST = [
        "about us", "contact", "home", "back", "gallery", 
        "archive", "click here", "apply now", "visit"
    ]
    
    if len(title) < 5:
        logger.warning(f"❌ REJECTED: Title too short ({len(title)} chars): {title[:40]}")
        return None
        
    for keyword in BLOCKLIST:
        if keyword in title.lower():
            logger.warning(f"❌ REJECTED: Blocklist '{keyword}': {title[:60]}")
            return None

    # 2. Date extraction
    real_date = extract_date(title)
    
    # 🔍 LOG 2: Date result
    if real_date:
        logger.info(f"✅ DATE FOUND: {real_date.strftime('%Y-%m-%d')} | {title[:60]}")
    else:
        logger.warning(f"⚠️ NO DATE in HTML: {title[:80]}")
        
        # Try PDF fallback
        if url and ".pdf" in url.lower():
            logger.info(f"🔍 Checking PDF: {url[:80]}")
            real_date = await get_date_from_pdf(url)
            if real_date:
                logger.info(f"✅ DATE FROM PDF: {real_date.strftime('%Y-%m-%d')}")
    
    if not real_date:
        logger.error(f"❌ REJECTED: No date found: {title[:60]}")
        return None

    # 3. Ghost filter
    OLD_YEARS = ["2019", "2020", "2021", "2022", "2023"]
    has_old_text = any(y in title for y in OLD_YEARS)
    is_old_date = str(real_date.year) in OLD_YEARS
    
    # 🔍 LOG 3: Ghost filter
    if has_old_text:
        logger.info(f"⚠️ Old year in text: {title[:60]}")
        if is_old_date:
            logger.warning(f"❌ REJECTED: Old date {real_date.year}: {title[:60]}")
            return None
        else:
            logger.info(f"✅ PASS: Recent date {real_date.year} despite old text")

    # 4. Year validity
    if real_date.year not in TARGET_YEARS:
        logger.error(f"❌ REJECTED: Year {real_date.year} not in {TARGET_YEARS}: {title[:60]}")
        return None
    
    # 🔍 LOG 4: Success!
    logger.info(f"✅✅✅ VALID: {title[:60]} | {real_date.strftime('%Y-%m-%d')}")
    
    return {
        "title": title.strip(),
        "source": source_name,
        "source_url": url,
        "pdf_url": url if ".pdf" in url.lower() else None,
        "content_hash": generate_hash(title, url),
        "published_date": real_date,
        "scraped_at": datetime.utcnow()
    }


async def scrape_source(source_key, source_config):
    health = source_health.get(source_key, {"fails": 0, "next_try": 0})
    if time.time() < health["next_try"]:
        return []

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    verify = not any(domain in source_config["url"] for domain in SSL_VERIFY_EXEMPT)
    
    try:
        await asyncio.sleep(random.uniform(2, 5)) 
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=verify, follow_redirects=True) as client:
            r = await client.get(source_config["url"], headers=headers)
            r.raise_for_status()

            raw_items = await asyncio.to_thread(_parse_html_sync, r.text, source_config)
            
            logger.info(f"🔎 {source_key}: Analyzing {len(raw_items)} candidates...")
            
            valid_items = []
            for raw in raw_items:
                item = await build_item(raw, source_config["source"])
                if item: 
                    valid_items.append(item)

            source_health[source_key] = {"fails": 0, "next_try": 0}
            
            if valid_items:
                logger.info(f"✅ {source_key}: Extracted {len(valid_items)} valid notices.")
            else:
                logger.warning(f"⚠️ {source_key}: No valid items after filtering.")
                
            return valid_items

    except Exception as e:
        fails = health["fails"] + 1
        wait_time = 0
        
        if fails >= MAX_FAILURES:
            wait_time = COOLDOWN_SECONDS
            logger.error(f"❌ {source_key} BROKEN: {e}. Cooling down for {wait_time}s.")
        else:
            logger.warning(f"⚠️ {source_key} Glitch: {e}")
        
        source_health[source_key] = {
            "fails": fails, 
            "next_try": time.time() + wait_time
        }
        return []

#@academictelebotbyroshhellwett
