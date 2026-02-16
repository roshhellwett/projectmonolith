from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

CryptoBase = declarative_base()

class Subscription(CryptoBase):
    __tablename__ = "crypto_subscriptions"
    user_id = Column(BigInteger, primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ActivationKey(CryptoBase):
    __tablename__ = "crypto_activation_keys"
    key_string = Column(String(50), primary_key=True)
    duration_days = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))