from sqlalchemy import Column, Integer, BigInteger, DateTime, UniqueConstraint, String, Boolean
from sqlalchemy.orm import declarative_base
from utils.time_util import utc_now

Base = declarative_base()

class GroupSettings(Base):
    __tablename__ = "zenith_group_settings"
    chat_id = Column(BigInteger, primary_key=True, index=True)
    owner_id = Column(BigInteger, nullable=False)
    group_name = Column(String, nullable=True)
    features = Column(String, default="both")
    strength = Column(String, default="medium")
    is_active = Column(Boolean, default=False)
    setup_date = Column(DateTime, default=utc_now)

class GroupStrike(Base):
    __tablename__ = "zenith_group_strikes"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    chat_id = Column(BigInteger, index=True)
    strike_count = Column(Integer, default=0)
    last_violation = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_user_chat_uc'),)

class NewMember(Base):
    __tablename__ = "zenith_new_members"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    chat_id = Column(BigInteger, index=True)
    joined_at = Column(DateTime, default=utc_now)
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_new_member_chat_uc'),)