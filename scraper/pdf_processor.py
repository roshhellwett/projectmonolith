import os
import time
import random
import requests
import logging
from google import genai
from google.genai import types

logger = logging.getLogger("PDF_PROCESSOR")

# --- ROBUST SEQUENTIAL MANAGER ---
RAW_KEYS = os.getenv("GEMINI_API_KEY", "")
ALL_KEYS = [k.strip() for k in RAW_KEYS.split(",") if k.strip()]

current_key_index = 0
BLACKLISTED_KEYS = {} # {key: timestamp}

def get_date_from_pdf(pdf_url):
    global current_key_index, BLACKLISTED_KEYS
    
    if not ALL_KEYS:
        logger.error("❌ No GEMINI_API_KEY found in .env!")
        return None

    now = time.time()
    
    # 1. Clean up old blacklisted keys
    for key, fail_time in list(BLACKLISTED_KEYS.items()):
        if now - fail_time > 86400: # 24 Hours
            del BLACKLISTED_KEYS[key]
            logger.info(f"♻️ Quota reset for a blacklisted key.")

    # 2. Try to find a working lifeline
    attempts = 0
    while attempts < len(ALL_KEYS):
        active_key = ALL_KEYS[current_key_index]
        
        if active_key in BLACKLISTED_KEYS:
            current_key_index = (current_key_index + 1) % len(ALL_KEYS)
            attempts += 1
            continue
            
        try:
            # Fetch PDF
            response = requests.get(pdf_url, timeout=20, verify=False, 
                                   headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200: return None
            
            # Anti-Spam Jitter
            time.sleep(random.uniform(7.0, 10.0)) 

            client = genai.Client(api_key=active_key)
            ai_response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[types.Part.from_bytes(data=response.content, mime_type="application/pdf"),
                          "Extract ONLY notice date DD-MM-YYYY from top-right header."]
            )

            return ai_response.text.strip()

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning(f"⚠️ Key #{current_key_index + 1} exhausted. Switching to lifeline...")
                BLACKLISTED_KEYS[active_key] = now
                current_key_index = (current_key_index + 1) % len(ALL_KEYS)
                attempts += 1
            else:
                logger.error(f"❌ AI Error on Key #{current_key_index + 1}: {e}")
                return None # Don't rotate for non-quota errors
                
    logger.error("🛑 ALL LIFELINES EXHAUSTED.")
    return None