from datetime import datetime


def _format_date(value):
    """
    Safe date formatter for MAKAUT notices
    """

    if not value:
        return "Latest"

    if isinstance(value, datetime):
        return value.strftime("%d %b %Y")

    # If string date passed accidentally
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.strftime("%d %b %Y")
    except:
        return "Latest"


def format_message(n):

    # ===== DATE PRIORITY =====
    date_val = (
        n.get("notice_date")      # Future scraper improvement
        or n.get("published_date")
        or n.get("scraped_at")
    )

    date_str = _format_date(date_val)

    return (
        f"🎓 MAKAUT NOTICE\n\n"
        f"📌 {n.get('title','No Title')}\n\n"
        f"📅 {date_str}\n"
        f"🏛 {n.get('source','MAKAUT')}\n\n"
        f"🔗 {n.get('source_url','')}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"⚠️ Auto Aggregated Notice"
    )

#@roshhellwett makaut tele bot