import os
import sys
import asyncio
import psutil
from sqlalchemy import func, select
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_ID
from database.db import AsyncSessionLocal
from database.models import Notification, UserStrike

async def update_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asynchronously pulls latest code from GitHub and restarts."""
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
    """Sends the database file to the admin securely."""
    if update.effective_user.id != ADMIN_ID: 
        return
    db_path = "makaut.db"
    if os.path.exists(db_path):
        with open(db_path, 'rb') as db_file:
            await update.message.reply_document(document=db_file, caption="📂 Database Backup")
    else:
        await update.message.reply_text("❌ Database not found.")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forensic Health Report with DB Metrics."""
    if update.effective_user.id != ADMIN_ID: 
        return
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    async with AsyncSessionLocal() as db:
        # Count total notifications in DB
        count_stmt = select(func.count(Notification.id))
        total_notices = (await db.execute(count_stmt)).scalar()
        
        # Count total users with strike records
        strike_stmt = select(func.count(UserStrike.user_id))
        active_strikes = (await db.execute(strike_stmt)).scalar()

    status_msg = (
        "<b>🖥️ ZENITH SYSTEM HEALTH</b>\n\n"
        f"<b>📊 CPU:</b> {cpu}% | <b>🧠 RAM:</b> {ram}%\n"
        f"<b>📁 DB Notices:</b> {total_notices}\n"
        f"<b>🚫 Tracked Violators:</b> {active_strikes}\n\n"
        "✅ <b>Database:</b> ASYNC STATIC POOL ACTIVE\n"
        "✅ <b>Pipeline:</b> HEARTBEAT STABLE"
    )
    await update.message.reply_text(status_msg, parse_mode='HTML')
     #@academictelebotbyroshhellwett