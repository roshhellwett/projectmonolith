import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import DATABASE_URL

logger = logging.getLogger("DATABASE")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# ===== CONFIGURE CONNECT ARGS =====
connect_args = {}
if "sqlite" not in DATABASE_URL:
    # Only use SSL for Postgres/Cloud DBs
    connect_args["sslmode"] = "prefer"

# ===== ENGINE =====
engine = create_engine(
    DATABASE_URL,

    # ===== Cloud Production Safety =====
    pool_pre_ping=True,        # Detect dead connections
    pool_recycle=1800,         # Refresh every 30 min
    # SQLite doesn't support pool_size/max_overflow in the same way, 
    # but SQLAlchemy handles this gracefully or ignores it for SQLite.
    
    # ===== SQLAlchemy Modern Mode =====
    future=True,

    # ===== Railway / Cloud Compatibility =====
    connect_args=connect_args,

    echo=False
)


# ===== SESSION FACTORY =====
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine
)


# ===== BASE MODEL =====
Base = declarative_base()

logger.info("DATABASE ENGINE READY")