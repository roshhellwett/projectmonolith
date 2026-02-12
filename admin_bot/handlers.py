import os
import sys
import asyncio
import psutil
import time
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_ID

async def update_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asynchronously pulls latest code and restarts."""
    if update.effective_user.id != ADMIN_ID: 
        return
    await update.message.reply_text("📥 <b>Admin:</b> Pulling from GitHub...")
    
    process = await asyncio.create_subprocess_shell(
        "git pull origin main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        await update.message.reply_text("✅ Code updated. Restarting system...")
        os.execv(sys.executable, ['python3'] + sys.argv)
    else:
        await update.message.reply_text(f"❌ Git Fail: {stderr.decode()}")

async def send_db_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the database file to the admin."""
    if update.effective_user.id != ADMIN_ID: 
        return
    db_path = "makaut.db"
    if os.path.exists(db_path):
        await update.message.reply_document(document=open(db_path, 'rb'), caption="📂 Database Backup")
    else:
        await update.message.reply_text("❌ Database not found.")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Async health check reporting system metrics."""
    if update.effective_user.id != ADMIN_ID: 
        return
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    uptime = time.strftime('%Hh %Mm', time.gmtime(time.time() - psutil.Process().create_time()))

    status_msg = (
        "<b>🖥️ SYSTEM HEALTH</b>\n\n"
        f"<b>⏱ Uptime:</b> {uptime}\n"
        f"<b>📊 CPU:</b> {cpu}% | <b>🧠 RAM:</b> {ram}%\n\n"
        "✅ <b>Mode:</b> ASYNC MODE\n"
        "✅ <b>Services:</b> All ACTIVE"
    )
    await update.message.reply_text(status_msg, parse_mode='HTML')