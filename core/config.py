import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
# TELEGRAM
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing in .env")

if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID missing in .env")

# ==============================
# DATABASE
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("⚠ DATABASE_URL not set — Using Local SQLite")
    DATABASE_URL = "sqlite:///makaut.db"
else:
    # Fix for SQLAlchemy 1.4+ removing 'postgres://' support
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ==============================
# PIPELINE
# ==============================
try:
    SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "300"))
except ValueError:
    SCRAPE_INTERVAL = 300

# ==============================
# LOGGING
# ==============================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")