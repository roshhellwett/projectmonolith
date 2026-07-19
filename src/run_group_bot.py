import asyncio
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
from core.gateway import attach_gateway
from core.logger import setup_logger
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_group_bot.group_app import (
    cmd_forgive,
    cmd_forgive_confirm,
    cmd_reset,
    cmd_reset_confirm,
    handle_message,
    handle_new_member,
)
from zenith_group_bot.pro_handlers import (
    cmd_addword,
    cmd_addword_confirm,
    cmd_analytics,
    cmd_antiraid,
    cmd_auditlog,
    cmd_delschedule,
    cmd_delword,
    cmd_delword_confirm,
    cmd_schedule,
    cmd_schedule_confirm,
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
from zenith_group_bot.ui import (
    get_activate_help,
    get_admin_dashboard,
    get_back_button,
    get_dashboard_help_msg,
    get_dashboard_main_msg,
    get_group_list_msg,
    get_start_group_msg,
    get_status_msg,
)

logger = setup_logger("SVC_GROUP")
router = APIRouter()

bot_app = None
bg_tasks = []


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await update.message.reply_text(get_start_group_msg())

    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    groups = await SettingsRepo.get_owned_groups(user_id)
    days_left = await SubscriptionRepo.get_days_left(user_id)

    text = get_dashboard_main_msg(is_pro, groups, days_left)
    await update.message.reply_text(
        text,
        reply_markup=get_admin_dashboard(is_pro, groups),
        parse_mode="HTML",
    )


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(get_activate_help(), parse_mode="HTML")
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
            text = get_dashboard_main_msg(is_pro, groups, days_left)
            await query.edit_message_text(
                text,
                reply_markup=get_admin_dashboard(is_pro, groups),
                parse_mode="HTML",
            )

        elif data == "grp_status":
            days = await SubscriptionRepo.get_days_left(user_id)
            text = get_status_msg(is_pro, days)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif data == "grp_list":
            groups = await SettingsRepo.get_owned_groups(user_id)
            text = get_group_list_msg(groups)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif data in (
            "grp_analytics_pick",
            "grp_audit_pick",
            "grp_words_help",
            "grp_schedule_help",
            "grp_welcome_help",
        ):
            text = get_dashboard_help_msg(data)
            await query.edit_message_text(
                text,
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
    attach_gateway(bot_app, "Group")

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

    bot_app.add_handler(CallbackQueryHandler(cmd_addword_confirm, pattern=r"^grp_addword_confirm_"))
    bot_app.add_handler(CallbackQueryHandler(cmd_delword_confirm, pattern=r"^grp_delword_confirm_"))
    bot_app.add_handler(CallbackQueryHandler(cmd_schedule_confirm, pattern=r"^grp_schedule_confirm_"))
    bot_app.add_handler(CallbackQueryHandler(cmd_forgive_confirm, pattern=r"^grp_forgive_"))
    bot_app.add_handler(CallbackQueryHandler(cmd_reset_confirm, pattern=r"^grp_reset_confirm$"))
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


async def stop_service(dispose_db: bool = False):
    for task in bg_tasks:
        task.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    if dispose_db:
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
