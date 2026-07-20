import os

from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Feature Flags
# ==========================================
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
ENABLE_WHALE_ALERTS = os.getenv("ENABLE_WHALE_ALERTS", "true").lower() == "true"
ENABLE_NEW_PAIRS = os.getenv("ENABLE_NEW_PAIRS", "true").lower() == "true"

# ==========================================
# Bot Tokens
# ==========================================
GROUP_BOT_TOKEN = os.getenv("GROUP_BOT_TOKEN", "").strip()
AI_BOT_TOKEN = os.getenv("AI_BOT_TOKEN", "").strip()
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "").strip()
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "").strip()
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "").strip()

# ==========================================
# Admin
# ==========================================
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0").strip())

# ==========================================
# Webhook & Server
# ==========================================
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
PORT = int(os.getenv("PORT", "8080").strip())
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

# ==========================================
# Database
# ==========================================
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL and DATABASE_URL.startswith("postgres://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL and DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))

# ==========================================
# Blockchain RPCs
# ==========================================
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

# ==========================================
# AI Services
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SUPPORT_GROQ_API_KEY = os.getenv("SUPPORT_GROQ_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
AI_SEARCH_TRIGGERS = ["today", "current", "news", "price", "latest", "search"]


# ==========================================
# Utility Functions
# ==========================================
def is_owner(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID and ADMIN_USER_ID != 0


def get_user_tier(user_id: int, days_left: int = 0) -> str:
    if is_owner(user_id):
        return "owner"
    elif days_left > 0:
        return "pro"
    else:
        return "free"
