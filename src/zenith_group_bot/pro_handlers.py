import contextlib

from telegram import Update
from telegram.ext import ContextTypes

from core.logger import setup_logger
from core.subscription import SubscriptionRepo
from core.validators import validate_custom_word
from zenith_group_bot.repository import (
    AuditLogRepo,
    CustomWordRepo,
    ScheduleRepo,
    SettingsRepo,
    WelcomeRepo,
)
from zenith_group_bot.ui import (
    get_addword_result,
    get_antiraid_status_msg,
    get_antiraid_toggle_msg,
    get_confirm_add_word,
    get_confirm_delete_word,
    get_confirm_schedule,
    get_delschedule_result,
    get_delword_help,
    get_delword_result,
    get_schedule_help,
    get_schedule_length_error,
    get_schedule_limit_reached,
    get_schedule_success,
    get_schedule_time_error,
    get_schedules_list,
    get_welcome_help,
    get_welcome_length_error,
    get_welcome_success,
    get_welcomeoff_result,
    get_word_help,
    get_word_limit_msg,
    get_wordlist_msg,
)

logger = setup_logger("GRP_PRO")

# Hardcoded limits
MAX_CUSTOM_WORDS = 200
MAX_SCHEDULED_MESSAGES = 10
MAX_SCHEDULE_MESSAGE_LENGTH = 1000
MAX_WELCOME_LENGTH = 500


async def _check_group_admin_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("This command must be used in a group chat.")
        return None, None, False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ["administrator", "creator"]:
            return chat_id, user_id, False
    except Exception:
        return chat_id, user_id, False

    settings = await SettingsRepo.get_settings(chat_id)
    if not settings:
        await update.message.reply_text("Run /setup first to configure this group.")
        return chat_id, user_id, False

    is_pro = await SubscriptionRepo.is_pro(settings.owner_id)
    if not is_pro:
        await update.message.reply_text(
            "Pro Feature\n\nThe group owner needs Zenith Pro to unlock this feature.\n/activate [KEY]",
            parse_mode="HTML",
        )
        return chat_id, user_id, False

    return chat_id, user_id, True


async def cmd_addword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text(get_word_help(), parse_mode="HTML")

    word = " ".join(context.args).lower().strip()

    validation = validate_custom_word(word)
    if not validation.is_valid:
        return await update.message.reply_text(f"Invalid Word\n\n{validation.error_message}", parse_mode="HTML")

    word = validation.sanitized_value

    count = await CustomWordRepo.count_words(chat_id)
    limit = MAX_CUSTOM_WORDS
    if count >= limit:
        msg = get_word_limit_msg(count, limit)
        return await update.message.reply_text(msg, parse_mode="HTML")

    # Confirmation dialog
    confirm_text, confirm_kb = get_confirm_add_word(word)
    await update.message.reply_text(confirm_text, reply_markup=confirm_kb, parse_mode="HTML")


async def cmd_addword_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    word = query.data.replace("grp_addword_confirm_", "")
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ["administrator", "creator"]:
            return await query.edit_message_text("Admin only.")
    except Exception:
        return await query.edit_message_text("Cannot verify admin status.")

    added = await CustomWordRepo.add_word(chat_id, word, user_id)
    count = await CustomWordRepo.count_words(chat_id)
    msg = get_addword_result(word, count, success=added)
    await query.edit_message_text(msg, parse_mode="HTML")


async def cmd_delword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text(get_delword_help(), parse_mode="HTML")

    word = " ".join(context.args).lower().strip()

    validation = validate_custom_word(word)
    if not validation.is_valid:
        return await update.message.reply_text(f"Invalid Word\n\n{validation.error_message}", parse_mode="HTML")

    word = validation.sanitized_value

    # Confirmation dialog
    confirm_text, confirm_kb = get_confirm_delete_word(word)
    await update.message.reply_text(confirm_text, reply_markup=confirm_kb, parse_mode="HTML")


async def cmd_delword_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    word = query.data.replace("grp_delword_confirm_", "")
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ["administrator", "creator"]:
            return await query.edit_message_text("Admin only.")
    except Exception:
        return await query.edit_message_text("Cannot verify admin status.")

    removed = await CustomWordRepo.remove_word(chat_id, word)
    msg = get_delword_result(word, success=removed)
    await query.edit_message_text(msg, parse_mode="HTML")


