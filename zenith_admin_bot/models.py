from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, BigInteger
from sqlalchemy.ext.declarative import declarative_base
import enum

AdminBase = declarative_base()


class ActionType(str, enum.Enum):
    KEYGEN = "keygen"
    EXTEND = "extend"
    REVOKE = "revoke"
    BROADCAST = "broadcast"
    USER_LOOKUP = "user_lookup"
    BOT_REGISTER = "bot_register"
    BOT_UNREGISTER = "bot_unregister"


class BotStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class AdminAuditLog(AdminBase):
    __tablename__ = "admin_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(BigInteger, nullable=False)
    action = Column(Enum(ActionType), nullable=False)
    target_user_id = Column(BigInteger, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BotRegistry(AdminBase):
    __tablename__ = "bot_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_name = Column(String(100), nullable=False, unique=True)
    token_hash = Column(String(64), nullable=True)
    status = Column(Enum(BotStatus), default=BotStatus.ACTIVE, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(20), default="unknown")
