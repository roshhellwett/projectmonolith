import contextlib

from cachetools import TTLCache
from telegram import ChatPermissions, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from core.logger import setup_logger
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_group_bot.filters import scan_for_abuse, scan_for_spam
from zenith_group_bot.flood_control import is_flooding
from zenith_group_bot.repository import (
    AuditLogRepo,
    CustomWordRepo,
    GroupRepo,
    MemberRepo,
    SettingsRepo,
    WelcomeRepo,
)
from zenith_group_bot.ui import (
    get_confirm_forgive,
    get_confirm_reset,
    get_forgive_admin_error,
    get_forgive_id_error,
    get_forgive_no_target,
    get_forgive_result,
    get_reset_admin_error,
    get_reset_not_configured,
    get_reset_owner_error,
    get_reset_private_error,
    get_reset_result,
    get_violation_notification,
)

logger = setup_logger("GROUP_APP")

_permission_errors = TTLCache(maxsize=1000, ttl=60)
_admin_cache = TTLCache(maxsize=5000, ttl=300)


async def _is_admin_cached(chat_id: int, user_id: int, context) -> bool:
    cache_key = f"{chat_id}_{user_id}"
    if cache_key in _admin_cache:
        return _admin_cache[cache_key]
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ["administrator", "creator"]
        _admin_cache[cache_key] = is_admin
        return is_admin
    except Exception:
        return False


async def _get_ban_threshold(strength: str) -> int:
    return {"low": 5, "medium": 3, "high": 2}.get(strength, 3)


async def _try_delete(message, chat_id: int) -> bool:
    error_key = f"perm_{chat_id}"
    if _permission_errors.get(error_key, 0) >= 3:
        return False
    try:
        await message.delete()
        return True
    except BadRequest as e:
        if "not enough rights" in str(e).lower() or "message can't be deleted" in str(e).lower():
            count = _permission_errors.get(error_key, 0)
            _permission_errors[error_key] = count + 1
            if count + 1 >= 3:
                logger.warning(f"Circuit breaker tripped for chat {chat_id}. Pausing deletions.")
        return False
    except Exception:
        return False


