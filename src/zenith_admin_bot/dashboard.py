
import contextlib
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_USER_ID
from zenith_admin_bot import ui as admin_ui
from zenith_admin_bot.common import logger
from zenith_admin_bot.repository import AdminRepo, BotRegistryRepo, MonitoringRepo
from zenith_crypto_bot.repository import CryptoSubscriptionRepo
from zenith_group_bot.repository import GroupSubscriptionRepo

async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()

    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        with contextlib.suppress(Exception):
            await query.answer("Unauthorized.", show_alert=True)
        return

    try:
        if query.data == "admin_main" or query.data == "admin_back":
            await query.edit_message_text(
                admin_ui.get_admin_dashboard(),
                reply_markup=admin_ui.get_admin_main_menu(),
                parse_mode="HTML",
            )
        elif query.data == "admin_overview":
            stats = await MonitoringRepo.get_subscription_stats()
            await query.edit_message_text(
                admin_ui.format_system_overview(stats),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_health":
            bots = await BotRegistryRepo.get_all_bots()
            await query.edit_message_text(
                admin_ui.format_bot_health(bots),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_menu":
            await query.edit_message_text(
                "🪙 <b>Crypto Bot Management</b>\n\nSelect an action:",
                reply_markup=admin_ui.get_crypto_admin_menu(),
                parse_mode="HTML",
            )
        elif query.data == "admin_group_menu":
            await query.edit_message_text(
                "🛡️ <b>Group Bot Management</b>\n\nSelect an action:",
                reply_markup=admin_ui.get_group_admin_menu(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_keygen_30":
            key = await CryptoSubscriptionRepo.generate_key(30)
            await query.edit_message_text(
                f"✅ Generated 30-day Crypto Key:\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_keygen_90":
            key = await CryptoSubscriptionRepo.generate_key(90)
            await query.edit_message_text(
                f"✅ Generated 90-day Crypto Key:\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_group_keygen_30":
            key = await GroupSubscriptionRepo.generate_key(30)
            await query.edit_message_text(
                f"✅ Generated 30-day Group Key:\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_group_keygen_90":
            key = await GroupSubscriptionRepo.generate_key(90)
            await query.edit_message_text(
                f"✅ Generated 90-day Group Key:\n<code>{key}</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_crypto_subs":
            subs = await CryptoSubscriptionRepo.get_all_subscriptions()
            text = "📋 <b>Active Crypto Subscriptions:</b>\n\n"
            for user, days in subs:
                text += f"• <code>{user}</code> - {days} days left\n"
            if not subs: text += "No active subscriptions."
            await query.edit_message_text(text, reply_markup=admin_ui.get_back_button(), parse_mode="HTML")
        elif query.data == "admin_group_subs":
            subs = await GroupSubscriptionRepo.get_all_subscriptions()
            text = "📋 <b>Active Group Subscriptions:</b>\n\n"
            for user, days in subs:
                text += f"• <code>{user}</code> - {days} days left\n"
            if not subs: text += "No active subscriptions."
            await query.edit_message_text(text, reply_markup=admin_ui.get_back_button(), parse_mode="HTML")
        elif query.data == "admin_users":
            users = await AdminRepo.get_all_users(limit=20)
            await query.edit_message_text(
                admin_ui.format_user_list(users),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_revenue":
            report = await AdminRepo.get_revenue_report()
            await query.edit_message_text(
                admin_ui.format_revenue_analytics(report),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_db_stats":
            stats = await AdminRepo.get_db_stats()
            await query.edit_message_text(
                admin_ui.format_db_stats(stats),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_audit":
            logs = await AdminRepo.get_audit_trail(limit=15)
            await query.edit_message_text(
                admin_ui.format_audit_log(logs),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_security":
            await query.edit_message_text(
                admin_ui.format_platform_metrics(),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        elif query.data == "admin_broadcast":
            await query.edit_message_text(
                "📡 <b>Broadcast System</b>\n\nTo send a broadcast to all users, use the command:\n<code>/broadcast [your message]</code>",
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )
        else:
            await query.answer("Feature in development or migrated.", show_alert=True)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
