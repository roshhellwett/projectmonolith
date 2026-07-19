import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from core.database import AsyncSessionLocal, db_retry
from core.logger import setup_logger
from zenith_crypto_bot.models import (
    ActivationKey,
    CryptoUser,
    PriceAlert,
    SavedAudit,
    Subscription,
    TrackedWallet,
    WatchlistToken,
)

logger = setup_logger("CRYPTO_DB")


class SubscriptionRepo:
    @staticmethod
    @db_retry
    async def register_user(user_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CryptoUser).where(CryptoUser.user_id == user_id))
            if not res.scalar_one_or_none():
                session.add(CryptoUser(user_id=user_id, alerts_enabled=False))
                await session.commit()

    @staticmethod
    @db_retry
    async def toggle_alerts(user_id: int, enable: bool):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CryptoUser).where(CryptoUser.user_id == user_id))
            user = res.scalar_one_or_none()
            if user:
                user.alerts_enabled = enable
            else:
                session.add(CryptoUser(user_id=user_id, alerts_enabled=enable))
            await session.commit()

    @staticmethod
    @db_retry
    async def get_alert_subscribers():
        async with AsyncSessionLocal() as session:
            now = datetime.now(UTC)
            users_res = await session.execute(select(CryptoUser.user_id).where(CryptoUser.alerts_enabled == True))
            all_alert_users = set([r[0] for r in users_res.all()])
            pro_res = await session.execute(select(Subscription.user_id).where(Subscription.expires_at > now))
            all_pro_users = set([r[0] for r in pro_res.all()])
            pro_subscribers = list(all_alert_users.intersection(all_pro_users))
            free_subscribers = list(all_alert_users.difference(all_pro_users))
            return free_subscribers, pro_subscribers

    @staticmethod
    @db_retry
    async def generate_key(days: int, validity_days: int = 365) -> str:
        new_key = f"ZENITH-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
        async with AsyncSessionLocal() as session:
            expires_at = datetime.now(UTC) + timedelta(days=validity_days)
            session.add(ActivationKey(key_string=new_key, duration_days=days, expires_at=expires_at))
            await session.commit()
        return new_key

    @staticmethod
    @db_retry
    async def redeem_key(user_id: int, key_string: str) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session, session.begin():
            res = await session.execute(
                select(ActivationKey).where(ActivationKey.key_string == key_string).with_for_update()
            )
            key = res.scalar_one_or_none()
            if not key or key.is_used:
                return False, "❌ <b>Activation Failed:</b> Invalid or already used key."

            if key.expires_at and key.expires_at <= datetime.now(UTC):
                return False, "❌ <b>Activation Failed:</b> This key has expired."

            key.is_used = True
            key.used_by = user_id
            key.used_at = datetime.now(UTC)

            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id).with_for_update())
            sub = res.scalar_one_or_none()
            now = datetime.now(UTC)
            add_on = timedelta(days=key.duration_days)
            if sub and sub.expires_at > now:
                sub.expires_at += add_on
            else:
                new_expiry = now + add_on
                if sub:
                    sub.expires_at = new_expiry
                else:
                    session.add(Subscription(user_id=user_id, expires_at=new_expiry))
            return True, (
                f"💎 <b>ZENITH PRO ACTIVATED</b>\n\n"
                f"✅ Successfully applied <b>{key.duration_days} days</b> to your account.\n"
                f"Enjoy zero-latency intelligence."
            )

    @staticmethod
    @db_retry
    async def get_days_left(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = res.scalar_one_or_none()
            now = datetime.now(UTC)
            if not sub or sub.expires_at <= now:
                return 0
            remaining = sub.expires_at - now
            return remaining.days + (1 if remaining.seconds > 0 else 0)

    @staticmethod
    @db_retry
    async def is_pro(user_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = res.scalar_one_or_none()
            if not sub:
                return False
            return sub.expires_at > datetime.now(UTC)

    @staticmethod
    @db_retry
    async def extend_subscription(user_id: int, days: int = 30) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session, session.begin():
            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id).with_for_update())
            sub = res.scalar_one_or_none()
            now = datetime.now(UTC)
            add_on = timedelta(days=days)
            if sub:
                base = sub.expires_at if sub.expires_at > now else now
                sub.expires_at = base + add_on
            else:
                session.add(Subscription(user_id=user_id, expires_at=now + add_on))
            new_expiry = sub.expires_at if sub else now + add_on
            return True, (
                f"✅ <b>Subscription Extended</b>\n\n"
                f"<b>User:</b> <code>{user_id}</code>\n"
                f"<b>Added:</b> {days} days\n"
                f"<b>New Expiry:</b> {new_expiry.strftime('%d %b %Y %H:%M UTC')}"
            )

    @staticmethod
    @db_retry
    async def revoke_subscription(user_id: int) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session, session.begin():
            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id).with_for_update())
            sub = res.scalar_one_or_none()
            if not sub:
                return False, "⚠️ No subscription found for this user."

            past_date = datetime(2000, 1, 1, tzinfo=UTC)
            sub.expires_at = past_date

            return True, (
                f"✅ <b>Subscription Revoked</b>\n\n"
                f"<b>User:</b> <code>{user_id}</code>\n"
                f"<b>Status:</b> Revoked\n"
                f"<b>Previous expiry:</b> Set to past date"
            )

    @staticmethod
    @db_retry
    async def get_expiring_users(within_hours: int = 72) -> list:
        async with AsyncSessionLocal() as session:
            now = datetime.now(UTC)
            cutoff = now + timedelta(hours=within_hours)
            stmt = select(Subscription).where(Subscription.expires_at > now, Subscription.expires_at <= cutoff)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def get_just_expired_users(within_hours: int = 1) -> list:
        async with AsyncSessionLocal() as session:
            now = datetime.now(UTC)
            cutoff = now - timedelta(hours=within_hours)
            stmt = select(Subscription).where(Subscription.expires_at <= now, Subscription.expires_at >= cutoff)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def save_audit(user_id: int, contract: str):
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(SavedAudit).where(SavedAudit.user_id == user_id, SavedAudit.contract == contract[:100])
            )
            audit = res.scalar_one_or_none()
            if audit:
                audit.saved_at = datetime.now(UTC)
            else:
                session.add(SavedAudit(user_id=user_id, contract=contract[:100], saved_at=datetime.now(UTC)))
            await session.commit()
            count_stmt = select(SavedAudit).where(SavedAudit.user_id == user_id).order_by(SavedAudit.saved_at.desc())
            audits = (await session.execute(count_stmt)).scalars().all()
            if len(audits) > 10:
                for extra_audit in audits[10:]:
                    await session.delete(extra_audit)
            await session.commit()

    @staticmethod
    @db_retry
    async def get_saved_audits(user_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(SavedAudit).where(SavedAudit.user_id == user_id).order_by(SavedAudit.saved_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def get_audit_by_id(user_id: int, audit_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(SavedAudit).where(SavedAudit.user_id == user_id, SavedAudit.id == audit_id)
            return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    @db_retry
    async def delete_audit(user_id: int, audit_id: int):
        async with AsyncSessionLocal() as session:
            stmt = delete(SavedAudit).where(SavedAudit.user_id == user_id, SavedAudit.id == audit_id)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    @db_retry
    async def clear_all_audits(user_id: int):
        async with AsyncSessionLocal() as session:
            stmt = delete(SavedAudit).where(SavedAudit.user_id == user_id)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    @db_retry
    async def set_groq_key(user_id: int, api_key: str) -> None:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CryptoUser).where(CryptoUser.user_id == user_id))
            user = res.scalar_one_or_none()
            if user:
                user.groq_api_key = api_key
            else:
                session.add(CryptoUser(user_id=user_id, groq_api_key=api_key))
            await session.commit()

    @staticmethod
    @db_retry
    async def get_groq_key(user_id: int) -> str | None:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CryptoUser).where(CryptoUser.user_id == user_id))
            user = res.scalar_one_or_none()
            return user.groq_api_key if user and user.groq_api_key else None

    @staticmethod
    @db_retry
    async def delete_groq_key(user_id: int) -> None:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(CryptoUser).where(CryptoUser.user_id == user_id))
            user = res.scalar_one_or_none()
            if user:
                user.groq_api_key = None
            else:
                session.add(CryptoUser(user_id=user_id, groq_api_key=None))
            await session.commit()

    @staticmethod
    @db_retry
    async def get_user_ai_context(user_id: int) -> str:
        async with AsyncSessionLocal() as session:
            parts = []

            sub_res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = sub_res.scalar_one_or_none()
            now = datetime.now(UTC)
            if sub and sub.expires_at > now:
                days = (sub.expires_at - now).days + 1
                parts.append(f"Subscription: Pro ({days} days left)")
            else:
                parts.append("Subscription: Free tier")

            watch_res = await session.execute(select(WatchlistToken).where(WatchlistToken.user_id == user_id))
            tokens = watch_res.scalars().all()
            if tokens:
                items = []
                for t in tokens[:10]:
                    items.append(f"{t.token_symbol} x{t.quantity} @ ${t.entry_price:,.2f}")
                parts.append("Portfolio: " + "; ".join(items))
            else:
                parts.append("Portfolio: Empty")

            alert_count = await session.execute(
                select(PriceAlert).where(PriceAlert.user_id == user_id, PriceAlert.is_triggered == False)
            )
            alert_total = len(alert_count.scalars().all())
            parts.append(f"Active Alerts: {alert_total}")

            wallet_total = await session.execute(select(TrackedWallet).where(TrackedWallet.user_id == user_id))
            parts.append(f"Tracked Wallets: {len(wallet_total.scalars().all())}")

            audit_total = await session.execute(select(SavedAudit).where(SavedAudit.user_id == user_id))
            parts.append(f"Saved Audits: {len(audit_total.scalars().all())}")

            return "\n".join(parts)