async def _notify_owner(settings, context, user, reason: str):
    with contextlib.suppress(Exception):
        await context.bot.send_message(
            chat_id=settings.owner_id,
            text=get_violation_notification(
                settings.group_name or str(settings.chat_id),
                user.first_name or "",
                user.id,
                reason,
            ),
            parse_mode="HTML",
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user:
        return

    chat_id = msg.chat_id
    user = msg.from_user
    user_id = user.id

    if msg.chat.type not in ("group", "supergroup"):
        return

    if user.is_bot or await _is_admin_cached(chat_id, user_id, context):
        return

    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active:
        return

    text = msg.text or msg.caption or ""
    features = settings.features or "both"
    strength = settings.strength or "medium"
    ban_threshold = await _get_ban_threshold(strength)
    username = user.username or ""

    if await SettingsRepo.get_raid_mode(chat_id) and not await _is_admin_cached(chat_id, user_id, context):
        if await _try_delete(msg, chat_id):
            await AuditLogRepo.log_action(chat_id, user_id, username, "DELETED", "Anti-raid lockdown", context.bot.id)
        return

    is_restricted = await MemberRepo.is_restricted(user_id, chat_id)
    if is_restricted:
        has_link = msg.entities and any(e.type in ("url", "text_link") for e in msg.entities)
        has_media = bool(msg.photo or msg.video or msg.document or msg.animation or msg.sticker)
        if has_link or has_media:
            if await _try_delete(msg, chat_id):
                await AuditLogRepo.log_action(
                    chat_id, user_id, username, "QUARANTINE", "New member link/media block", context.bot.id
                )
                await _notify_owner(settings, context, user, "New member tried to send link/media (quarantine)")
            return

    if features in ("spam", "both") and text and scan_for_spam(text) and await _try_delete(msg, chat_id):
        strikes = await GroupRepo.process_violation(user_id, chat_id)
        await AuditLogRepo.log_action(
            chat_id, user_id, username, "DELETED", f"Spam link detected (strike {strikes})", context.bot.id
        )
        if strikes >= ban_threshold:
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await AuditLogRepo.log_action(
                    chat_id, user_id, username, "BANNED", f"Strike threshold ({ban_threshold}) reached", context.bot.id
                )
            except Exception:
                logger.warning(f"Failed to ban user {user_id} in chat {chat_id} (spam threshold)")
        await _notify_owner(settings, context, user, f"Spam link (Strike {strikes})")
        return

    if features in ("abuse", "both") and text:
        custom_words = None
        owner_is_pro = await SubscriptionRepo.is_pro(settings.owner_id)
        if owner_is_pro:
            custom_words = await CustomWordRepo.get_words(chat_id)

        if scan_for_abuse(text, custom_words=custom_words):
            if await _try_delete(msg, chat_id):
                strikes = await GroupRepo.process_violation(user_id, chat_id)
                await AuditLogRepo.log_action(
                    chat_id,
                    user_id,
                    username,
                    "DELETED",
                    f"Abuse/profanity detected (strike {strikes})",
                    context.bot.id,
                )
                if strikes >= ban_threshold:
                    try:
                        await context.bot.ban_chat_member(chat_id, user_id)
                        await AuditLogRepo.log_action(
                            chat_id,
                            user_id,
                            username,
                            "BANNED",
                            f"Strike threshold ({ban_threshold}) reached",
                            context.bot.id,
                        )
                    except Exception:
                        logger.warning(f"Failed to ban user {user_id} in chat {chat_id} (abuse threshold)")
                await _notify_owner(settings, context, user, f"Abuse detected (Strike {strikes})")
            return

    flooding, flood_reason = is_flooding(user_id, getattr(msg, "media_group_id", None), strength)
    if flooding and await _try_delete(msg, chat_id):
        strikes = await GroupRepo.process_violation(user_id, chat_id)
        await AuditLogRepo.log_action(
            chat_id, user_id, username, "DELETED", f"Flood/spam (strike {strikes})", context.bot.id
        )
        if strikes >= ban_threshold:
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await AuditLogRepo.log_action(
                    chat_id, user_id, username, "BANNED", "Flood + strike threshold", context.bot.id
                )
            except Exception:
                logger.warning(f"Failed to ban user {user_id} in chat {chat_id} (flood threshold)")


async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.new_chat_members:
        return

    chat_id = msg.chat_id
    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active:
        return

    for member in msg.new_chat_members:
        if member.is_bot:
            continue

        if await SettingsRepo.get_raid_mode(chat_id):
            try:
                await context.bot.restrict_chat_member(
                    chat_id,
                    member.id,
                    permissions=ChatPermissions(can_send_messages=False),
                )
                await AuditLogRepo.log_action(
                    chat_id,
                    member.id,
                    member.username,
                    "QUARANTINE",
                    "Anti-raid: auto-restricted on join",
                    context.bot.id,
                )
            except Exception:
                logger.warning(f"Failed to restrict new member {member.id} in raid mode (chat {chat_id})")
            continue

        await MemberRepo.register_new_member(member.id, chat_id)

        owner_is_pro = await SubscriptionRepo.is_pro(settings.owner_id)
        if owner_is_pro:
            welcome_config = await WelcomeRepo.get_welcome(chat_id)
            if welcome_config:
                welcome_text = (
                    welcome_config.message_template.replace("{name}", member.first_name or "there")
                    .replace("{username}", f"@{member.username}" if member.username else member.first_name or "there")
                    .replace("{group}", msg.chat.title or "our group")
                )
                try:
                    if welcome_config.send_dm:
                        await context.bot.send_message(chat_id=member.id, text=welcome_text, parse_mode="HTML")
                    else:
                        await msg.reply_text(welcome_text, parse_mode="HTML")
                except Exception as e:
                    logger.debug(f"Welcome send failed: {e}")


async def cmd_forgive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    if not await _is_admin_cached(update.effective_chat.id, update.effective_user.id, context):
        return await update.message.reply_text(get_forgive_admin_error())

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text(get_forgive_id_error())

    if not target_id:
        return await update.message.reply_text(get_forgive_no_target())

    strikes = await GroupRepo.get_strikes(target_id, update.effective_chat.id)
    target_name = update.message.reply_to_message.from_user.first_name if update.message.reply_to_message else None

    confirm_text, confirm_kb = get_confirm_forgive(target_id, target_name, strikes)
    await update.message.reply_text(confirm_text, reply_markup=confirm_kb, parse_mode="HTML")


async def cmd_forgive_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()
    if not await _is_admin_cached(update.effective_chat.id, query.from_user.id, context):
        return await query.edit_message_text(get_forgive_admin_error())

    user_id = int(query.data.replace("grp_forgive_", ""))
    chat_id = update.effective_chat.id

    forgiven = await GroupRepo.forgive_user(user_id, chat_id)
    await query.edit_message_text(get_forgive_result(forgiven))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text(get_reset_private_error())
    if not await _is_admin_cached(update.effective_chat.id, update.effective_user.id, context):
        return await update.message.reply_text(get_reset_admin_error())

    settings = await SettingsRepo.get_settings(update.effective_chat.id)
    if not settings:
        return await update.message.reply_text(get_reset_not_configured())
    if update.effective_user.id != settings.owner_id:
        return await update.message.reply_text(get_reset_owner_error())

    confirm_text, confirm_kb = get_confirm_reset(settings.group_name)
    await update.message.reply_text(confirm_text, reply_markup=confirm_kb, parse_mode="HTML")


async def cmd_reset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()
    chat_id = update.effective_chat.id
    user_id = query.from_user.id
    settings = await SettingsRepo.get_settings(chat_id)

    if not settings or settings.owner_id != user_id:
        return await query.edit_message_text("Reset failed.")

    wiped = await SettingsRepo.wipe_group_container(chat_id, user_id)
    await query.edit_message_text(get_reset_result(wiped))
