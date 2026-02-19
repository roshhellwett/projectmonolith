import asyncio
import time
from functools import wraps
from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import ADMIN_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_admin_bot.repository import (
    init_admin_db, AdminRepo, BotRegistryRepo, MonitoringRepo, dispose_admin_engine,
)
from zenith_support_bot.repository import FAQRepo, CannedRepo, TicketRepo
from zenith_support_bot.notifications import notify_user_on_admin_reply
from zenith_admin_bot.ui import (
    get_admin_main_menu, get_back_button, get_admin_dashboard,
    format_system_overview, format_key_management, format_user_management,
    format_bot_health, format_audit_log, format_revenue_analytics,
    format_subscription_list, format_ticket_list, format_ticket_detail,
    format_ticket_metrics, format_user_list, format_group_list,
    format_group_search, format_db_stats, format_revenue_detailed,
    format_key_history, format_faq_list, format_canned_list,
    get_tickets_keyboard, get_faq_keyboard,
    get_system_keyboard, get_bulk_keygen_keyboard,
)
from zenith_admin_bot.monitoring import start_monitoring, stop_monitoring

logger = setup_logger("ADMIN")
router = APIRouter()
bot_app = None
background_tasks = set()

_admin_command_timestamps = {}


def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def rate_limit_admin(seconds: int = 10):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            command = func.__name__
            key = f"{user_id}:{command}"
            now = time.time()
            
            if key in _admin_command_timestamps:
                last_time = _admin_command_timestamps[key]
                if now - last_time < seconds:
                    if update.message:
                        await update.message.reply_text(
                            f"⏳ Please wait {seconds} seconds between {command} commands."
                        )
                    return
            
            _admin_command_timestamps[key] = now
            return await func(update, context)
        return wrapper
    return decorator


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_USER_ID:
            if update.message:
                await update.message.reply_text("⛔ Unauthorized.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized.", show_alert=True)
            return
        return await func(update, context)
    return wrapper


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
    await AdminRepo.log_action(
        ADMIN_USER_ID, "keygen", details=f"Generated key for {days} days: {key}"
    )
    await update.message.reply_text(
        f"🔑 <b>Key Generated</b>\n\n"
        f"<b>Key:</b> <code>{key}</code>\n"
        f"<b>Duration:</b> {days} days",
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=30)
async def cmd_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/extend [USER_ID] [DAYS]</code>\n"
            "Example: <code>/extend 123456789 30</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    days = 30
    if len(context.args) > 1:
        try:
            days = int(context.args[1])
            days = max(1, min(days, 365))
        except ValueError:
            await update.message.reply_text("⚠️ Invalid day count.")
            return

    success, msg = await SubscriptionRepo.extend_subscription(target_user_id, days)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "extend", target_user_id=target_user_id,
        details=f"Extended by {days} days"
    )

    if success:
        try:
            await bot_app.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"💎 <b>PRO SUBSCRIPTION EXTENDED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"✅ <b>{days} days</b> have been added to your account.\n"
                    f"Enjoy uninterrupted access to all Pro features!\n\n"
                    f"<i>Type /start to open your terminal.</i>"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {target_user_id}: {e}")

    await update.message.reply_text(msg, parse_mode="HTML")


@admin_only
@rate_limit_admin(seconds=30)
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/revoke [USER_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    success, msg = await SubscriptionRepo.revoke_subscription(target_user_id)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "revoke", target_user_id=target_user_id,
        details="Revoked subscription"
    )

    if success:
        try:
            await bot_app.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"❌ <b>SUBSCRIPTION REVOKED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Your Pro subscription has been revoked.\n"
                    f"Contact admin for details."
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {target_user_id}: {e}")
            pass

    await update.message.reply_text(msg, parse_mode="HTML")


@admin_only
async def cmd_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/lookup [USER_ID]</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return

    sub_details = await MonitoringRepo.get_user_subscription_details(target_user_id)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "user_lookup", target_user_id=target_user_id,
        details="Looked up user subscription"
    )

    await update.message.reply_text(
        format_user_management(target_user_id, sub_details),
        parse_mode="HTML",
    )


@admin_only
async def cmd_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = await MonitoringRepo.get_recent_keys(limit=10)
    await update.message.reply_text(
        format_key_management(keys),
        parse_mode="HTML",
    )


