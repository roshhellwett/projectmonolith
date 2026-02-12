import re
import asyncio
import unicodedata
from group_bot.word_list import BANNED_WORDS, SPAM_DOMAINS

def _run_regex_sync(text):
    """Zenith Deep Scan Engine: Flattens text to catch bypass attempts."""
    if not text:
        return False, None

    # 1. Unicode Normalization
    normalized_text = unicodedata.normalize("NFKD", text).lower()
    
    # 2. De-Noising: Remove all symbols and spaces (e.g., f.u.c.k -> fuck)
    # Supports English, Hindi, and Bengali character ranges
    noise_free = re.sub(r'[^a-zA-Z0-9\u0900-\u097F\u0980-\u09FF\s]', '', normalized_text)
    collapsed_text = noise_free.replace(" ", "")

    # 3. Substring Forensic Match
    for word in BANNED_WORDS:
        if word.lower() in collapsed_text:
            return True, "Abusive/Inappropriate Language"

    # 4. Smart Link Protection
    if "makaut" not in normalized_text:
        for domain in SPAM_DOMAINS:
            if domain in normalized_text:
                return True, "Unauthorized/Suspicious Link"

    return False, None

async def is_inappropriate(text: str) -> (bool, str):
    if not text:
        return False, None
    return await asyncio.to_thread(_run_regex_sync, text)