class PriceAlertRepo:
    @staticmethod
    @db_retry
    async def create_alert(
        user_id: int, token_id: str, token_symbol: str, target_price: float, direction: str
    ) -> PriceAlert:
        async with AsyncSessionLocal() as session:
            alert = PriceAlert(
                user_id=user_id,
                token_id=token_id,
                token_symbol=token_symbol.upper(),
                target_price=target_price,
                direction=direction,
            )
            session.add(alert)
            await session.commit()
            await session.refresh(alert)
            return alert

    @staticmethod
    @db_retry
    async def get_user_alerts(user_id: int) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(PriceAlert)
                .where(PriceAlert.user_id == user_id, PriceAlert.is_triggered == False)
                .order_by(PriceAlert.created_at.desc())
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def get_all_active_alerts() -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(PriceAlert).where(PriceAlert.is_triggered == False)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def trigger_alert(alert_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(PriceAlert).where(PriceAlert.id == alert_id)
            alert = (await session.execute(stmt)).scalar_one_or_none()
            if alert:
                alert.is_triggered = True
                await session.commit()

    @staticmethod
    @db_retry
    async def delete_alert(user_id: int, alert_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(PriceAlert).where(PriceAlert.user_id == user_id, PriceAlert.id == alert_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def count_user_alerts(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(PriceAlert)
                .where(PriceAlert.user_id == user_id, PriceAlert.is_triggered == False)
            )
            result = await session.execute(stmt)
            return result.scalar() or 0


class WalletTrackerRepo:
    @staticmethod
    @db_retry
    async def add_wallet(user_id: int, wallet_address: str, label: str = "Unnamed Wallet") -> bool:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(TrackedWallet).where(
                    TrackedWallet.user_id == user_id, TrackedWallet.wallet_address == wallet_address.lower()
                )
            )
            if res.scalar_one_or_none():
                return False
            session.add(TrackedWallet(user_id=user_id, wallet_address=wallet_address.lower(), label=label[:50]))
            await session.commit()
            return True

    @staticmethod
    @db_retry
    async def get_user_wallets(user_id: int) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(TrackedWallet).where(TrackedWallet.user_id == user_id).order_by(TrackedWallet.created_at.desc())
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def get_all_tracked_wallets() -> list:
        async with AsyncSessionLocal() as session:
            now = datetime.now(UTC)
            stmt = (
                select(TrackedWallet)
                .join(Subscription, TrackedWallet.user_id == Subscription.user_id)
                .where(Subscription.expires_at > now)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def remove_wallet(user_id: int, wallet_address: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(TrackedWallet).where(
                TrackedWallet.user_id == user_id, TrackedWallet.wallet_address == wallet_address.lower()
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def update_last_tx(wallet_id: int, tx_hash: str):
        async with AsyncSessionLocal() as session:
            stmt = select(TrackedWallet).where(TrackedWallet.id == wallet_id)
            wallet = (await session.execute(stmt)).scalar_one_or_none()
            if wallet:
                wallet.last_checked_tx = tx_hash
                await session.commit()

    @staticmethod
    @db_retry
    async def count_user_wallets(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(func.count()).select_from(TrackedWallet).where(TrackedWallet.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar() or 0


class WatchlistRepo:
    @staticmethod
    @db_retry
    async def add_token(
        user_id: int, token_id: str, token_symbol: str, entry_price: float, quantity: float = 1.0
    ) -> bool:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(WatchlistToken).where(WatchlistToken.user_id == user_id, WatchlistToken.token_id == token_id)
            )
            token = res.scalar_one_or_none()
            if token:
                token.entry_price = entry_price
                token.quantity = quantity
            else:
                session.add(
                    WatchlistToken(
                        user_id=user_id,
                        token_id=token_id,
                        token_symbol=token_symbol.upper(),
                        entry_price=entry_price,
                        quantity=quantity,
                    )
                )
            await session.commit()
            return True

    @staticmethod
    @db_retry
    async def get_watchlist(user_id: int) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(WatchlistToken)
                .where(WatchlistToken.user_id == user_id)
                .order_by(WatchlistToken.created_at.desc())
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def remove_token(user_id: int, token_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(WatchlistToken).where(WatchlistToken.user_id == user_id, WatchlistToken.token_id == token_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def count_watchlist(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(func.count()).select_from(WatchlistToken).where(WatchlistToken.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar() or 0
