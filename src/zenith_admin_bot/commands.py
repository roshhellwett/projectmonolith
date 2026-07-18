import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from core.config import ADMIN_USER_ID
from zenith_admin_bot.common import admin_only, rate_limit_admin
from zenith_admin_bot.repository import AdminRepo, BotRegistryRepo, MonitoringRepo
from zenith_admin_bot.ui import (
    format_audit_log,
    format_bot_health,
    format_canned_list,
    format_db_stats,
    format_faq_list,
    format_group_list,
    format_group_search,
    format_key_history,
    format_key_management,
    format_revenue_detailed,
    format_subscription_list,
    format_system_overview,
    format_ticket_detail,
    format_ticket_list,
    format_ticket_metrics,
    format_user_list,
    format_user_management,
    get_admin_dashboard,
    get_admin_main_menu,
)
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_support_bot.notifications import notify_user_on_admin_reply
from zenith_support_bot.repository import CannedRepo, FAQRepo, TicketRepo


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        get_admin_dashboard(),
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(context.args[0]) if context.args else 30
        days = max(1, min(days, 365))
    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid day count. Usage: <code>/keygen [DAYS]</code>",
            parse_mode="HTML",
        )
        return

    key = await SubscriptionRepo.generate_key(days)
    await AdminRepo.log_action(ADMIN_USER_ID, "keygen", details=f"Generated key for {days} days")
    await update.message.reply_text(
        f"🔑 <b>Key Generated</b>\n\n" f"<code>{key}</code>\n\n" f"<b>Duration:</b> {days} days",
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Usage: <code>/extend [USER_ID] [DAYS]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user = int(context.args[0])
        days = int(context.args[1])
        days = max(1, min(days, 365))
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID or day count.")
        return

    result = await SubscriptionRepo.extend_subscription(target_user, days)
    await AdminRepo.log_action(ADMIN_USER_ID, "extend", target_user_id=target_user, details=f"Extended by {days} days")
    await update.message.reply_text(result, parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: <code>/revoke [USER_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    result = await SubscriptionRepo.revoke_subscription(target_user)
    await AdminRepo.log_action(ADMIN_USER_ID, "revoke", target_user_id=target_user)
    await update.message.reply_text(result, parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: <code>/lookup [USER_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    details = await MonitoringRepo.get_user_subscription_details(target_user)
    await AdminRepo.log_action(ADMIN_USER_ID, "user_lookup", target_user_id=target_user)
    await update.message.reply_text(
        format_user_management(target_user, details),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = await MonitoringRepo.get_recent_keys(limit=20)
    await update.message.reply_text(
        format_key_management(keys),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=10)
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await MonitoringRepo.get_subscription_stats()
    ticket_stats = await MonitoringRepo.get_ticket_stats()
    await update.message.reply_text(
        format_system_overview(stats, ticket_stats),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=15)
async def cmd_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = await MonitoringRepo.get_all_active_subscriptions()
    await update.message.reply_text(
        format_subscription_list(subs),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=30)
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: <code>/broadcast [MESSAGE]</code>",
            parse_mode="HTML",
        )
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
        f"📢 <b>Broadcast Complete</b>\n\n"
        f"👤 Users: {len(user_ids)}\n"
        f"⭐ Pro Users: {len(pro_user_ids)}\n"
        f"👥 Groups: {len(group_ids)}\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}",
        parse_mode="HTML",
    )


@admin_only
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = await AdminRepo.get_audit_trail(limit=30)
    await update.message.reply_text(
        format_audit_log(logs),
        parse_mode="HTML",
    )


@admin_only
async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await BotRegistryRepo.get_all_bots()
    await update.message.reply_text(
        format_bot_health(bots),
        parse_mode="HTML",
    )


@admin_only
async def cmd_botlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await BotRegistryRepo.get_all_bots()
    await update.message.reply_text(
        format_bot_health(bots),
        parse_mode="HTML",
    )


@admin_only
async def cmd_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickets = await MonitoringRepo.get_all_tickets_admin(limit=30)
    await update.message.reply_text(
        format_ticket_list(tickets, "🎫 ALL TICKETS"),
        parse_mode="HTML",
    )


@admin_only
async def cmd_ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: <code>/ticket [TICKET_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID.")
        return

    ticket = await MonitoringRepo.get_ticket_by_id(ticket_id)
    if not ticket:
        await update.message.reply_text("⚠️ Ticket not found.")
        return

    await update.message.reply_text(
        format_ticket_detail(ticket),
        parse_mode="HTML",
    )


@admin_only
async def cmd_ticket_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/resolve [TICKET_ID] [response]</code>\n\n"
            "Example: <code>/resolve 5 The issue has been fixed.</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID.")
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
        await update.message.reply_text(
            f"✅ <b>Ticket Resolved</b>\n\nTicket #{ticket_id} has been resolved.\n\n📬 User has been notified.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("⚠️ Ticket not found.")


@admin_only
async def cmd_ticket_inprogress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/inprogress [TICKET_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID.")
        return

    success = await TicketRepo.set_in_progress(ticket_id)
    if success:
        await update.message.reply_text(
            f"✅ <b>Ticket In-Progress</b>\n\nTicket #{ticket_id} is now being worked on.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("⚠️ Ticket not found.")


@admin_only
async def cmd_ticket_close_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/close [TICKET_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID.")
        return

    success = await TicketRepo.admin_close_ticket(ticket_id)
    if success:
        await update.message.reply_text(
            f"✅ <b>Ticket Closed</b>\n\nTicket #{ticket_id} has been closed.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("⚠️ Ticket not found or cannot be closed.")


@admin_only
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/search [USER_ID or USERNAME]</code>",
            parse_mode="HTML",
        )
        return

    query = context.args[0]
    users = await MonitoringRepo.search_users(query, limit=20)
    await AdminRepo.log_action(ADMIN_USER_ID, "user_search", details=f"Searched: {query}")
    await update.message.reply_text(
        format_user_list(users),
        parse_mode="HTML",
    )


@admin_only
async def cmd_groups_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = await MonitoringRepo.get_all_groups(limit=30)
    await AdminRepo.log_action(ADMIN_USER_ID, "group_lookup", details="Listed all groups")
    await update.message.reply_text(
        format_group_list(groups),
        parse_mode="HTML",
    )


@admin_only
async def cmd_group_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/gsearch [GROUP_ID or NAME]</code>",
            parse_mode="HTML",
        )
        return

    query = " ".join(context.args)
    groups = await MonitoringRepo.search_groups(query, limit=20)
    await AdminRepo.log_action(ADMIN_USER_ID, "group_lookup", details=f"Searched: {query}")
    await update.message.reply_text(
        format_group_search(groups),
        parse_mode="HTML",
    )


@admin_only
async def cmd_bulk_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/bulkkeygen [COUNT] [DAYS]</code>\n" "Example: <code>/bulkkeygen 10 30</code>",
            parse_mode="HTML",
        )
        return

    try:
        count = int(context.args[0])
        days = int(context.args[1])
        days = max(1, min(days, 365))
    except ValueError:
        await update.message.reply_text("⚠️ Invalid numbers.")
        return

    if count > 50:
        await update.message.reply_text("⚠️ Maximum 50 keys at a time.")
        return

    keys = await MonitoringRepo.generate_bulk_keys(count, days)
    await AdminRepo.log_action(ADMIN_USER_ID, "keygen_bulk", details=f"Generated {count} keys for {days} days")

    keys_text = "\n".join([f"<code>{k}</code>" for k in keys])
    await update.message.reply_text(
        f"🔑 <b>BULK KEY GENERATED</b>\n\n"
        f"<b>Count:</b> {count} keys\n"
        f"<b>Duration:</b> {days} days\n\n"
        f"<b>Keys:</b>\n{keys_text}",
        parse_mode="HTML",
    )


@admin_only
async def cmd_dbstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await MonitoringRepo.get_db_stats()
    await update.message.reply_text(
        format_db_stats(stats),
        parse_mode="HTML",
    )


@admin_only
async def cmd_revenue_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = await MonitoringRepo.get_revenue_report()
    await update.message.reply_text(
        format_revenue_detailed(report),
        parse_mode="HTML",
    )


@admin_only
async def cmd_key_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = await MonitoringRepo.get_key_usage_history(limit=20)
    await update.message.reply_text(
        format_key_history(keys),
        parse_mode="HTML",
    )


@admin_only
async def cmd_ticket_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metrics = await MonitoringRepo.get_ticket_metrics()
    await update.message.reply_text(
        format_ticket_metrics(metrics),
        parse_mode="HTML",
    )


@admin_only
async def cmd_stale_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickets = await MonitoringRepo.get_stale_tickets(days=2)
    await update.message.reply_text(
        format_ticket_list(tickets, "⚠️ STALE TICKETS"),
        parse_mode="HTML",
    )


@admin_only
async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "<code>/faq list</code> - List all FAQs\n"
            "<code>/faq add [question] | [answer] | [category]</code>\n"
            "<code>/faq delete [id]</code>",
            parse_mode="HTML",
        )
        return

    action = context.args[0].lower()

    if action == "list":
        faqs = await FAQRepo.get_all_faqs(limit=30)
        await update.message.reply_text(
            format_faq_list(faqs),
            parse_mode="HTML",
        )

    elif action == "add":
        if len(context.args) < 3:
            await update.message.reply_text(
                "⚠️ <b>Usage:</b> <code>/faq add [question] | [answer] | [category]</code>",
                parse_mode="HTML",
            )
            return

        full_text = " ".join(context.args[1:])
        parts = full_text.split("|")
        if len(parts) < 2:
            await update.message.reply_text("⚠️ Use | to separate question, answer, and category.")
            return

        question = parts[0].strip()
        answer = parts[1].strip()
        category = parts[2].strip() if len(parts) > 2 else "general"

        await FAQRepo.add_faq(question, answer, category, ADMIN_USER_ID)
        await AdminRepo.log_action(ADMIN_USER_ID, "faq_add", details=f"Added FAQ: {question[:30]}")
        await update.message.reply_text(
            f"✅ <b>FAQ Added</b>\n\n" f"<b>Q:</b> {question}\n" f"<b>A:</b> {answer}\n" f"<b>Category:</b> {category}",
            parse_mode="HTML",
        )

    elif action == "delete":
        try:
            faq_id = int(context.args[1])
        except (ValueError, IndexError):
            await update.message.reply_text("⚠️ Invalid FAQ ID.")
            return

        success = await FAQRepo.delete_faq(faq_id)
        if success:
            await AdminRepo.log_action(ADMIN_USER_ID, "faq_delete", details=f"Deleted FAQ #{faq_id}")
            await update.message.reply_text(f"✅ FAQ #{faq_id} deleted.")
        else:
            await update.message.reply_text(f"⚠️ FAQ #{faq_id} not found.")

    else:
        await update.message.reply_text("⚠️ Unknown action. Use list, add, or delete.")


@admin_only
async def cmd_canned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "<code>/canned list</code> - List all canned responses\n"
            "<code>/canned add [tag] | [content]</code>\n"
            "<code>/canned delete [tag]</code>",
            parse_mode="HTML",
        )
        return

    action = context.args[0].lower()

    if action == "list":
        canned = await CannedRepo.get_all_canned()
        await update.message.reply_text(
            format_canned_list(canned),
            parse_mode="HTML",
        )

    elif action == "add":
        if len(context.args) < 3:
            await update.message.reply_text(
                "⚠️ <b>Usage:</b> <code>/canned add [tag] | [content]</code>",
                parse_mode="HTML",
            )
            return

        full_text = " ".join(context.args[1:])
        parts = full_text.split("|")
        if len(parts) < 2:
            await update.message.reply_text("⚠️ Use | to separate tag and content.")
            return

        tag = parts[0].strip()
        content = parts[1].strip()

        await CannedRepo.add_canned(tag, content, ADMIN_USER_ID)
        await AdminRepo.log_action(ADMIN_USER_ID, "canned_add", details=f"Added canned: {tag}")
        await update.message.reply_text(
            f"✅ <b>Canned Response Added</b>\n\n" f"<b>Tag:</b> {tag}\n" f"<b>Content:</b> {content}",
            parse_mode="HTML",
        )

    elif action == "delete":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Specify tag to delete.")
            return

        tag = context.args[1]
        success = await CannedRepo.delete_canned(tag)
        if success:
            await AdminRepo.log_action(ADMIN_USER_ID, "canned_delete", details=f"Deleted canned: {tag}")
            await update.message.reply_text(f"✅ Canned response '{tag}' deleted.")
        else:
            await update.message.reply_text(f"⚠️ Canned response '{tag}' not found.")

    else:
        await update.message.reply_text("⚠️ Unknown action. Use list, add, or delete.")
