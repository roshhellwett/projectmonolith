import html
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import setup_logger
from core.validators import validate_custom_word
from core.animation import send_typing_action
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_group_bot.repository import (
    SettingsRepo, CustomWordRepo, ScheduleRepo,
    WelcomeRepo, AuditLogRepo,
)
from zenith_group_bot.ui import (
    get_confirm_add_word, get_confirm_delete_word,
    get_word_limit_msg, get_pro_feature_msg,
    get_confirm_forgive, get_confirm_reset,
)

logger = setup_logger("GRP_PRO")


async def _check_group_admin_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ This command must be used in a group chat.")
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
        await update.message.reply_text("⚠️ Run /setup first to configure this group.")
        return chat_id, user_id, False

    is_pro = await SubscriptionRepo.is_pro(settings.owner_id)
    if not is_pro:
        await update.message.reply_text(
            "🔒 <b>Pro Feature</b>\n\n"
            "The group owner needs <b>Zenith Pro</b> to unlock this feature.\n"
            "<code>/activate [KEY]</code>",
            parse_mode="HTML",
        )
        return chat_id, user_id, False

    return chat_id, user_id, True


async def cmd_addword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text(
            "📝 <b>Custom Word Filter</b>\n\n"
            "<b>Usage:</b> <code>/addword [WORD]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/addword scam</code>\n\n"
            "Added words will trigger automatic deletion.\n\n"
            "<i>💡 Tip: Use phrases like 'free money' to catch scammers</i>",
            parse_mode="HTML",
        )

    word = " ".join(context.args).lower().strip()
    
    validation = validate_custom_word(word)
    if not validation.is_valid:
        return await update.message.reply_text(
            f"⚠️ <b>Invalid Word</b>\n\n{validation.error_message}",
            parse_mode="HTML"
        )
    
    word = validation.sanitized_value

    count = await CustomWordRepo.count_words(chat_id)
    limit = 200
    if count >= limit:
        msg = get_word_limit_msg(count, limit)
        return await update.message.reply_text(msg, parse_mode="HTML")

    added = await CustomWordRepo.add_word(chat_id, word, user_id)
    if added:
        await update.message.reply_text(
            f"✅ <b>Word Added</b>\n\n"
            f"<code>{html.escape(word)}</code> will now trigger message deletion.\n\n"
            f"<i>Total custom words: {count + 1}/200</i>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "⚠️ <b>Already Added</b>\n\n"
            "This word is already in the filter.",
            parse_mode="HTML",
        )


async def cmd_delword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text(
            "📝 <b>Remove Custom Word</b>\n\n"
            "<b>Usage:</b> <code>/delword [WORD]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/delword scam</code>",
            parse_mode="HTML"
        )

    word = " ".join(context.args).lower().strip()
    
    validation = validate_custom_word(word)
    if not validation.is_valid:
        return await update.message.reply_text(
            f"⚠️ <b>Invalid Word</b>\n\n{validation.error_message}",
            parse_mode="HTML"
        )
    
    word = validation.sanitized_value
    
    removed = await CustomWordRepo.remove_word(chat_id, word)
    
    if removed:
        await update.message.reply_text(
            f"✅ <b>Word Removed</b>\n\n"
            f"<code>{html.escape(word)}</code> is no longer filtered.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "⚠️ <b>Word Not Found</b>\n\n"
            "This word is not in your filter list.\n\n"
            "Use <code>/wordlist</code> to see all filtered words.",
            parse_mode="HTML"
        )


