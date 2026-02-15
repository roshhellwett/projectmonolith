from datetime import datetime, timezone
import zoneinfo

def utc_now() -> datetime:
    """Returns a naive UTC datetime to prevent asyncpg Timezone DataErrors."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def get_now_ist() -> datetime:
    """Returns timezone-aware IST datetime using Python standard library."""
    ist_zone = zoneinfo.ZoneInfo('Asia/Kolkata')
    return datetime.now(ist_zone)