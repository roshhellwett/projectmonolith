import asyncio
from telegram import Bot
from database.db import SessionLocal
from core.config import BOT_TOKEN

async def check_telegram():
    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        print(f"TELEGRAM OK | Bot: @{me.username} | ID: {me.id}")
    except Exception as e:
        print(f"TELEGRAM FAIL | {e}")

def run_health_check():
    print("=== TELEACADEMIC HEALTH CHECK ===")

    # 1. DATABASE CHECK
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        print("DATABASE OK")
        db.close()
    except Exception as e:
        print(f"DATABASE FAIL | {e}")

    # 2. TELEGRAM CONNECTIVITY CHECK
    asyncio.run(check_telegram())

    # 3. SUBSCRIBER MODE
    print("SUBSCRIBERS: Mode is Channel Broadcast Only")

if __name__ == "__main__":
    run_health_check()