from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    # Manually adjust to IST (UTC + 5:30)
    # This avoids needing the 'pytz' library which isn't in your requirements.txt
    ist_offset = timedelta(hours=5, minutes=30)
    now_ist = datetime.utcnow() + ist_offset
    
    formatted_time = now_ist.strftime("%d %b %Y %I:%M %p")

    text = f"""
✅ **SYSTEM ONLINE**

**Time (IST):** {formatted_time}
**Status:** Monitoring Active
**Mode:** Auto-Broadcast

_If no messages appear, there are no new notices on the website._
"""
    # Using markdown parsing for bold text
    await update.message.reply_text(text, parse_mode="Markdown")