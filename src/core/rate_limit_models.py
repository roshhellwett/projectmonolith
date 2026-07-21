"""Rate limit persistence model for surviving restarts."""

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, UniqueConstraint

from core.database import Base


class PersistentRateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(50), nullable=False)
    count = Column(Integer, default=0)
    window_start = Column(DateTime, nullable=False, index=True)

    __table_args__ = (UniqueConstraint("user_id", "action", "window_start", name="uix_rate_limit_key"),)