@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await MonitoringRepo.get_subscription_stats()
    ticket_stats = await MonitoringRepo.get_ticket_stats()

    await update.message.reply_text(
        format_system_overview(stats, ticket_stats),
        parse_mode="HTML",
    )


@admin_only
async def cmd_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscriptions = await MonitoringRepo.get_all_active_subscriptions()
    await update.message.reply_text(
        format_subscription_list(subscriptions),
        parse_mode="HTML",
    )


@admin_only
@rate_limit_admin(seconds=60)
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/broadcast [all|pro|groups] [MESSAGE]</code>\n\n"
            "Examples:\n"
            "<code>/broadcast all Hello everyone!</code>\n"
            "<code>/broadcast pro Get 50% off!</code>\n"
            "<code>/broadcast groups New feature alert!</code>",
            parse_mode="HTML",
        )
        return

    target = context.args[0].lower()
    if target not in ["all", "pro", "groups"]:
        target = "all"
        message = " ".join(context.args)
    else:
        message = " ".join(context.args[1:])

    if not message:
        await update.message.reply_text("⚠️ Please provide a message.")
        return

    await update.message.reply_text(
        f"📢 <b>Broadcast Started</b>\n\n"
        f"<b>Target:</b> {target.upper()}\n"
        f"<b>Message:</b> {message[:100]}...",
        parse_mode="HTML",
    )

    success_count = 0
    fail_count = 0

    try:
        if target == "all":
            user_ids = await MonitoringRepo.get_all_user_ids()
        elif target == "pro":
            user_ids = await MonitoringRepo.get_all_pro_user_ids()
        else:
            user_ids = await MonitoringRepo.get_all_group_chat_ids()

        for user_id in user_ids:
            try:
                await bot_app.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 <b>ANNOUNCEMENT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{message}",
                    parse_mode="HTML",
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.warning(f"Broadcast failed for {user_id}: {e}")

            await asyncio.sleep(0.05)

    except Exception as e:
        logger.error(f"Broadcast error: {e}")

    await update.message.reply_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"<b>Target:</b> {target.upper()}\n"
        f"<b>Sent:</b> {success_count}\n"
        f"<b>Failed:</b> {fail_count}",
        parse_mode="HTML",
    )

    await AdminRepo.log_action(
        ADMIN_USER_ID, "broadcast", details=f"Broadcast to {target}: {message[:50]}..."
    )


@admin_only
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = await AdminRepo.get_audit_trail(limit=20)
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
    status = None
    if context.args:
        status_arg = context.args[0].lower()
        if status_arg in ["open", "in_progress", "resolved", "closed"]:
            status = status_arg
    
    tickets = await MonitoringRepo.get_all_tickets_admin(status=status, limit=30)
    title = f"🎫 {'{status.upper()} TICKETS'}" if status else "🎫 ALL TICKETS"
    await update.message.reply_text(
        format_ticket_list(tickets, title),
        parse_mode="HTML",
    )


@admin_only
async def cmd_ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/ticket [TICKET_ID]</code>",
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

    success = await TicketRepo.close_ticket(ticket_id)
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
    await AdminRepo.log_action(
        ADMIN_USER_ID, "user_search", details=f"Searched: {query}"
    )
    await update.message.reply_text(
        format_user_list(users),
        parse_mode="HTML",
    )


@admin_only
async def cmd_groups_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = await MonitoringRepo.get_all_groups(limit=30)
    await AdminRepo.log_action(
        ADMIN_USER_ID, "group_lookup", details="Listed all groups"
    )
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
    await AdminRepo.log_action(
        ADMIN_USER_ID, "group_lookup", details=f"Searched: {query}"
    )
    await update.message.reply_text(
        format_group_search(groups),
        parse_mode="HTML",
    )


