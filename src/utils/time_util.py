import zoneinfo
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_now_ist() -> datetime:
    ist_zone = zoneinfo.ZoneInfo("Asia/Kolkata")
    return datetime.now(ist_zone)
