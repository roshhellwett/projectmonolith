import re
import asyncio
import unicodedata
from group_bot.word_list import BANNED_WORDS, SPAM_DOMAINS

def _run_regex_sync(text):
    """Synchronous regex engine for heavy word lists."""
    normalized_text = unicodedata.normalize("NFKD", text).lower()
    
    # Forensic Abuse Detection using Word Boundaries
    abuse_pattern = r"(?i)\b(" + "|".join(re.escape(word) for word in BANNED_WORDS) + r")\b"
    
    if re.search(abuse_pattern, normalized_text):
        return True, "Abusive/Inappropriate Language"

    # Smart Link Protection 
    if "makaut" not in normalized_text:
        for domain in SPAM_DOMAINS:
            if domain in normalized_text:
                return True, "Unauthorized/Suspicious Link"

    return False, None

async def is_inappropriate(text: str) -> (bool, str):
    """Async wrapper for the multi-lingual forensic filter."""
    if not text:
        return False, None
    
    # Offload heavy regex matching to a separate thread
    return await asyncio.to_thread(_run_regex_sync, text)