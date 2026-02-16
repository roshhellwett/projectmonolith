import re
import asyncio
import unicodedata
from zenith_group_bot.word_list import BANNED_WORDS

# Compile regex at startup (O(1) time complexity)
_PATTERN_STRING = r'\b(' + '|'.join(map(re.escape, BANNED_WORDS)) + r')\b'
BANNED_REGEX = re.compile(_PATTERN_STRING, re.IGNORECASE)

def _sync_regex_scan(text: str) -> tuple[bool, str]:
    if not text: return False, ""
    
    # 🚀 SCENARIO 6: Strip weird fonts & invisible characters (Zalgo/Spoofing)
    normalized_text = unicodedata.normalize('NFKC', text)
    clean_text = re.sub(r'[\u200B-\u200D\uFEFF]', '', normalized_text)
    
    # 🚀 SCENARIO 11: ReDoS Protection (Truncate massive payloads)
    if len(clean_text) > 1000:
        clean_text = clean_text[:1000]

    if BANNED_REGEX.search(clean_text):
        return True, "Banned vocabulary detected."
            
    return False, ""

async def is_inappropriate(text: str) -> tuple[bool, str]:
    # 🚀 SCENARIO 11: Push heavy regex to background thread so async loop doesn't freeze
    return await asyncio.to_thread(_sync_regex_scan, text)