async def cmd_wordlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    words = await CustomWordRepo.get_words(chat_id)
    count = len(words)
    msg = get_wordlist_msg(words, count)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args or len(context.args) < 2:
        return await update.message.reply_text(get_schedule_help(), parse_mode="HTML")

    time_str = context.args[0]
    try:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError()
    except (ValueError, IndexError):
        return await update.message.reply_text(get_schedule_time_error(), parse_mode="HTML")

    message_text = " ".join(context.args[1:])
    if len(message_text) > MAX_SCHEDULE_MESSAGE_LENGTH:
        return await update.message.reply_text(get_schedule_length_error(), parse_mode="HTML")

    count = await ScheduleRepo.count_schedules(chat_id)
    limit = MAX_SCHEDULED_MESSAGES
    if count >= limit:
        return await update.message.reply_text(get_schedule_limit_reached(limit), parse_mode="HTML")

    # Confirmation dialog
    confirm_text, confirm_kb = get_confirm_schedule(f"{hour:02d}:{minute:02d}", message_text)
    context.user_data["pending_schedule"] = {
        "chat_id": chat_id,
        "user_id": user_id,
        "message_text": message_text,
        "hour": hour,
        "minute": minute,
    }
    await update.message.reply_text(confirm_text, reply_markup=confirm_kb, parse_mode="HTML")


async def cmd_schedule_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pending = context.user_data.get("pending_schedule")
    if not pending or query.from_user.id != pending.get("user_id"):
        return await query.edit_message_text("Session expired or unauthorized. Try again.")

    try:
        member = await context.bot.get_chat_member(pending["chat_id"], query.from_user.id)
        if member.status not in ["administrator", "creator"]:
            return await query.edit_message_text("Admin only.")
    except Exception:
        return await query.edit_message_text("Cannot verify admin status.")

    context.user_data.pop("pending_schedule", None)
    sid = await ScheduleRepo.add_schedule(
        pending["chat_id"], pending["user_id"], pending["message_text"], pending["hour"], pending["minute"]
    )
    msg = get_schedule_success(pending["hour"], pending["minute"], pending["message_text"], sid)
    await query.edit_message_text(msg, parse_mode="HTML")


async def cmd_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    items = await ScheduleRepo.get_schedules(chat_id)
    msg = get_schedules_list(items)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_delschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text("Usage: /delschedule [ID]")
    try:
        sid = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Invalid schedule ID.")

    deleted = await ScheduleRepo.delete_schedule(sid, user_id)
    msg = get_delschedule_result(deleted)
    await update.message.reply_text(msg)


async def cmd_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text(get_welcome_help(), parse_mode="HTML")

    template = " ".join(context.args)
    if len(template) > MAX_WELCOME_LENGTH:
        return await update.message.reply_text(get_welcome_length_error())

    await WelcomeRepo.set_welcome(chat_id, template)
    preview = template.replace("{name}", "TestUser").replace("{username}", "@testuser").replace("{group}", "MyGroup")
    msg = get_welcome_success(preview)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_welcomeoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return
    disabled = await WelcomeRepo.disable_welcome(chat_id)
    msg = get_welcomeoff_result(disabled)
    await update.message.reply_text(msg)


async def cmd_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    day_stats = await AuditLogRepo.count_actions(chat_id, hours=24)
    week_stats = await AuditLogRepo.count_actions(chat_id, hours=168)
    top_violators = await AuditLogRepo.get_top_violators(chat_id, hours=168)
    total = await AuditLogRepo.total_actions(chat_id)

    from zenith_group_bot.ui import get_analytics_msg

    msg = get_analytics_msg(day_stats, week_stats, total, top_violators)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_auditlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    limit = 15
    if context.args:
        with contextlib.suppress(ValueError):
            limit = min(int(context.args[0]), 50)

    logs = await AuditLogRepo.get_recent(chat_id, limit=limit)
    from zenith_group_bot.ui import get_audit_log_msg

    msg = get_audit_log_msg(logs)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_antiraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    raid_active = await SettingsRepo.get_raid_mode(chat_id)

    if not context.args:
        msg = get_antiraid_status_msg(raid_active)
        return await update.message.reply_text(msg, parse_mode="HTML")

    action = context.args[0].lower()
    if action == "on":
        await SettingsRepo.set_raid_mode(chat_id, True)
        msg = get_antiraid_toggle_msg(activated=True)
        await update.message.reply_text(msg, parse_mode="HTML")
        await AuditLogRepo.log_action(
            chat_id, user_id, update.effective_user.username, "RAID_LOCK_ON", "Anti-raid activated by admin"
        )
    elif action == "off":
        await SettingsRepo.set_raid_mode(chat_id, False)
        msg = get_antiraid_toggle_msg(activated=False)
        await update.message.reply_text(msg, parse_mode="HTML")
        await AuditLogRepo.log_action(
            chat_id, user_id, update.effective_user.username, "RAID_LOCK_OFF", "Anti-raid deactivated by admin"
        )
    else:
        await update.message.reply_text("Use /antiraid on or /antiraid off")
