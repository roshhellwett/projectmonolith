from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, String, UniqueConstraint

from core.database import Base

CryptoBase = Base


class CryptoUser(CryptoBase):
    __tablename__ = "crypto_users"
    user_id = Column(BigInteger, primary_key=True)
    alerts_enabled = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Subscription(CryptoBase):
    __tablename__ = "crypto_subscriptions"
    user_id = Column(BigInteger, primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ActivationKey(CryptoBase):
    __tablename__ = "crypto_activation_keys"
    key_string = Column(String(50), primary_key=True)
    duration_days = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by = Column(BigInteger, nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SavedAudit(CryptoBase):
    __tablename__ = "crypto_saved_audits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    contract = Column(String(150), nullable=False)
    saved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (UniqueConstraint("user_id", "contract", name="uix_user_contract"),)


class PriceAlert(CryptoBase):
    __tablename__ = "crypto_price_alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    token_id = Column(String(100), nullable=False)
    token_symbol = Column(String(20), nullable=False)
    target_price = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TrackedWallet(CryptoBase):
    __tablename__ = "crypto_tracked_wallets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    wallet_address = Column(String(100), nullable=False)
    label = Column(String(50), default="Unnamed Wallet")
    last_checked_tx = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (UniqueConstraint("user_id", "wallet_address", name="uix_user_wallet"),)


class WatchlistToken(CryptoBase):
    __tablename__ = "crypto_watchlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    token_id = Column(String(100), nullable=False)
    token_symbol = Column(String(20), nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (UniqueConstraint("user_id", "token_id", name="uix_user_watchlist_token"),)


class ReferralCode(CryptoBase):
    __tablename__ = "referral_codes"
    user_id = Column(BigInteger, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    total_redeemed = Column(Integer, default=0)
    bonus_days = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ReferralRedemption(CryptoBase):
    __tablename__ = "referral_redemptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(BigInteger, nullable=False, index=True)
    redeemed_by = Column(BigInteger, nullable=False, unique=True)
    redeemed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class UserFeedback(CryptoBase):
    __tablename__ = "user_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    message = Column(String(2000), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