@admin_only
async def cmd_bulk_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/bulkkeygen [COUNT] [DAYS]</code>\n"
            "Example: <code>/bulkkeygen 10 30</code>",
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
    await AdminRepo.log_action(
        ADMIN_USER_ID, "keygen_bulk", details=f"Generated {count} keys for {days} days"
    )
    
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
        await AdminRepo.log_action(
            ADMIN_USER_ID, "faq_add", details=f"Added FAQ: {question[:30]}"
        )
        await update.message.reply_text(
            f"✅ <b>FAQ Added</b>\n\n"
            f"<b>Q:</b> {question}\n"
            f"<b>A:</b> {answer}\n"
            f"<b>Category:</b> {category}",
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
            await AdminRepo.log_action(
                ADMIN_USER_ID, "faq_delete", details=f"Deleted FAQ #{faq_id}"
            )
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
        await AdminRepo.log_action(
            ADMIN_USER_ID, "canned_add", details=f"Added canned: {tag}"
        )
        await update.message.reply_text(
            f"✅ <b>Canned Response Added</b>\n\n"
            f"<b>Tag:</b> {tag}\n"
            f"<b>Content:</b> {content}",
            parse_mode="HTML",
        )

    elif action == "delete":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Specify tag to delete.")
            return

        tag = context.args[1]
        success = await CannedRepo.delete_canned(tag)
        if success:
            await AdminRepo.log_action(
                ADMIN_USER_ID, "canned_delete", details=f"Deleted canned: {tag}"
            )
            await update.message.reply_text(f"✅ Canned response '{tag}' deleted.")
        else:
            await update.message.reply_text(f"⚠️ Canned response '{tag}' not found.")

    else:
        await update.message.reply_text("⚠️ Unknown action. Use list, add, or delete.")


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.answer("⛔ Unauthorized.", show_alert=True)
        return

    try:
        if query.data == "admin_main":
            await query.edit_message_text(
                get_admin_dashboard(),
                reply_markup=get_admin_main_menu(),
                parse_mode="HTML",
            )

        elif query.data == "admin_overview":
            stats = await MonitoringRepo.get_subscription_stats()
            ticket_stats = await MonitoringRepo.get_ticket_stats()
            await query.edit_message_text(
                format_system_overview(stats, ticket_stats),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_keys":
            keys = await MonitoringRepo.get_recent_keys(limit=10)
            await query.edit_message_text(
                format_key_management(keys),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_users":
            await query.edit_message_text(
                "<b>👤 USER MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Use commands:\n"
                "• <code>/lookup [USER_ID]</code> — View user subscription\n"
                "• <code>/extend [USER_ID] [DAYS]</code> — Extend subscription\n"
                "• <code>/revoke [USER_ID]</code> — Revoke subscription",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_health":
            bots = await BotRegistryRepo.get_all_bots()
            await query.edit_message_text(
                format_bot_health(bots),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_audit":
            logs = await AdminRepo.get_audit_trail(limit=20)
            await query.edit_message_text(
                format_audit_log(logs),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_revenue":
            stats = await MonitoringRepo.get_subscription_stats()
            await query.edit_message_text(
                format_revenue_analytics(stats),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_back":
            await query.edit_message_text(
                get_admin_dashboard(),
                reply_markup=get_admin_main_menu(),
                parse_mode="HTML",
            )

        elif query.data == "admin_groups":
            groups = await MonitoringRepo.get_all_groups(limit=30)
            await query.edit_message_text(
                format_group_list(groups),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets":
            tickets = await MonitoringRepo.get_all_tickets_admin(limit=30)
            await query.edit_message_text(
                format_ticket_list(tickets, "🎫 ALL TICKETS"),
                reply_markup=get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_all":
            tickets = await MonitoringRepo.get_all_tickets_admin(limit=30)
            await query.edit_message_text(
                format_ticket_list(tickets, "🎫 ALL TICKETS"),
                reply_markup=get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_open":
            tickets = await MonitoringRepo.get_all_tickets_admin(status="open", limit=30)
            await query.edit_message_text(
                format_ticket_list(tickets, "🟢 OPEN TICKETS"),
                reply_markup=get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_progress":
            tickets = await MonitoringRepo.get_all_tickets_admin(status="in_progress", limit=30)
            await query.edit_message_text(
                format_ticket_list(tickets, "🟡 IN PROGRESS TICKETS"),
                reply_markup=get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_resolved":
            tickets = await MonitoringRepo.get_all_tickets_admin(status="resolved", limit=30)
            await query.edit_message_text(
                format_ticket_list(tickets, "✅ RESOLVED TICKETS"),
                reply_markup=get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_tickets_stale":
            tickets = await MonitoringRepo.get_stale_tickets(days=2)
            await query.edit_message_text(
                format_ticket_list(tickets, "⚠️ STALE TICKETS"),
                reply_markup=get_tickets_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_db_stats":
            stats = await MonitoringRepo.get_db_stats()
            await query.edit_message_text(
                format_db_stats(stats),
                reply_markup=get_system_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_key_history":
            keys = await MonitoringRepo.get_key_usage_history(limit=20)
            await query.edit_message_text(
                format_key_history(keys),
                reply_markup=get_system_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_faq_menu":
            faq_count = await MonitoringRepo.get_faq_count()
            canned_count = await MonitoringRepo.get_canned_count()
            await query.edit_message_text(
                f"<b>📋 FAQ & CANNED MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>❓ FAQs:</b> {faq_count}\n"
                f"<b>💬 Canned Responses:</b> {canned_count}\n\n"
                f"<i>Use commands to manage:</i>\n"
                f"<code>/faq list</code> - List FAQs\n"
                f"<code>/faq add</code> - Add FAQ\n"
                f"<code>/canned list</code> - List canned responses",
                reply_markup=get_system_keyboard(),
                parse_mode="HTML",
            )

        elif query.data == "admin_bulk_keys":
            await query.edit_message_text(
                "<b>🔑 BULK KEY GENERATION</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Select quick options or use command:\n"
                "<code>/bulkkeygen [COUNT] [DAYS]</code>\n\n"
                "Example: <code>/bulkkeygen 10 30</code>",
                reply_markup=get_bulk_keygen_keyboard(),
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
                keys_text = "\n".join([f"<code>{k}</code>" for k in keys])
                await query.edit_message_text(
                    f"🔑 <b>BULK KEY GENERATED</b>\n\n"
                    f"<b>Count:</b> {count} keys\n"
                    f"<b>Duration:</b> {days} days\n\n"
                    f"<b>Keys:</b>\n{keys_text}",
                    reply_markup=get_bulk_keygen_keyboard(),
                    parse_mode="HTML",
                )

    except Exception as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Dashboard callback error: {e}")


async def start_service():
    global bot_app
    if not ADMIN_BOT_TOKEN:
        logger.warning("⚠️ ADMIN_BOT_TOKEN missing! Admin Service disabled.")
        return

    await init_admin_db()
    bot_app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen))
    bot_app.add_handler(CommandHandler("extend", cmd_extend))
    bot_app.add_handler(CommandHandler("revoke", cmd_revoke))
    bot_app.add_handler(CommandHandler("lookup", cmd_lookup))
    bot_app.add_handler(CommandHandler("keys", cmd_keys))
    bot_app.add_handler(CommandHandler("stats", cmd_stats))
    bot_app.add_handler(CommandHandler("subs", cmd_subs))
    bot_app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    bot_app.add_handler(CommandHandler("audit", cmd_audit))
    bot_app.add_handler(CommandHandler("health", cmd_health))
    bot_app.add_handler(CommandHandler("botlist", cmd_botlist))
    bot_app.add_handler(CommandHandler("tickets", cmd_tickets))
    bot_app.add_handler(CommandHandler("ticket", cmd_ticket_detail))
    bot_app.add_handler(CommandHandler("resolve", cmd_ticket_resolve))
    bot_app.add_handler(CommandHandler("inprogress", cmd_ticket_inprogress))
    bot_app.add_handler(CommandHandler("close", cmd_ticket_close_admin))
    bot_app.add_handler(CommandHandler("search", cmd_search))
    bot_app.add_handler(CommandHandler("groups", cmd_groups_list))
    bot_app.add_handler(CommandHandler("gsearch", cmd_group_search))
    bot_app.add_handler(CommandHandler("bulkkeygen", cmd_bulk_keygen))
    bot_app.add_handler(CommandHandler("dbstats", cmd_dbstats))
    bot_app.add_handler(CommandHandler("revenue", cmd_revenue_report))
    bot_app.add_handler(CommandHandler("keyhistory", cmd_key_history))
    bot_app.add_handler(CommandHandler("ticketmetrics", cmd_ticket_metrics))
    bot_app.add_handler(CommandHandler("stale", cmd_stale_tickets))
    bot_app.add_handler(CommandHandler("faq", cmd_faq))
    bot_app.add_handler(CommandHandler("canned", cmd_canned))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/admin/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=Update.ALL_TYPES,
            )
            logger.info("✅ Admin Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ Admin Bot Webhook Failed: {e}")

    await start_monitoring(bot_app)
    logger.info("👑 Admin Bot: Online")


async def stop_service():
    await stop_monitoring()

    for t in list(background_tasks):
        t.cancel()

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

    await dispose_admin_engine()
    logger.info("👑 Admin Bot: Stopped")


@router.post("/webhook/admin/{secret}")
async def admin_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)

    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Admin Webhook Error: {e}")
        return Response(status_code=200)
