import os
from dotenv import load_dotenv

load_dotenv()

GROUP_BOT_TOKEN = os.getenv("GROUP_BOT_TOKEN", "")
AI_BOT_TOKEN = os.getenv("AI_BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "")
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0))
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))