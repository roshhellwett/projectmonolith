import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from core.config import ADMIN_USER_ID
from zenith_admin_bot import ui as admin_ui
from zenith_admin_bot.common import admin_only, rate_limit_admin
from zenith_admin_bot.repository import AdminRepo, BotRegistryRepo, MonitoringRepo
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_support_bot.notifications import notify_user_on_admin_reply
from zenith_support_bot.repository import CannedRepo, FAQRepo, TicketRepo


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        admin_ui.get_admin_dashboard(),
        reply_markup=admin_ui.get_admin_main_menu(),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(context.args[0]) if context.args else 30
        days = max(1, min(days, 365))
    except ValueError:
        await update.message.reply_text("Invalid day count. Usage: /keygen [DAYS]")
        return

    key = await SubscriptionRepo.generate_key(days)
    await AdminRepo.log_action(ADMIN_USER_ID, "keygen", details=f"Generated key for {days} days")
    await update.message.reply_text(admin_ui.get_keygen_success(key, days), parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /extend [USER_ID] [DAYS]")
        return

    try:
        target_user = int(context.args[0])
        days = int(context.args[1])
        days = max(1, min(days, 365))
    except ValueError:
        await update.message.reply_text("Invalid user ID or day count.")
        return

    result = await SubscriptionRepo.extend_subscription(target_user, days)
    await AdminRepo.log_action(ADMIN_USER_ID, "extend", target_user_id=target_user, details=f"Extended by {days} days")
    await update.message.reply_text(result, parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /revoke [USER_ID]")
        return

    try:
        target_user = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    result = await SubscriptionRepo.revoke_subscription(target_user)
    await AdminRepo.log_action(ADMIN_USER_ID, "revoke", target_user_id=target_user)
    await update.message.reply_text(result, parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lookup [USER_ID]")
        return

    try:
        target_user = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    details = await MonitoringRepo.get_user_subscription_details(target_user)
    await AdminRepo.log_action(ADMIN_USER_ID, "user_lookup", target_user_id=target_user)
    await update.message.reply_text(admin_ui.format_user_management(target_user, details), parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = await MonitoringRepo.get_recent_keys(limit=20)
    await update.message.reply_text(admin_ui.format_key_management(keys), parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await MonitoringRepo.get_subscription_stats()
    ticket_stats = await MonitoringRepo.get_ticket_stats()
    await update.message.reply_text(admin_ui.format_system_overview(stats, ticket_stats), parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=15)
async def cmd_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = await MonitoringRepo.get_all_active_subscriptions()
    await update.message.reply_text(admin_ui.format_subscription_list(subs), parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=30)
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [MESSAGE]")
        return

    message = " ".join(context.args)
    user_ids = await MonitoringRepo.get_all_user_ids()
    pro_user_ids = await MonitoringRepo.get_all_pro_user_ids()
    group_ids = await MonitoringRepo.get_all_group_chat_ids()

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=message, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await AdminRepo.log_action(ADMIN_USER_ID, "broadcast", details=f"Sent to {len(user_ids)} users")
    await update.message.reply_text(
        admin_ui.get_broadcast_result(user_ids, pro_user_ids, group_ids, sent, failed), parse_mode="HTML"
    )


@admin_only
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = await AdminRepo.get_audit_trail(limit=30)
    await update.message.reply_text(admin_ui.format_audit_log(logs), parse_mode="HTML")


@admin_only
async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await BotRegistryRepo.get_all_bots()
    await update.message.reply_text(admin_ui.format_bot_health(bots), parse_mode="HTML")


@admin_only
async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(admin_ui.format_platform_metrics(), parse_mode="HTML")


@admin_only
async def cmd_botlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await BotRegistryRepo.get_all_bots()
    await update.message.reply_text(admin_ui.format_bot_health(bots), parse_mode="HTML")


@admin_only
async def cmd_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickets = await MonitoringRepo.get_all_tickets_admin(limit=30)
    await update.message.reply_text(admin_ui.format_ticket_list(tickets, "All Tickets"), parse_mode="HTML")


@admin_only
async def cmd_ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /ticket [TICKET_ID]")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ticket ID.")
        return

    ticket = await MonitoringRepo.get_ticket_by_id(ticket_id)
    if not ticket:
        await update.message.reply_text("Ticket not found.")
        return

    await update.message.reply_text(admin_ui.format_ticket_detail(ticket), parse_mode="HTML")


@admin_only
async def cmd_ticket_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /resolve [TICKET_ID] [response]\n" "Example: /resolve 5 The issue has been fixed."
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ticket ID.")
        return

    response = " ".join(context.args[1:])
    success = await TicketRepo.set_admin_response(ticket_id, response)
    if success:
        ticket = await TicketRepo.get_ticket(ticket_id)
        if ticket:
            await notify_user_on_admin_reply(
                user_id=ticket.user_id,
                ticket_id=ticket_id,
                subject=ticket.subject,
                admin_response=response,
            )
        await update.message.reply_text(admin_ui.get_resolve_success(ticket_id), parse_mode="HTML")
    else:
        await update.message.reply_text("Ticket not found.")


@admin_only
async def cmd_ticket_inprogress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /inprogress [TICKET_ID]")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ticket ID.")
        return

    success = await TicketRepo.set_in_progress(ticket_id)
    if success:
        await update.message.reply_text(admin_ui.get_ticket_inprogress_success(ticket_id), parse_mode="HTML")
    else:
        await update.message.reply_text("Ticket not found.")


@admin_only
async def cmd_ticket_close_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /close [TICKET_ID]")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ticket ID.")
        return

    success = await TicketRepo.admin_close_ticket(ticket_id)
    if success:
        await update.message.reply_text(admin_ui.get_ticket_close_success(ticket_id), parse_mode="HTML")
    else:
        await update.message.reply_text(admin_ui.get_ticket_not_found_msg())


@admin_only
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search [USER_ID or USERNAME]")
        return

    query = context.args[0]
    users = await MonitoringRepo.search_users(query, limit=20)
    await AdminRepo.log_action(ADMIN_USER_ID, "user_search", details=f"Searched: {query}")
    await update.message.reply_text(admin_ui.format_user_list(users), parse_mode="HTML")


@admin_only
async def cmd_groups_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = await MonitoringRepo.get_all_groups(limit=30)
    await AdminRepo.log_action(ADMIN_USER_ID, "group_lookup", details="Listed all groups")
    await update.message.reply_text(admin_ui.format_group_list(groups), parse_mode="HTML")


@admin_only
async def cmd_group_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /gsearch [GROUP_ID or NAME]")
        return

    query = " ".join(context.args)
    groups = await MonitoringRepo.search_groups(query, limit=20)
    await AdminRepo.log_action(ADMIN_USER_ID, "group_lookup", details=f"Searched: {query}")
    await update.message.reply_text(admin_ui.format_group_search(groups), parse_mode="HTML")


@admin_only
async def cmd_bulk_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /bulkkeygen [COUNT] [DAYS]\nExample: /bulkkeygen 10 30")
        return

    try:
        count = int(context.args[0])
        days = int(context.args[1])
        days = max(1, min(days, 365))
    except ValueError:
        await update.message.reply_text("Invalid numbers.")
        return

    if count > 50:
        await update.message.reply_text("Maximum 50 keys at a time.")
        return

    keys = await MonitoringRepo.generate_bulk_keys(count, days)
    await AdminRepo.log_action(ADMIN_USER_ID, "keygen_bulk", details=f"Generated {count} keys for {days} days")
    await update.message.reply_text(admin_ui.get_bulk_keygen_success(count, days, keys), parse_mode="HTML")


@admin_only
async def cmd_dbstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await MonitoringRepo.get_db_stats()
    await update.message.reply_text(admin_ui.format_db_stats(stats), parse_mode="HTML")


@admin_only
async def cmd_revenue_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = await MonitoringRepo.get_revenue_report()
    await update.message.reply_text(admin_ui.format_revenue_detailed(report), parse_mode="HTML")


@admin_only
async def cmd_key_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = await MonitoringRepo.get_key_usage_history(limit=20)
    await update.message.reply_text(admin_ui.format_key_history(keys), parse_mode="HTML")


@admin_only
async def cmd_ticket_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metrics = await MonitoringRepo.get_ticket_metrics()
    await update.message.reply_text(admin_ui.format_ticket_metrics(metrics), parse_mode="HTML")


@admin_only
async def cmd_stale_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickets = await MonitoringRepo.get_stale_tickets(days=2)
    await update.message.reply_text(admin_ui.format_ticket_list(tickets, "Stale Tickets"), parse_mode="HTML")


@admin_only
async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/faq list \u2014 List all FAQs\n"
            "/faq add [question] | [answer] | [category]\n"
            "/faq delete [id]"
        )
        return

    action = context.args[0].lower()

    if action == "list":
        faqs = await FAQRepo.get_all_faqs(limit=30)
        await update.message.reply_text(admin_ui.format_faq_list(faqs), parse_mode="HTML")

    elif action == "add":
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /faq add [question] | [answer] | [category]")
            return

        full_text = " ".join(context.args[1:])
        parts = full_text.split("|")
        if len(parts) < 2:
            await update.message.reply_text("Use | to separate question, answer, and category.")
            return

        question = parts[0].strip()
        answer = parts[1].strip()
        category = parts[2].strip() if len(parts) > 2 else "general"

        await FAQRepo.add_faq(question, answer, category, ADMIN_USER_ID)
        await AdminRepo.log_action(ADMIN_USER_ID, "faq_add", details=f"Added FAQ: {question[:30]}")
        await update.message.reply_text(
            f"<b>FAQ Added</b>\n\nQ: {question}\nA: {answer}\nCategory: {category}",
            parse_mode="HTML",
        )

    elif action == "delete":
        try:
            faq_id = int(context.args[1])
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid FAQ ID.")
            return

        success = await FAQRepo.delete_faq(faq_id)
        if success:
            await AdminRepo.log_action(ADMIN_USER_ID, "faq_delete", details=f"Deleted FAQ #{faq_id}")
            await update.message.reply_text(f"FAQ #{faq_id} deleted.")
        else:
            await update.message.reply_text(f"FAQ #{faq_id} not found.")

    else:
        await update.message.reply_text("Unknown action. Use list, add, or delete.")


@admin_only
async def cmd_canned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/canned list \u2014 List all canned responses\n"
            "/canned add [tag] | [content]\n"
            "/canned delete [tag]"
        )
        return

    action = context.args[0].lower()

    if action == "list":
        canned = await CannedRepo.get_all_canned()
        await update.message.reply_text(admin_ui.format_canned_list(canned), parse_mode="HTML")

    elif action == "add":
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /canned add [tag] | [content]")
            return

        full_text = " ".join(context.args[1:])
        parts = full_text.split("|")
        if len(parts) < 2:
            await update.message.reply_text("Use | to separate tag and content.")
            return

        tag = parts[0].strip()
        content = parts[1].strip()

        await CannedRepo.add_canned(tag, content, ADMIN_USER_ID)
        await AdminRepo.log_action(ADMIN_USER_ID, "canned_add", details=f"Added canned: {tag}")
        await update.message.reply_text(
            f"<b>Canned Response Added</b>\n\nTag: {tag}\nContent: {content}",
            parse_mode="HTML",
        )

    elif action == "delete":
        if len(context.args) < 2:
            await update.message.reply_text("Specify tag to delete.")
            return

        tag = context.args[1]
        success = await CannedRepo.delete_canned(tag)
        if success:
            await AdminRepo.log_action(ADMIN_USER_ID, "canned_delete", details=f"Deleted canned: {tag}")
            await update.message.reply_text(f"Canned response '{tag}' deleted.")
        else:
            await update.message.reply_text(f"Canned response '{tag}' not found.")

    else:
        await update.message.reply_text("Unknown action. Use list, add, or delete.")
