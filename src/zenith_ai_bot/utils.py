import asyncio
import re

from cachetools import TTLCache
from sqlalchemy import text

from core.logger import setup_logger

logger = setup_logger("AI_UTILS")

_rate_free = TTLCache(maxsize=10000, ttl=86400.0)  # 24h window for daily limits
_rate_pro = TTLCache(maxsize=10000, ttl=3600.0)  # 1h window for hourly limits

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?(your\s+)?(instructions|rules|guidelines)", re.IGNORECASE),
    re.compile(r"you\s+are\s+(now\s+)?(a|an|different|new)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"\(system\s*\)", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"drop\s+the\s+(system|persona|character)", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all|your)", re.IGNORECASE),
    re.compile(r"new\s+instruction[s]?\s*:", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?(system|programming)", re.IGNORECASE),
]

MAX_INPUT_LENGTH = 5000


def get_db_engine():
    from core.database import get_engine as _get_engine

    return _get_engine()


async def check_user_ban_status(user_id: int) -> bool:
    try:
        from core.database import AsyncSessionLocal
        from sqlalchemy import select
        from zenith_group_bot.models import GroupStrike

        async def fetch_db():
            async with AsyncSessionLocal() as session:
                stmt = select(GroupStrike.strike_count).where(
                    GroupStrike.user_id == user_id,
                    GroupStrike.strike_count >= 3,
                ).limit(1)
                result = await session.execute(stmt)
                return result.scalar() is not None

        return await asyncio.wait_for(fetch_db(), timeout=5.0)
    except TimeoutError:
        logger.warning("⚠️ DB Fallback: Connection Timeout.")
        return False
    except Exception as e:
        logger.warning(f"⚠️ DB Fallback Triggered: {repr(e)}")
        return False



async def check_ai_rate_limit(user_id: int, is_pro: bool = False) -> tuple[bool, str]:
    if await check_user_ban_status(user_id):
        return False, "🚫 You are globally banned from Zenith services due to group violations."

    if is_pro:
        current = _rate_pro.get(user_id, 0)
        if current >= 60:
            return False, "⏳ Pro rate limit reached (60/hour). Please wait a moment."
        _rate_pro[user_id] = current + 1
    else:
        current = _rate_free.get(user_id, 0)
        if current >= 10:
            return False, (
                "⏳ <b>Free tier limit reached</b> (10/day).\n\n"
                "💎 Upgrade to <b>Zenith Pro</b> for <b>60 queries/hour</b>, "
                "AI personas, deep research, code generation, and more.\n\n"
                "<code>/activate [YOUR_KEY]</code>"
            )
        _rate_free[user_id] = current + 1

    return True, ""


def sanitize_telegram_html(raw_text: str) -> str:
    if not raw_text:
        return ""
    txt = raw_text

    if txt.startswith("```html"):
        txt = txt[7:]
    elif txt.startswith("```"):
        txt = txt[3:]
    if txt.endswith("```"):
        txt = txt[:-3]

    txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
    txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<img[^>]*>", "[Image Omitted]", txt, flags=re.IGNORECASE)

    allowed_pattern = re.compile(
        r"<(?!" r"/?b>|/?i>|/?u>|/?s>|/?code>|/?pre>|" r'a\s+href=["\'][^"\']*["\'][^>]*>|/a>' r")[^>]*>",
        re.IGNORECASE,
    )
    txt = allowed_pattern.sub("", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()


def sanitize_user_input(text: str) -> str:
    if not text:
        return ""

    sanitized = text[:MAX_INPUT_LENGTH]

    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = pattern.sub("[FILTERED]", sanitized)

    sanitized = sanitized.replace("\x00", "")
    sanitized = re.sub(r"[\u200b-\u200f\u2028-\u202f]", "", sanitized)

    return sanitized.strip()
