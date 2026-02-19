from sqlalchemy import Column, Integer, BigInteger, DateTime, String, Text, Enum, Boolean
from sqlalchemy.orm import declarative_base
from utils.time_util import utc_now
import enum

Base = declarative_base()


class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicket(Base):
    __tablename__ = "zenith_support_tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default=TicketStatus.OPEN.value)
    priority = Column(String(20), default=TicketPriority.NORMAL.value)
    ai_response = Column(Text, nullable=True)
    admin_response = Column(Text, nullable=True)
    user_reply = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    last_admin_reply_at = Column(DateTime, nullable=True)
    user_replied = Column(Boolean, default=False)
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    resolved_at = Column(DateTime, nullable=True)


class FAQEntry(Base):
    __tablename__ = "zenith_support_faq"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class CannedResponse(Base):
    __tablename__ = "zenith_support_canned"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String(50), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    created_by = Column(BigInteger, nullable=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