async def cmd_wordlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    words = await CustomWordRepo.get_words(chat_id)
    if not words:
        return await update.message.reply_text(
            "📝 <b>Custom Word Filter</b>\n\nNo custom words added yet.\n"
            "<code>/addword [WORD]</code>",
            parse_mode="HTML",
        )

    word_list = ", ".join(f"<code>{html.escape(w)}</code>" for w in words[:50])
    count = len(words)
    await update.message.reply_text(
        f"📝 <b>Custom Word Filter ({count}/200)</b>\n\n{word_list}",
        parse_mode="HTML",
    )


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args or len(context.args) < 2:
        return await update.message.reply_text(
            "⏰ <b>Scheduled Messages</b>\n\n"
            "<b>Format:</b> <code>/schedule [HH:MM] [MESSAGE]</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/schedule 09:00 Good morning! 🌅</code>\n"
            "• <code>/schedule 20:00 Please read the pinned rules.</code>\n\n"
            "<i>Times are in UTC. Messages repeat daily.</i>",
            parse_mode="HTML",
        )

    time_str = context.args[0]
    try:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError()
    except (ValueError, IndexError):
        return await update.message.reply_text(
            "⚠️ <b>Invalid Time Format</b>\n\n"
            "Use <code>HH:MM</code> in 24-hour format.\n\n"
            "<b>Examples:</b>\n"
            "• 09:00 (9 AM)\n"
            "• 14:30 (2:30 PM)\n"
            "• 23:59 (11:59 PM)",
            parse_mode="HTML"
        )

    message_text = " ".join(context.args[1:])
    if len(message_text) > 1000:
        return await update.message.reply_text(
            "⚠️ <b>Message Too Long</b>\n\n"
            "Message must be under 1000 characters.",
            parse_mode="HTML"
        )

    count = await ScheduleRepo.count_schedules(chat_id)
    limit = 10
    if count >= limit:
        return await update.message.reply_text(
            "⚠️ <b>Schedule Limit Reached</b>\n\n"
            f"You've reached the maximum of {limit} scheduled messages.\n\n"
            "Delete some to add more.",
            parse_mode="HTML"
        )

    sid = await ScheduleRepo.add_schedule(chat_id, user_id, message_text, hour, minute)
    await update.message.reply_text(
        f"✅ <b>Message Scheduled</b>\n\n"
        f"⏰ <b>Time:</b> {hour:02d}:{minute:02d} UTC (daily)\n"
        f"📝 <b>Message:</b> {html.escape(message_text[:100])}...\n\n"
        f"<b>ID:</b> <code>{sid}</code>\n\n"
        f"<i>Delete with</i> <code>/delschedule {sid}</code>",
        parse_mode="HTML",
    )


