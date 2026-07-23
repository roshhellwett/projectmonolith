import re

from cachetools import TTLCache

from zenith_group_bot.word_list import BANNED_WORDS, SPAM_DOMAINS

_pattern_cache = TTLCache(maxsize=1000, ttl=300)


def _word_to_pattern(word: str) -> str:
    word = word.strip()
    if not word:
        return ""
    if word.startswith("regex:"):
        return word[6:]
    escaped = re.escape(word)
    prefix = r"\b" if re.match(r"^\w", word, re.UNICODE) else r"(?:^|(?<=\s|\W))"
    suffix = r"\b" if re.search(r"\w$", word, re.UNICODE) else r"(?:$|(?=\s|\W))"
    return f"{prefix}{escaped}{suffix}"


def build_abuse_pattern(extra_words: list = None) -> re.Pattern:
    cache_key = tuple(sorted(extra_words)) if extra_words else ()
    if cache_key in _pattern_cache:
        return _pattern_cache[cache_key]

    all_words = list(BANNED_WORDS)
    if extra_words:
        all_words.extend(extra_words)

    patterns = [_word_to_pattern(w) for w in all_words if w.strip()]
    patterns = [p for p in patterns if p]
    compiled = re.compile(f"({'|'.join(patterns)})", re.IGNORECASE) if patterns else re.compile(r"$^")

    _pattern_cache[cache_key] = compiled
    return compiled


_default_pattern = build_abuse_pattern()


def scan_for_abuse(text: str, custom_words: list = None) -> bool:
    if not text:
        return False

    pattern = build_abuse_pattern(custom_words) if custom_words else _default_pattern

    return bool(pattern.search(text))


def scan_for_spam(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(domain in lower for domain in SPAM_DOMAINS)
