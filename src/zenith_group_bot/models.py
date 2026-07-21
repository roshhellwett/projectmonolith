from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint

from core.database import Base
from utils.time_util import utc_now


class GroupSettings(Base):
    __tablename__ = "zenith_group_settings"
    chat_id = Column(BigInteger, primary_key=True)
    owner_id = Column(BigInteger, nullable=False)
    group_name = Column(String, nullable=True)
    features = Column(String, default="both")
    strength = Column(String, default="medium")
    is_active = Column(Boolean, default=False)
    ai_enabled = Column(Boolean, default=False)
    crypto_enabled = Column(Boolean, default=False)
    raid_mode = Column(Boolean, default=False)
    raid_expires_at = Column(DateTime, nullable=True)
    setup_date = Column(DateTime, default=utc_now)


class GroupStrike(Base):
    __tablename__ = "zenith_group_strikes"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    chat_id = Column(BigInteger, index=True)
    strike_count = Column(Integer, default=0)
    last_violation = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "chat_id", name="_user_chat_uc"),)


class NewMember(Base):
    __tablename__ = "zenith_new_members"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    chat_id = Column(BigInteger, index=True)
    joined_at = Column(DateTime, default=utc_now)
    __table_args__ = (UniqueConstraint("user_id", "chat_id", name="_new_member_chat_uc"),)


class CustomBannedWord(Base):
    __tablename__ = "zenith_custom_words"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    word = Column(String(100), nullable=False)
    added_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    __table_args__ = (UniqueConstraint("chat_id", "word", name="_chat_word_uc"),)


class ScheduledMessage(Base):
    __tablename__ = "zenith_scheduled_messages"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    owner_id = Column(BigInteger, nullable=False)
    message_text = Column(Text, nullable=False)
    hour = Column(Integer, nullable=False)
    minute = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_sent = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class WelcomeConfig(Base):
    __tablename__ = "zenith_welcome_config"
    chat_id = Column(BigInteger, primary_key=True)
    message_template = Column(Text, nullable=False)
    send_dm = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=utc_now)


class ModerationLog(Base):
    __tablename__ = "zenith_moderation_log"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(100), nullable=True)
    action = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    moderator_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=utc_now)
