import re

from zenith_group_bot.word_list import BANNED_WORDS, SPAM_DOMAINS


def build_abuse_pattern(extra_words: list = None) -> re.Pattern:
    all_words = list(BANNED_WORDS)
    if extra_words:
        all_words.extend(extra_words)

    escaped = [re.escape(w) for w in all_words if w.strip()]
    if not escaped:
        return re.compile(r"$^")
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern, re.IGNORECASE)


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
