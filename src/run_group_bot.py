import asyncio
import html
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.config import GROUP_BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL
from core.database import dispose_engine
from core.logger import setup_logger
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_group_bot.group_app import cmd_forgive, cmd_reset, handle_message, handle_new_member
from zenith_group_bot.pro_handlers import (
    cmd_addword,
    cmd_analytics,
    cmd_antiraid,
    cmd_auditlog,
    cmd_delschedule,
    cmd_delword,
    cmd_schedule,
    cmd_schedules,
    cmd_welcome,
    cmd_welcomeoff,
    cmd_wordlist,
)
from zenith_group_bot.repository import (
    ScheduleRepo,
    SettingsRepo,
)
from zenith_group_bot.setup_flow import cmd_setup, setup_callback
from zenith_group_bot.ui import get_admin_dashboard, get_back_button

logger = setup_logger("SVC_GROUP")
router = APIRouter()

bot_app = None
bg_tasks = []


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await update.message.reply_text(
            "👋 Use <code>/setup</code> in your group to get started.\n" "Message me in DMs for the dashboard.",
            parse_mode="HTML",
        )

    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    groups = await SettingsRepo.get_owned_groups(user_id)
    days_left = await SubscriptionRepo.get_days_left(user_id)

    max_groups = 5 if is_pro else 1
    if is_pro:
        status = f"💎 <b>PRO ACTIVE</b> — {days_left} day{'s' if days_left != 1 else ''} remaining"
    else:
        status = "🆓 <b>FREE TIER</b> — 1 group, basic protection"

    active = sum(1 for g in groups if g.is_active)
    text = (
        f"<b>🛡️ ZENITH GROUP HQ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{status}\n"
        f"<b>Groups:</b> {active}/{max_groups} active\n\n"
        f"<b>Commands:</b>\n"
        f"• <code>/setup</code> — Configure a group (in-group)\n"
        f"• <code>/activate [KEY]</code> — Activate Pro\n"
    )
    if is_pro:
        text += (
            "\n<b>Pro Commands</b> (use in group):\n"
            "• <code>/addword</code> / <code>/delword</code> — Custom filters\n"
            "• <code>/antiraid</code> — Anti-raid shield\n"
            "• <code>/analytics</code> — Moderation stats\n"
            "• <code>/schedule</code> — Scheduled messages\n"
            "• <code>/welcome</code> — Welcome messages\n"
            "• <code>/auditlog</code> — Action history"
        )

    await update.message.reply_text(
        text,
        reply_markup=get_admin_dashboard(is_pro, groups),
        parse_mode="HTML",
    )


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "🔑 <b>Activate Pro</b>\n\n" "<b>Usage:</b> <code>/activate [YOUR_KEY]</code>",
            parse_mode="HTML",
        )
    key = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key)
    await update.message.reply_text(msg, parse_mode="HTML")


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("setup_"):
        return await setup_callback(update, context)

    try:
        is_pro = await SubscriptionRepo.is_pro(user_id)

        if data == "grp_main_menu":
            groups = await SettingsRepo.get_owned_groups(user_id)
            days_left = await SubscriptionRepo.get_days_left(user_id)
            max_groups = 5 if is_pro else 1
            status = f"💎 <b>PRO</b> — {days_left}d remaining" if is_pro else "🆓 <b>FREE</b>"
            active = sum(1 for g in groups if g.is_active)
            text = (
                f"<b>🛡️ ZENITH GROUP HQ</b>\n" f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n" f"{status} | {active}/{max_groups} groups"
            )
            await query.edit_message_text(
                text,
                reply_markup=get_admin_dashboard(is_pro, groups),
                parse_mode="HTML",
            )

        elif data == "grp_status":
            days = await SubscriptionRepo.get_days_left(user_id)
            if is_pro:
                text = (
                    "💎 <b>PRO SUBSCRIPTION</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"<b>Status:</b> ✅ Active\n<b>Remaining:</b> {days} days\n\n"
                    "<b>Pro Benefits:</b>\n"
                    "• Up to 5 protected groups\n"
                    "• Custom word filters (200/group)\n"
                    "• Anti-raid lockdown shield\n"
                    "• Moderation analytics dashboard\n"
                    "• Scheduled announcements\n"
                    "• Custom welcome messages\n"
                    "• Full audit log"
                )
            else:
                text = (
                    "🆓 <b>FREE TIER</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "<b>Limits:</b>\n"
                    "• 1 group only\n• Default word list\n• Basic moderation\n\n"
                    "<code>/activate [KEY]</code>"
                )
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif data == "grp_list":
            groups = await SettingsRepo.get_owned_groups(user_id)
            if not groups:
                text = "📋 <b>My Groups</b>\n\nNo groups configured. Use /setup in your group."
            else:
                lines = ["📋 <b>MY GROUPS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
                for g in groups:
                    status = "✅ Active" if g.is_active else "⏸️ Inactive"
                    name = g.group_name or f"Group {g.chat_id}"
                    lines.append(f"• <b>{html.escape(name)}</b> — {status}")
                text = "\n".join(lines)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif data in (
            "grp_analytics_pick",
            "grp_audit_pick",
            "grp_words_help",
            "grp_schedule_help",
            "grp_welcome_help",
        ):
            help_texts = {
                "grp_analytics_pick": "📊 <b>Analytics</b>\n\nUse in your group:\n<code>/analytics</code>",
                "grp_audit_pick": "📜 <b>Audit Log</b>\n\nUse in your group:\n<code>/auditlog [count]</code>",
                "grp_words_help": "📝 <b>Custom Words</b>\n\nUse in group:\n<code>/addword [word]</code>\n<code>/delword [word]</code>\n<code>/wordlist</code>",
                "grp_schedule_help": "⏰ <b>Schedules</b>\n\nUse in group:\n<code>/schedule HH:MM [message]</code>\n<code>/schedules</code>\n<code>/delschedule [id]</code>",
                "grp_welcome_help": "👋 <b>Welcome</b>\n\nUse in group:\n<code>/welcome Hello {name}!</code>\n<code>/welcomeoff</code>",
            }
            await query.edit_message_text(
                help_texts[data],
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

    except Exception as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Dashboard error: {e}")


async def scheduled_message_loop():
    while True:
        try:
            now = datetime.now(UTC)
            due = await ScheduleRepo.get_due_messages(now.hour, now.minute)
            for msg in due:
                try:
                    await bot_app.bot.send_message(
                        chat_id=msg.chat_id,
                        text=msg.message_text,
                        parse_mode="HTML",
                    )
                    await ScheduleRepo.mark_sent(msg.id)
                except Exception as e:
                    logger.warning(f"Scheduled msg send failed (chat {msg.chat_id}): {e}")
        except Exception as e:
            logger.error(f"Scheduled loop error: {e}")
        await asyncio.sleep(60)


async def start_service():
    global bot_app, bg_tasks
    if not GROUP_BOT_TOKEN:
        logger.warning("GROUP_BOT_TOKEN missing! Group Service disabled.")
        return

    bot_app = ApplicationBuilder().token(GROUP_BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("setup", cmd_setup))
    bot_app.add_handler(CommandHandler("forgive", cmd_forgive))
    bot_app.add_handler(CommandHandler("reset", cmd_reset))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))

    bot_app.add_handler(CommandHandler("addword", cmd_addword))
    bot_app.add_handler(CommandHandler("delword", cmd_delword))
    bot_app.add_handler(CommandHandler("wordlist", cmd_wordlist))
    bot_app.add_handler(CommandHandler("schedule", cmd_schedule))
    bot_app.add_handler(CommandHandler("schedules", cmd_schedules))
    bot_app.add_handler(CommandHandler("delschedule", cmd_delschedule))
    bot_app.add_handler(CommandHandler("welcome", cmd_welcome))
    bot_app.add_handler(CommandHandler("welcomeoff", cmd_welcomeoff))
    bot_app.add_handler(CommandHandler("analytics", cmd_analytics))
    bot_app.add_handler(CommandHandler("auditlog", cmd_auditlog))
    bot_app.add_handler(CommandHandler("antiraid", cmd_antiraid))

    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, handle_message))
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/group/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=Update.ALL_TYPES,
            )
            logger.info("✅ Group Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ Group Bot Webhook Failed: {e}")

    bg_tasks.append(asyncio.create_task(scheduled_message_loop()))
    logger.info("⏰ Scheduled Message Loop: Online")


async def stop_service():
    for task in bg_tasks:
        task.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_engine()


@router.post("/webhook/group/{secret}")
async def group_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Group Webhook Error: {e}")
        return Response(status_code=200)
