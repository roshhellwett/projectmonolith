from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Displays the current system status and time in IST.
    """
    # Manually adjust to IST (UTC + 5:30)
    ist_offset = timedelta(hours=5, minutes=30)
    now_ist = datetime.utcnow() + ist_offset
    
    formatted_time = now_ist.strftime("%d %b %Y %I:%M %p")

    text = f"""
✅ <b>SUPREME SYSTEM ONLINE</b>

<b>Time (IST):</b> {formatted_time}
<b>Status:</b> Monitoring 24/7
<b>Services:</b> Async Pipeline Active

<i>The bot is checking university portals every few minutes. New notices will be broadcasted automatically.</i>
"""
    await update.message.reply_text(text, parse_mode="HTML")