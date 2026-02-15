import asyncio
from cachetools import TTLCache
import fitz  
from pydub import AudioSegment
from core.logger import setup_logger

logger = setup_logger("AI_UTILS")

ai_rate_limit = TTLCache(maxsize=10000, ttl=60.0)
_ai_db_engine = None

async def get_db_engine():
    global _ai_db_engine
    if _ai_db_engine is None:
        from core.config import DATABASE_URL
        if DATABASE_URL:
            from sqlalchemy.ext.asyncio import create_async_engine
            _ai_db_engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
    return _ai_db_engine

async def dispose_db_engine():
    global _ai_db_engine
    if _ai_db_engine:
        await _ai_db_engine.dispose()

async def check_user_ban_status(user_id: int) -> bool:
    try:
        engine = await get_db_engine()
        if not engine: return False
        from sqlalchemy import text
        
        async def fetch_db():
            async with engine.connect() as conn:
                query = text("SELECT strike_count FROM zenith_group_strikes WHERE user_id = :uid AND strike_count >= 3 LIMIT 1")
                result = await conn.execute(query, {"uid": user_id})
                return result.scalar() is not None
        
        return await asyncio.wait_for(fetch_db(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("⚠️ DB Fallback: Connection Timeout (Database took too long to respond).")
        return False
    except Exception as e:
        logger.warning(f"⚠️ DB Fallback Triggered: {repr(e)}")
        return False

async def check_ai_rate_limit(user_id: int) -> tuple[bool, str]:
    is_banned = await check_user_ban_status(user_id)
    if is_banned:
        return False, "🚫 You are globally banned from Zenith services due to group violations."

    current_requests = ai_rate_limit.get(user_id, 0)
    if current_requests >= 5:
        return False, "⏳ You are requesting too fast! Zenith AI needs a moment to rest. Please wait 60 seconds."
    
    ai_rate_limit[user_id] = current_requests + 1
    return True, ""

def sanitize_telegram_html(text: str) -> str:
    if not text: return ""
    if text.startswith("```html"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

def is_file_allowed(file_size: int) -> bool:
    if not file_size: return False
    return file_size <= (20 * 1024 * 1024)

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        with fitz.open(file_path) as doc:
            if doc.is_encrypted:
                return "ERROR:ENCRYPTED"
            for page in doc[:5]:
                text += page.get_text()
                
        if not text.strip():
            return "ERROR:EMPTY"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF Error: {e}")
        return "ERROR:BROKEN"

def convert_ogg_to_wav(ogg_path: str) -> str:
    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        audio = AudioSegment.from_file(ogg_path, format="ogg")
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        logger.error(f"Audio Error: {e}. Is FFmpeg installed?")
        return ""