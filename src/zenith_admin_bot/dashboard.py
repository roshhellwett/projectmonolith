
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
            ticket_stats = {"total": 0, "open": 0, "resolved": 0} # Dummy for now
            await query.edit_message_text(
                admin_ui.format_system_overview(stats, ticket_stats),
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
        else:
            await query.answer("Feature in development or migrated.", show_alert=True)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
