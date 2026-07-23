from datetime import timedelta

from cachetools import TTLCache
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database import AsyncSessionLocal, db_retry
from core.logger import setup_logger
from utils.time_util import utc_now
from zenith_group_bot.models import (
    CustomBannedWord,
    GroupSettings,
    GroupStrike,
    ModerationLog,
    NewMember,
    ScheduledMessage,
    WelcomeConfig,
)

logger = setup_logger("DB_REPO")

settings_cache = TTLCache(maxsize=1000, ttl=300)
quarantine_cache = TTLCache(maxsize=5000, ttl=3600)
join_debounce = TTLCache(maxsize=2000, ttl=60)
custom_words_cache = TTLCache(maxsize=500, ttl=300)


class SettingsRepo:
    @staticmethod
    @db_retry
    async def get_settings(chat_id: int):
        if chat_id in settings_cache:
            return settings_cache[chat_id]
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                settings_cache[chat_id] = record
            return record

    @staticmethod
    @db_retry
    async def get_owned_groups(owner_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.owner_id == owner_id)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def count_owned_groups(owner_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(GroupSettings)
                .where(
                    GroupSettings.owner_id == owner_id,
                    GroupSettings.is_active == True,
                )
            )
            return (await session.execute(stmt)).scalar() or 0

    @staticmethod
    @db_retry
    async def upsert_settings(
        chat_id: int,
        owner_id: int,
        group_name: str,
        features: str = None,
        strength: str = None,
        is_active: bool = None,
        ai_enabled: bool = None,
        crypto_enabled: bool = None,
        faq_knowledge: str = None,
    ):
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(GroupSettings).values(
                chat_id=chat_id,
                owner_id=owner_id,
                group_name=group_name,
                features=features or "both",
                strength=strength or "medium",
                is_active=is_active or False,
            )
            update_dict = {}
            if features:
                update_dict["features"] = features
            if strength:
                update_dict["strength"] = strength
            if is_active is not None:
                update_dict["is_active"] = is_active
            if group_name:
                update_dict["group_name"] = group_name
            if ai_enabled is not None:
                update_dict["ai_enabled"] = ai_enabled
            if crypto_enabled is not None:
                update_dict["crypto_enabled"] = crypto_enabled
            if faq_knowledge is not None:
                update_dict["faq_knowledge"] = faq_knowledge

            if update_dict:
                stmt = stmt.on_conflict_do_update(index_elements=["chat_id"], set_=update_dict)
            else:
                stmt = stmt.on_conflict_do_nothing()

            await session.execute(stmt)
            await session.commit()

            res = await session.execute(select(GroupSettings).where(GroupSettings.chat_id == chat_id))
            record = res.scalar_one()
            settings_cache[chat_id] = record
            return record

    @staticmethod
    @db_retry
    async def get_raid_mode(chat_id: int) -> bool:
        settings = await SettingsRepo.get_settings(chat_id)
        if not settings:
            return False
        if settings.raid_expires_at and utc_now() > settings.raid_expires_at:
            if settings.raid_mode:
                async with AsyncSessionLocal() as session:
                    stmt = update(GroupSettings).where(GroupSettings.chat_id == chat_id).values(raid_mode=False)
                    await session.execute(stmt)
                    await session.commit()
                    settings_cache.pop(chat_id, None)
            return False
        return bool(settings.raid_mode)

    @staticmethod
    @db_retry
    async def set_raid_mode(chat_id: int, active: bool, expires_in_minutes: int = 30):
        async with AsyncSessionLocal() as session:
            expires = utc_now() + timedelta(minutes=expires_in_minutes) if active else None
            stmt = (
                update(GroupSettings)
                .where(GroupSettings.chat_id == chat_id)
                .values(raid_mode=active, raid_expires_at=expires)
            )
            await session.execute(stmt)
            await session.commit()
            settings_cache.pop(chat_id, None)

    @staticmethod
    @db_retry
    async def wipe_group_container(chat_id: int, owner_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = select(GroupSettings).where(GroupSettings.chat_id == chat_id, GroupSettings.owner_id == owner_id)
            if not (await session.execute(stmt)).scalar_one_or_none():
                return False
            await session.execute(delete(GroupStrike).where(GroupStrike.chat_id == chat_id))
            await session.execute(delete(NewMember).where(NewMember.chat_id == chat_id))
            await session.execute(delete(CustomBannedWord).where(CustomBannedWord.chat_id == chat_id))
            await session.execute(delete(ScheduledMessage).where(ScheduledMessage.chat_id == chat_id))
            await session.execute(delete(WelcomeConfig).where(WelcomeConfig.chat_id == chat_id))
            await session.execute(delete(ModerationLog).where(ModerationLog.chat_id == chat_id))
            await session.execute(delete(GroupSettings).where(GroupSettings.chat_id == chat_id))
            await session.commit()
            settings_cache.pop(chat_id, None)
            custom_words_cache.pop(chat_id, None)
            return True


class GroupRepo:
    @staticmethod
    @db_retry
    async def process_violation(user_id: int, chat_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = (
                pg_insert(GroupStrike)
                .values(
                    user_id=user_id,
                    chat_id=chat_id,
                    strike_count=1,
                    last_violation=utc_now(),
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "chat_id"],
                    set_=dict(strike_count=GroupStrike.strike_count + 1, last_violation=utc_now()),
                )
                .returning(GroupStrike.strike_count)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar()

    @staticmethod
    @db_retry
    async def get_strikes(user_id: int, chat_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(GroupStrike).where(GroupStrike.user_id == user_id, GroupStrike.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            return record.strike_count if record else 0

    @staticmethod
    @db_retry
    async def forgive_user(user_id: int, chat_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(GroupStrike).where(GroupStrike.user_id == user_id, GroupStrike.chat_id == chat_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0


class MemberRepo:
    @staticmethod
    @db_retry
    async def register_new_member(user_id: int, chat_id: int):
        cache_key = f"{chat_id}_{user_id}"
        if cache_key in join_debounce:
            return
        join_debounce[cache_key] = True

        async with AsyncSessionLocal() as session:
            stmt = (
                pg_insert(NewMember)
                .values(
                    user_id=user_id,
                    chat_id=chat_id,
                    joined_at=utc_now(),
                )
                .on_conflict_do_update(index_elements=["user_id", "chat_id"], set_=dict(joined_at=utc_now()))
            )
            await session.execute(stmt)
            await session.commit()
            quarantine_cache.pop(cache_key, None)

    @staticmethod
    @db_retry
    async def is_restricted(user_id: int, chat_id: int) -> bool:
        cache_key = f"{chat_id}_{user_id}"
        if quarantine_cache.get(cache_key) == "CLEARED":
            return False
        async with AsyncSessionLocal() as session:
            stmt = select(NewMember).where(NewMember.user_id == user_id, NewMember.chat_id == chat_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record and (utc_now() - record.joined_at) < timedelta(hours=24):
                return True
            quarantine_cache[cache_key] = "CLEARED"
            return False

    @staticmethod
    @db_retry
    async def clear_quarantine(user_id: int, chat_id: int) -> bool:
        cache_key = f"{chat_id}_{user_id}"
        quarantine_cache[cache_key] = "CLEARED"
        async with AsyncSessionLocal() as session:
            stmt = delete(NewMember).where(NewMember.user_id == user_id, NewMember.chat_id == chat_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0


class CustomWordRepo:
    @staticmethod
    @db_retry
    async def add_word(chat_id: int, word: str, added_by: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = (
                pg_insert(CustomBannedWord)
                .values(
                    chat_id=chat_id,
                    word=word.lower().strip(),
                    added_by=added_by,
                )
                .on_conflict_do_nothing()
            )
            result = await session.execute(stmt)
            await session.commit()
            custom_words_cache.pop(chat_id, None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def remove_word(chat_id: int, word: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(CustomBannedWord).where(
                CustomBannedWord.chat_id == chat_id,
                CustomBannedWord.word == word.lower().strip(),
            )
            result = await session.execute(stmt)
            await session.commit()
            custom_words_cache.pop(chat_id, None)
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def get_words(chat_id: int) -> list[str]:
        if chat_id in custom_words_cache:
            return custom_words_cache[chat_id]
        async with AsyncSessionLocal() as session:
            stmt = select(CustomBannedWord.word).where(CustomBannedWord.chat_id == chat_id)
            rows = (await session.execute(stmt)).scalars().all()
            custom_words_cache[chat_id] = list(rows)
            return list(rows)

    @staticmethod
    @db_retry
    async def count_words(chat_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(CustomBannedWord)
                .where(
                    CustomBannedWord.chat_id == chat_id,
                )
            )
            return (await session.execute(stmt)).scalar() or 0


class ScheduleRepo:
    @staticmethod
    @db_retry
    async def add_schedule(chat_id: int, owner_id: int, text: str, hour: int, minute: int = 0) -> int:
        async with AsyncSessionLocal() as session:
            msg = ScheduledMessage(
                chat_id=chat_id,
                owner_id=owner_id,
                message_text=text,
                hour=hour,
                minute=minute,
            )
            session.add(msg)
            await session.commit()
            return msg.id

    @staticmethod
    @db_retry
    async def get_schedules(chat_id: int) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(ScheduledMessage).where(
                ScheduledMessage.chat_id == chat_id,
                ScheduledMessage.is_active == True,
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def delete_schedule(schedule_id: int, owner_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(ScheduledMessage).where(
                ScheduledMessage.id == schedule_id,
                ScheduledMessage.owner_id == owner_id,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    @db_retry
    async def count_schedules(chat_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(ScheduledMessage)
                .where(
                    ScheduledMessage.chat_id == chat_id,
                    ScheduledMessage.is_active == True,
                )
            )
            return (await session.execute(stmt)).scalar() or 0

    @staticmethod
    @db_retry
    async def get_due_messages(current_hour: int, current_minute: int) -> list:
        async with AsyncSessionLocal() as session:
            now = utc_now()
            one_hour_ago = now - timedelta(hours=1)
            stmt = (
                select(ScheduledMessage)
                .where(
                    ScheduledMessage.is_active == True,
                    ScheduledMessage.hour == current_hour,
                    ScheduledMessage.minute == current_minute,
                )
                .filter((ScheduledMessage.last_sent == None) | (ScheduledMessage.last_sent < one_hour_ago))
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def mark_sent(schedule_id: int):
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ScheduledMessage)
                .where(
                    ScheduledMessage.id == schedule_id,
                )
                .values(last_sent=utc_now())
            )
            await session.execute(stmt)
            await session.commit()


class WelcomeRepo:
    @staticmethod
    @db_retry
    async def set_welcome(chat_id: int, template: str, send_dm: bool = False):
        async with AsyncSessionLocal() as session:
            stmt = (
                pg_insert(WelcomeConfig)
                .values(
                    chat_id=chat_id,
                    message_template=template,
                    send_dm=send_dm,
                    is_active=True,
                    updated_at=utc_now(),
                )
                .on_conflict_do_update(
                    index_elements=["chat_id"],
                    set_=dict(message_template=template, send_dm=send_dm, is_active=True, updated_at=utc_now()),
                )
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    @db_retry
    async def get_welcome(chat_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(WelcomeConfig).where(
                WelcomeConfig.chat_id == chat_id,
                WelcomeConfig.is_active == True,
            )
            return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    @db_retry
    async def disable_welcome(chat_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = update(WelcomeConfig).where(WelcomeConfig.chat_id == chat_id).values(is_active=False)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0


class AuditLogRepo:
    @staticmethod
    @db_retry
    async def log_action(chat_id: int, user_id: int, username: str, action: str, reason: str, moderator_id: int = None):
        async with AsyncSessionLocal() as session:
            session.add(
                ModerationLog(
                    chat_id=chat_id,
                    user_id=user_id,
                    username=username,
                    action=action,
                    reason=reason,
                    moderator_id=moderator_id,
                )
            )
            await session.commit()

    @staticmethod
    @db_retry
    async def get_recent(chat_id: int, limit: int = 20) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ModerationLog)
                .where(ModerationLog.chat_id == chat_id)
                .order_by(ModerationLog.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    @db_retry
    async def count_actions(chat_id: int, hours: int = 24) -> dict:
        async with AsyncSessionLocal() as session:
            cutoff = utc_now() - timedelta(hours=hours)
            stmt = (
                select(
                    ModerationLog.action,
                    func.count().label("cnt"),
                )
                .where(
                    ModerationLog.chat_id == chat_id,
                    ModerationLog.created_at >= cutoff,
                )
                .group_by(ModerationLog.action)
            )
            rows = (await session.execute(stmt)).all()
            return {row[0]: row[1] for row in rows}

    @staticmethod
    @db_retry
    async def get_top_violators(chat_id: int, hours: int = 168, limit: int = 5) -> list:
        async with AsyncSessionLocal() as session:
            cutoff = utc_now() - timedelta(hours=hours)
            stmt = (
                select(
                    ModerationLog.username,
                    ModerationLog.user_id,
                    func.count().label("violations"),
                )
                .where(
                    ModerationLog.chat_id == chat_id,
                    ModerationLog.created_at >= cutoff,
                )
                .group_by(
                    ModerationLog.username,
                    ModerationLog.user_id,
                )
                .order_by(func.count().desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).all()

    @staticmethod
    @db_retry
    async def total_actions(chat_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(ModerationLog)
                .where(
                    ModerationLog.chat_id == chat_id,
                )
            )
            return (await session.execute(stmt)).scalar() or 0
