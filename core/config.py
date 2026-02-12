import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
# TELEGRAM TOKENS
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SEARCH_BOT_TOKEN = os.getenv("SEARCH_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
GROUP_BOT_TOKEN = os.getenv("GROUP_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing in .env")

# ==============================
# DATABASE CONFIGURATION
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///makaut.db")

# ==============================
# PIPELINE & LOGIC
# ==============================
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "300"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
TARGET_YEAR = 2026  # Centralized Gatekeeper Year
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# SSL Safety: Targeted exemptions for known broken university certs
SSL_VERIFY_EXEMPT = ["makautexam.net", "www.makautexam.net"]