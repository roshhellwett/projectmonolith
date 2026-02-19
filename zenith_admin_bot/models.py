from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, BigInteger
from sqlalchemy.ext.declarative import declarative_base
import enum

AdminBase = declarative_base()


class ActionType(str, enum.Enum):
    KEYGEN = "keygen"
    KEYGEN_BULK = "keygen_bulk"
    EXTEND = "extend"
    REVOKE = "revoke"
    BROADCAST = "broadcast"
    USER_LOOKUP = "user_lookup"
    USER_SEARCH = "user_search"
    GROUP_LOOKUP = "group_lookup"
    TICKET_REPLY = "ticket_reply"
    TICKET_CLOSE = "ticket_close"
    FAQ_ADD = "faq_add"
    FAQ_DELETE = "faq_delete"
    CANNED_ADD = "canned_add"
    CANNED_DELETE = "canned_delete"
    BROADCAST_SCHEDULED = "broadcast_scheduled"
    GROUP_DISABLE = "group_disable"
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class BotRegistry(AdminBase):
    __tablename__ = "bot_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_name = Column(String(100), nullable=False, unique=True)
    token_hash = Column(String(64), nullable=True)
    status = Column(Enum(BotStatus), default=BotStatus.ACTIVE, nullable=False)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(20), default="unknown")
