import os
from dotenv import load_dotenv

load_dotenv()

GROUP_BOT_TOKEN = os.getenv("GROUP_BOT_TOKEN", "")
AI_BOT_TOKEN = os.getenv("AI_BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Force SQLAlchemy to use the asyncpg driver
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))