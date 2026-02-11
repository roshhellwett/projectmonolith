from datetime import datetime


def format_message(n):

    title = n.get("title", "New Notification")
    source = n.get("source", "MAKAUT")
    url = n.get("source_url", "")
    pdf = n.get("pdf_url")
    date = n.get("published_date")

    # Format date nicely
    if isinstance(date, datetime):
        date_str = date.strftime("%d %b %Y %I:%M %p")
    else:
        date_str = "Just Now"

    # PDF badge
    pdf_line = f"\n📄 PDF: {pdf}" if pdf else ""

    return (
        "🎓 *MAKAUT NEW NOTIFICATION*\n\n"

        f"📌 *{title}*\n\n"

        f"🏛 Source: {source}\n"
        f"🕒 {date_str}\n\n"

        f"🔗 View Notice:\n{url}"
        f"{pdf_line}\n\n"

        "━━━━━━━━━━━━━━━\n"
        "_TeleAcademic Bot_"
    )
