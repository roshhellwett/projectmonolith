import os
import sys
import logging
import psutil
import time
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_ID

# Import the processor module directly to access live global variables
import scraper.pdf_processor as pdf_proc

logger = logging.getLogger("ADMIN_HANDLERS")

async def update_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pulls latest changes from GitHub and performs a hot-swap restart."""
    if update.effective_user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("📥 <b>Admin:</b> Pulling latest changes from GitHub...")
    try:
        os.system("git pull origin main")
        await update.message.reply_text("✅ Code updated. Restarting system...")
        # Restarting the python process
        os.execv(sys.executable, ['python3'] + sys.argv)
    except Exception as e:
        logger.error(f"Update failed: {e}")
        await update.message.reply_text(f"❌ Update failed: {e}")

async def send_db_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the SQLite database file to the Admin."""
    if update.effective_user.id != ADMIN_ID:
        return
        
    db_path = "makaut.db"
    if os.path.exists(db_path):
        await update.message.reply_document(
            document=open(db_path, 'rb'), 
            caption="📂 <b>Database Backup</b>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Database file not found.")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides a real-time report of system metrics and Sequential API status."""
    if update.effective_user.id != ADMIN_ID:
        return

    # 1. Gather System Metrics
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    process_start = psutil.Process(os.getpid()).create_time()
    uptime_seconds = int(time.time() - process_start)
    uptime_str = time.strftime('%Hh %Mm %Ss', time.gmtime(uptime_seconds))

    # 2. Sequential Key Monitoring (Live Data)
    total_keys = len(pdf_proc.ALL_KEYS)
    exhausted_count = len(pdf_proc.BLACKLISTED_KEYS)
    # Adding 1 because index starts at 0 (e.g., Index 0 is Key #1)
    active_key_num = pdf_proc.current_key_index + 1
    
    key_status = (
        f"<b>🔑 Gemini API Pool:</b> {total_keys - exhausted_count}/{total_keys} Available\n"
        f"🎯 <b>Current Lifeline:</b> Key #{active_key_num}\n"
    )
    
    if exhausted_count > 0:
        key_status += f"⚠️ <i>{exhausted_count} keys cooling down (24h).</i>\n"

    # 3. Final Status Message
    status_msg = (
        "<b>🖥️ System Health Report</b>\n\n"
        f"{key_status}\n"
        f"<b>⏱ Uptime:</b> {uptime_str}\n"
        f"<b>📊 CPU:</b> {cpu_usage}% | <b>🧠 RAM:</b> {ram_usage}%\n\n"
        "<b>🤖 Services:</b>\n"
        "✅ Broadcast & Search: Active\n"
        "✅ Scraper Pipeline: Active\n\n"
        "<i>Running 24/7 on Linux Mint</i>"
    )
    
    await update.message.reply_text(status_msg, parse_mode='HTML')