async def cmd_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    items = await ScheduleRepo.get_schedules(chat_id)
    if not items:
        return await update.message.reply_text(
            "⏰ <b>Scheduled Messages</b>\n\nNo active schedules.\n"
            "<code>/schedule 09:00 Good morning!</code>",
            parse_mode="HTML",
        )

    lines = ["⏰ <b>SCHEDULED MESSAGES</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for s in items:
        preview = s.message_text[:60] + "..." if len(s.message_text) > 60 else s.message_text
        lines.append(
            f"<b>#{s.id}</b> — {s.hour:02d}:{s.minute:02d} UTC\n"
            f"  <i>{html.escape(preview)}</i>\n"
        )
    lines.append(f"<i>Delete with</i> <code>/delschedule [ID]</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_delschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text("Usage: <code>/delschedule [ID]</code>", parse_mode="HTML")
    try:
        sid = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("⚠️ Invalid schedule ID.")

    deleted = await ScheduleRepo.delete_schedule(sid, user_id)
    msg = "✅ Schedule removed." if deleted else "⚠️ Schedule not found or not owned by you."
    await update.message.reply_text(msg)


async def cmd_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        return await update.message.reply_text(
            "👋 <b>Custom Welcome Message</b>\n\n"
            "<b>Format:</b> <code>/welcome [MESSAGE]</code>\n\n"
            "<b>Variables:</b>\n"
            "• <code>{name}</code> — User's first name\n"
            "• <code>{username}</code> — User's @username\n"
            "• <code>{group}</code> — Group name\n\n"
            "<b>Example:</b>\n"
            "<code>/welcome Welcome {name}! 👋 Please read the pinned rules.</code>\n\n"
            "<i>Disable with</i> <code>/welcomeoff</code>",
            parse_mode="HTML",
        )

    template = " ".join(context.args)
    if len(template) > 500:
        return await update.message.reply_text("⚠️ Welcome message must be under 500 characters.")

    await WelcomeRepo.set_welcome(chat_id, template)
    preview = template.replace("{name}", "TestUser").replace("{username}", "@testuser").replace("{group}", "MyGroup")
    await update.message.reply_text(
        f"✅ <b>Welcome Message Set</b>\n\n"
        f"<b>Preview:</b>\n<i>{html.escape(preview)}</i>\n\n"
        f"<i>Disable with</i> <code>/welcomeoff</code>",
        parse_mode="HTML",
    )


async def cmd_welcomeoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return
    disabled = await WelcomeRepo.disable_welcome(chat_id)
    msg = "✅ Custom welcome disabled." if disabled else "⚠️ No active welcome config found."
    await update.message.reply_text(msg)


async def cmd_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    day_stats = await AuditLogRepo.count_actions(chat_id, hours=24)
    week_stats = await AuditLogRepo.count_actions(chat_id, hours=168)
    top_violators = await AuditLogRepo.get_top_violators(chat_id, hours=168)
    total = await AuditLogRepo.total_actions(chat_id)

    deleted_24h = day_stats.get("DELETED", 0)
    warned_24h = day_stats.get("WARNED", 0)
    banned_24h = day_stats.get("BANNED", 0)
    quarantine_24h = day_stats.get("QUARANTINE", 0)

    deleted_7d = week_stats.get("DELETED", 0)
    warned_7d = week_stats.get("WARNED", 0)
    banned_7d = week_stats.get("BANNED", 0)

    lines = [
        "<b>📊 MODERATION ANALYTICS</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "<b>Last 24 Hours:</b>",
        f"  🗑️ Messages Deleted: <b>{deleted_24h}</b>",
        f"  ⚠️ Warnings Issued: <b>{warned_24h}</b>",
        f"  🚫 Users Banned: <b>{banned_24h}</b>",
        f"  🛡️ Quarantine Blocks: <b>{quarantine_24h}</b>\n",
        "<b>Last 7 Days:</b>",
        f"  🗑️ Deleted: <b>{deleted_7d}</b> | ⚠️ Warned: <b>{warned_7d}</b> | 🚫 Banned: <b>{banned_7d}</b>\n",
        f"<b>Total All-Time Actions:</b> {total}\n",
    ]

    if top_violators:
        lines.append("<b>🔝 Top Violators (7 Days):</b>")
        for rank, (username, uid, count) in enumerate(top_violators, 1):
            name = f"@{username}" if username else f"<code>{uid}</code>"
            lines.append(f"  {rank}. {name} — <b>{count}</b> violations")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_auditlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    limit = 15
    if context.args:
        try:
            limit = min(int(context.args[0]), 50)
        except ValueError:
            pass

    logs = await AuditLogRepo.get_recent(chat_id, limit=limit)
    if not logs:
        return await update.message.reply_text(
            "📜 <b>Audit Log</b>\n\nNo moderation actions recorded yet.",
            parse_mode="HTML",
        )

    lines = ["<b>📜 MODERATION AUDIT LOG</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    action_icons = {"DELETED": "🗑️", "WARNED": "⚠️", "BANNED": "🚫", "QUARANTINE": "🛡️"}
    for log in logs:
        icon = action_icons.get(log.action, "📌")
        name = f"@{log.username}" if log.username else f"ID:{log.user_id}"
        time_str = log.created_at.strftime("%d/%m %H:%M") if log.created_at else "?"
        reason_short = (log.reason[:40] + "...") if log.reason and len(log.reason) > 40 else (log.reason or "N/A")
        lines.append(f"{icon} <b>{log.action}</b> | {name} | {time_str}\n   <i>{html.escape(reason_short)}</i>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


_raid_mode = {}


def is_raid_mode(chat_id: int) -> bool:
    return _raid_mode.get(chat_id, False)


def set_raid_mode(chat_id: int, active: bool):
    _raid_mode[chat_id] = active


async def cmd_antiraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user_id, ok = await _check_group_admin_pro(update, context)
    if not ok:
        return

    if not context.args:
        status = "🟢 ACTIVE" if is_raid_mode(chat_id) else "⚪ INACTIVE"
        return await update.message.reply_text(
            f"🛡️ <b>Anti-Raid Shield</b>\n\n"
            f"<b>Status:</b> {status}\n\n"
            f"<b>Usage:</b>\n"
            f"• <code>/antiraid on</code> — Enable lockdown\n"
            f"• <code>/antiraid off</code> — Disable lockdown\n\n"
            f"<i>When active: all new members are auto-muted. "
            f"No messages from non-admins for the duration.</i>",
            parse_mode="HTML",
        )

    action = context.args[0].lower()
    if action == "on":
        set_raid_mode(chat_id, True)
        await update.message.reply_text(
            "🛡️ <b>ANTI-RAID LOCKDOWN ACTIVATED</b>\n\n"
            "⚠️ All messages from non-admin members will be deleted.\n"
            "New joins will be auto-restricted.\n\n"
            "<i>Disable with</i> <code>/antiraid off</code>",
            parse_mode="HTML",
        )
        await AuditLogRepo.log_action(chat_id, user_id, update.effective_user.username, "RAID_LOCK_ON", "Anti-raid activated by admin")
    elif action == "off":
        set_raid_mode(chat_id, False)
        await update.message.reply_text(
            "✅ <b>Anti-Raid Lockdown Deactivated</b>\n\n"
            "Normal moderation resumed.",
            parse_mode="HTML",
        )
        await AuditLogRepo.log_action(chat_id, user_id, update.effective_user.username, "RAID_LOCK_OFF", "Anti-raid deactivated by admin")
    else:
        await update.message.reply_text("⚠️ Use <code>/antiraid on</code> or <code>/antiraid off</code>", parse_mode="HTML")
