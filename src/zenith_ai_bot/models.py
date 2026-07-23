from sqlalchemy import BigInteger, Column, Date, DateTime, Integer, String, Text

from core.database import Base
from utils.time_util import utc_now

AIBase = Base


class AIConversation(AIBase):
    __tablename__ = "zenith_ai_conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)


class AIUsageLog(AIBase):
    __tablename__ = "zenith_ai_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    usage_date = Column(Date, nullable=False)
    query_count = Column(Integer, default=0)
    summarize_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    persona = Column(String(20), default="default")
    selected_model = Column(String(50), default="llama-3.3-70b-versatile")


class AIUserSettings(AIBase):
    __tablename__ = "zenith_ai_user_settings"
    user_id = Column(BigInteger, primary_key=True)
    groq_api_key = Column(String(255), nullable=True)
    groq_tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
