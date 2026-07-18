from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, Integer, String, Text

from core.database import Base

AIBase = Base


class AIConversation(AIBase):
    __tablename__ = "zenith_ai_conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class AIUsageLog(AIBase):
    __tablename__ = "zenith_ai_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    usage_date = Column(Date, nullable=False)
    query_count = Column(Integer, default=0)
    summarize_count = Column(Integer, default=0)
    persona = Column(String(20), default="default")
