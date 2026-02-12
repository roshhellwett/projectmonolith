from database.db import SessionLocal
from database.models import Notification
from pipeline.message_formatter import format_search_result

def get_latest_results(limit=10):
    """Fetches results with mandatory session closing[cite: 82]."""
    # Use context manager for SQLite safety
    with SessionLocal() as db:
        notices = db.query(Notification).order_by(
            Notification.published_date.desc()
        ).limit(limit).all()
        return format_search_result(notices)

def search_by_keyword(query, limit=10):
    """Case-insensitive search with mandatory session closing[cite: 83]."""
    with SessionLocal() as db:
        results = db.query(Notification).filter(
            Notification.title.ilike(f"%{query}%")
        ).order_by(Notification.published_date.desc()).limit(limit).all()
        return format_search_result(results)