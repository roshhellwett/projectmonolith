from telegram import Update
from telegram.ext import ContextTypes

from core.config import ADMIN_USER_ID
from zenith_admin_bot import ui as admin_ui
from zenith_admin_bot.common import logger
from zenith_admin_bot.repository import AdminRepo, BotRegistryRepo, MonitoringRepo


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.answer("Unauthorized.", show_alert=True)
        return

    try:
        if query.data == "admin_main":
            await query.edit_message_text(
                admin_ui.get_admin_dashboard(),
                reply_markup=admin_ui.get_admin_main_menu(),
                parse_mode="HTML",
            )

        elif query.data == "admin_overview":
            stats = await MonitoringRepo.get_subscription_stats()
            ticket_stats = await MonitoringRepo.get_ticket_stats()
            await query.edit_message_text(
                admin_ui.format_system_overview(stats, ticket_stats),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_keys":
            keys = await MonitoringRepo.get_recent_keys(limit=10)
            await query.edit_message_text(
                admin_ui.format_key_management(keys),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_users":
            await query.edit_message_text(
                admin_ui.get_user_management_help(),
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

        elif query.data == "admin_audit":
            logs = await AdminRepo.get_audit_trail(limit=20)
            await query.edit_message_text(
                admin_ui.format_audit_log(logs),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_revenue":
            stats = await MonitoringRepo.get_subscription_stats()
            await query.edit_message_text(
                admin_ui.format_revenue_analytics(stats),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_back":
            await query.edit_message_text(
                admin_ui.get_admin_dashboard(),
                reply_markup=admin_ui.get_admin_main_menu(),
                parse_mode="HTML",
            )

        elif query.data == "admin_groups":
            groups = await MonitoringRepo.get_all_groups(limit=30)
            await query.edit_message_text(
                admin_ui.format_group_list(groups),
                reply_markup=admin_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets" or query.data == "admin_tickets_all":
            tickets = await MonitoringRepo.get_all_tickets_admin(limit=30)
            await query.edit_message_text(
                admin_ui.format_ticket_list(tickets, "All Tickets"),
                reply_markup=admin_ui.get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_open":
            tickets = await MonitoringRepo.get_all_tickets_admin(status="open", limit=30)
            await query.edit_message_text(
                admin_ui.format_ticket_list(tickets, "Open Tickets"),
                reply_markup=admin_ui.get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_progress":
            tickets = await MonitoringRepo.get_all_tickets_admin(status="in_progress", limit=30)
            await query.edit_message_text(
                admin_ui.format_ticket_list(tickets, "In Progress Tickets"),
                reply_markup=admin_ui.get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_resolved":
            tickets = await MonitoringRepo.get_all_tickets_admin(status="resolved", limit=30)
            await query.edit_message_text(
                admin_ui.format_ticket_list(tickets, "Resolved Tickets"),
                reply_markup=admin_ui.get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_stale":
            tickets = await MonitoringRepo.get_stale_tickets(days=2)
            await query.edit_message_text(
                admin_ui.format_ticket_list(tickets, "Stale Tickets"),
                reply_markup=admin_ui.get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_db_stats":
            stats = await MonitoringRepo.get_db_stats()
            await query.edit_message_text(
                admin_ui.format_db_stats(stats),
                reply_markup=admin_ui.get_system_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_key_history":
            keys = await MonitoringRepo.get_key_usage_history(limit=20)
            await query.edit_message_text(
                admin_ui.format_key_history(keys),
                reply_markup=admin_ui.get_system_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_faq_menu":
            faq_count = await MonitoringRepo.get_faq_count()
            canned_count = await MonitoringRepo.get_canned_count()
            await query.edit_message_text(
                admin_ui.get_faq_menu_msg(faq_count, canned_count),
                reply_markup=admin_ui.get_system_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_bulk_keys":
            await query.edit_message_text(
                admin_ui.get_bulk_keygen_help(),
                reply_markup=admin_ui.get_bulk_keygen_keyboard(),
                parse_mode="HTML",
            )

        elif query.data.startswith("admin_bulk_"):
            parts = query.data.split("_")
            if len(parts) >= 4:
                count = int(parts[2])
                days = int(parts[3])
                days = max(1, min(days, 365))
                keys = await MonitoringRepo.generate_bulk_keys(count, days)
                await AdminRepo.log_action(
                    ADMIN_USER_ID, "keygen_bulk", details=f"Generated {count} keys for {days} days"
                )
                await query.edit_message_text(
                    admin_ui.get_bulk_keygen_success(count, days, keys),
                    reply_markup=admin_ui.get_bulk_keygen_keyboard(),
                    parse_mode="HTML",
                )

    except Exception as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Dashboard callback error: {e}")
