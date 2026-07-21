import asyncio
import contextlib
from datetime import UTC, datetime
from html import escape

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.config import GROUP_BOT_TOKEN
from core.database import dispose_engine
from core.error_handler import handle_bot_error
from core.gateway import attach_gateway, setup_bot_webhook
from core.logger import setup_logger
from core.webhook_router import register_bot_webhook
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
    AuditLogRepo,
    GroupRepo,
    ScheduleRepo,
    SettingsRepo,
)
from zenith_group_bot.setup_flow import cmd_setup, setup_callback
from zenith_group_bot.ui import (
    get_activate_help,
    get_admin_dashboard,
    get_analytics_msg,
    get_audit_log_msg,
    get_back_button,
    get_dashboard_help_msg,
    get_dashboard_main_msg,
    get_forgive_result,
    get_group_list_msg,
    get_group_picker,
    get_group_settings_keyboard,
    get_reset_result,
    get_start_group_msg,
    get_status_msg,
)

logger = setup_logger("SVC_GROUP")

bot_app = None
background_tasks = set()


def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


async def safe_loop(name, coro):
    while True:
        try:
            await coro()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Loop '{name}' crashed: {e}")
            await asyncio.sleep(5)


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
        user_id = update.effective_user.id
        is_pro = await SubscriptionRepo.is_pro(user_id)
        if is_pro:
            return await update.message.reply_text(
                "💎 <b>Active Pro Shield</b>\n\nYou are already an active Enterprise Pro Shield member! No activation is needed right now.",
                parse_mode="HTML",
            )
        return await update.message.reply_text(get_activate_help(), parse_mode="HTML")
    key = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key)
    await update.message.reply_text(msg, parse_mode="HTML")


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
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
            await query.edit_message_text(
                text,
                reply_markup=get_group_picker(groups, "grp_config", is_pro),
                parse_mode="HTML",
            )

        elif data in (
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

        elif data == "grp_analytics_pick":
            groups = await SettingsRepo.get_owned_groups(user_id)
            await query.edit_message_text(
                get_dashboard_help_msg(data),
                reply_markup=get_group_picker(groups, "grp_analytics", is_pro),
                parse_mode="HTML",
            )

        elif data == "grp_audit_pick":
            groups = await SettingsRepo.get_owned_groups(user_id)
            await query.edit_message_text(
                get_dashboard_help_msg(data),
                reply_markup=get_group_picker(groups, "grp_audit", is_pro),
                parse_mode="HTML",
            )

        elif data.startswith("grp_analytics_") and data != "grp_analytics_pick":
            chat_id = int(data.rsplit("_", 1)[-1])
            day_stats = await AuditLogRepo.count_actions(chat_id, hours=24)
            week_stats = await AuditLogRepo.count_actions(chat_id, hours=168)
            total = await AuditLogRepo.total_actions(chat_id)
            top_violators = await AuditLogRepo.get_top_violators(chat_id, hours=168, limit=5)
            text = get_analytics_msg(day_stats, week_stats, total, top_violators)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif data.startswith("grp_audit_") and data != "grp_audit_pick":
            chat_id = int(data.rsplit("_", 1)[-1])
            entries = await AuditLogRepo.get_recent(chat_id, limit=20)
            text = get_audit_log_msg(entries)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif data.startswith("grp_config_") or data.startswith("grp_settings_"):
            chat_id = int(data.rsplit("_", 1)[-1])
            settings = await SettingsRepo.get_settings(chat_id)
            settings_dict = {}
            if settings:
                settings_dict = {
                    "anti_spam": "spam" in (settings.features or "both") or settings.features == "both",
                    "anti_abuse": "abuse" in (settings.features or "both") or settings.features == "both",
                    "flood_control": settings.strength != "low",
                }
            name = settings.group_name if settings else f"Group {chat_id}"
            text = f"<b>Group Configuration</b>\n\nCommunity: <b>{escape(name or str(chat_id))}</b>\nSelect settings below to toggle:"
            await query.edit_message_text(
                text,
                reply_markup=get_group_settings_keyboard(chat_id, settings_dict),
                parse_mode="HTML",
            )

        elif (
            data.startswith("grp_toggle_spam_")
            or data.startswith("grp_toggle_abuse_")
            or data.startswith("grp_toggle_flood_")
        ):
            parts = data.rsplit("_", 1)
            chat_id = int(parts[-1])
            toggle_type = data.split("_")[2]
            settings = await SettingsRepo.get_settings(chat_id)
            if settings:
                current_features = settings.features or "both"
                current_strength = settings.strength or "medium"
                if toggle_type == "spam":
                    if current_features == "both":
                        new_features = "abuse"
                    elif current_features == "spam":
                        new_features = "none"
                    elif current_features == "abuse":
                        new_features = "both"
                    else:
                        new_features = "spam"
                    await SettingsRepo.upsert_settings(chat_id, user_id, settings.group_name, features=new_features)
                elif toggle_type == "abuse":
                    if current_features == "both":
                        new_features = "spam"
                    elif current_features == "abuse":
                        new_features = "none"
                    elif current_features == "spam":
                        new_features = "both"
                    else:
                        new_features = "abuse"
                    await SettingsRepo.upsert_settings(chat_id, user_id, settings.group_name, features=new_features)
                elif toggle_type == "flood":
                    new_strength = "low" if current_strength != "low" else "medium"
                    await SettingsRepo.upsert_settings(chat_id, user_id, settings.group_name, strength=new_strength)

            settings = await SettingsRepo.get_settings(chat_id)
            settings_dict = {
                "anti_spam": "spam" in (settings.features or "both") or settings.features == "both"
                if settings
                else True,
                "anti_abuse": "abuse" in (settings.features or "both") or settings.features == "both"
                if settings
                else True,
                "flood_control": (settings.strength != "low") if settings else True,
            }
            name = settings.group_name if settings else f"Group {chat_id}"
            text = f"<b>Group Configuration</b>\n\nCommunity: <b>{escape(name or str(chat_id))}</b>\nSelect settings below to toggle:"
            await query.edit_message_text(
                text,
                reply_markup=get_group_settings_keyboard(chat_id, settings_dict),
                parse_mode="HTML",
            )

        elif data.startswith("grp_forgive_confirm_"):
            target_id = int(data.rsplit("_", 1)[-1])
            groups = await SettingsRepo.get_owned_groups(user_id)
            success = False
            for g in groups:
                if await GroupRepo.forgive_user(target_id, g.chat_id):
                    success = True
            await query.edit_message_text(
                get_forgive_result(success), reply_markup=get_back_button(), parse_mode="HTML"
            )

        elif data.startswith("grp_reset_confirm"):
            if "_" in data:
                chat_id = int(data.rsplit("_", 1)[-1])
                success = await SettingsRepo.wipe_group_container(chat_id, user_id)
            else:
                groups = await SettingsRepo.get_owned_groups(user_id)
                success = False
                for g in groups:
                    if await SettingsRepo.wipe_group_container(g.chat_id, user_id):
                        success = True
            await query.edit_message_text(get_reset_result(success), reply_markup=get_back_button(), parse_mode="HTML")

    except Exception as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Group Dashboard error: {e}", exc_info=True)


async def scheduled_message_loop():
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
    await asyncio.sleep(60)


async def start_service():
    global bot_app
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

    bot_app.add_error_handler(handle_bot_error)

    register_bot_webhook("group", bot_app)
    await bot_app.initialize()
    await bot_app.start()

    track_task(asyncio.create_task(safe_loop("scheduled_messages", scheduled_message_loop)))
    logger.info("⏰ Scheduled Message Loop: Online")


async def register_webhook():
    if bot_app:
        await setup_bot_webhook(bot_app, "group")


async def stop_service(dispose_db: bool = False):
    for task in list(background_tasks):
        task.cancel()
    if background_tasks:
        await asyncio.gather(*list(background_tasks), return_exceptions=True)
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    if dispose_db:
        await dispose_engine()

