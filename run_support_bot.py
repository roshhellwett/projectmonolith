import html
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import RetryAfter, BadRequest, Forbidden

from core.logger import setup_logger
from core.config import SUPPORT_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from core.task_manager import fire_and_forget
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_support_bot.repository import (
    init_support_db, dispose_support_engine, TicketRepo, FAQRepo,
)
from zenith_support_bot.ui import (
    get_support_dashboard, get_back_button, get_ticket_keyboard,
    get_ticket_detail_keyboard, get_faq_keyboard, get_welcome_msg,
    get_ticket_status_msg, get_ticket_created_msg, get_priority_keyboard,
)
from zenith_support_bot.ai_responder import generate_ai_response
from zenith_support_bot.pro_handlers import (
    cmd_priority, cmd_savereply, cmd_replies, cmd_reply,
    cmd_addfaq, cmd_delfaq, cmd_rate, cmd_stats, cmd_resolve,
)

logger = setup_logger("SUPPORT")
router = APIRouter()
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
    user_id = update.effective_user.id
    await SubscriptionRepo.register_user(user_id)
    first_name = html.escape(update.effective_user.first_name or "User")
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    open_tickets = await TicketRepo.count_open_tickets(user_id) if not is_pro else 0
    
    await update.message.reply_text(
        get_welcome_msg(first_name, is_pro, days_left),
        reply_markup=get_support_dashboard(is_pro, open_tickets),
        parse_mode="HTML",
    )


async def cmd_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    username = update.effective_user.username or update.effective_user.first_name or "Unknown"
    
    max_tickets = 15 if is_pro else 3
    open_tickets = await TicketRepo.count_open_tickets(user_id)
    
    if open_tickets >= max_tickets:
        await update.message.reply_text(
            f"⚠️ <b>Ticket Limit Reached</b>\n\n"
            f"You have {open_tickets} open ticket(s). Maximum allowed: {max_tickets}\n\n"
            f"{'💎 Upgrade to Pro for 15 tickets!' if not is_pro else ''}",
            parse_mode="HTML",
        )
        return

    if not context.args:
        await update.message.reply_text(
            "🎫 <b>Create Support Ticket</b>\n\n"
            "Usage: <code>/ticket [subject] | [description]</code>\n\n"
            "Example: <code>/ticket Login Issue | I can't log into my account</code>",
            parse_mode="HTML",
        )
        return

    args = " ".join(context.args).split(" | ")
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ Use <code>|</code> to separate subject and description.\n\n"
            "Example: <code>/ticket Login Issue | I can't log into my account</code>",
            parse_mode="HTML",
        )
        return

    subject = args[0].strip()
    description = args[1].strip()

    msg = await update.message.reply_text("<i>Creating ticket...</i>", parse_mode="HTML")
    
    ticket = await TicketRepo.create_ticket(user_id, username, subject, description)
    
    ai_response = None
    if is_pro:
        try:
            ai_response = await generate_ai_response(subject, description)
            if ai_response:
                await TicketRepo.set_ai_response(ticket.id, ai_response)
        except Exception as e:
            logger.error(f"AI response failed: {e}")

    await msg.edit_text(
        get_ticket_created_msg(ticket.id, ai_response),
        reply_markup=get_back_button(),
        parse_mode="HTML",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/status [TICKET_ID]</code>\n\n"
            "Example: <code>/status 5</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID.")
        return

    ticket = await TicketRepo.get_ticket(ticket_id)
    if not ticket:
        await update.message.reply_text("⚠️ Ticket not found.")
        return

    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0

    await update.message.reply_text(
        get_ticket_status_msg(ticket, is_pro),
        reply_markup=get_ticket_detail_keyboard(ticket.id, ticket.user_id == user_id, is_pro, user_id == ADMIN_USER_ID),
        parse_mode="HTML",
    )


async def cmd_mytickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tickets = await TicketRepo.get_user_tickets(user_id, open_only=False)
    
    if not tickets:
        await update.message.reply_text(
            "🎫 <b>Your Tickets</b>\n\nNo tickets found. Use /ticket to create one.",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        "🎫 <b>Your Tickets</b>",
        reply_markup=get_ticket_keyboard(tickets),
        parse_mode="HTML",
    )


async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    
    faqs = await FAQRepo.get_all_faqs(limit=50 if is_pro else 10)
    
    if not faqs:
        await update.message.reply_text(
            "❓ <b>FAQ</b>\n\nNo FAQ entries available.",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        "❓ <b>Frequently Asked Questions</b>",
        reply_markup=get_faq_keyboard(faqs),
        parse_mode="HTML",
    )


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/close [TICKET_ID]</code>\n\n"
            "Example: <code>/close 5</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID.")
        return

    user_id = update.effective_user.id
    success = await TicketRepo.close_ticket(ticket_id, user_id)
    
    if success:
        await update.message.reply_text(
            f"✅ <b>Ticket Closed</b>\n\nTicket #{ticket_id} has been closed.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "⚠️ Could not close ticket. It may already be closed or you don't own this ticket.",
            parse_mode="HTML",
        )


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "⚠️ <b>Invalid Format.</b> Use: <code>/activate [YOUR_KEY]</code>",
            parse_mode="HTML",
        )
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return await update.message.reply_text("⛔ Unauthorized.")
    try:
        days = int(context.args[0]) if context.args else 30
    except ValueError:
        return await update.message.reply_text("⚠️ Invalid day count. Usage: <code>/keygen [DAYS]</code>", parse_mode="HTML")
    key = await SubscriptionRepo.generate_key(days)
    await update.message.reply_text(f"🔑 <b>Key Generated:</b> <code>{key}</code>\nDuration: <b>{days} days</b>", parse_mode="HTML")


async def cmd_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return await update.message.reply_text("⛔ Unauthorized.")
    if not context.args:
        return await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/extend [USER_ID] [DAYS]</code>\n"
            "Example: <code>/extend 123456789 30</code>",
            parse_mode="HTML",
        )
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("⚠️ Invalid user ID.")
    days = 30
    if len(context.args) > 1:
        try:
            days = int(context.args[1])
        except ValueError:
            return await update.message.reply_text("⚠️ Invalid day count.")
    success, msg = await SubscriptionRepo.extend_subscription(target_user_id, days)
    await update.message.reply_text(msg, parse_mode="HTML")


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    first_name = html.escape(update.effective_user.first_name or "User")
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0

    try:
        if query.data == "sup_main_menu":
            open_tickets = await TicketRepo.count_open_tickets(user_id) if not is_pro else 0
            await query.edit_message_text(
                get_welcome_msg(first_name, is_pro, days_left),
                reply_markup=get_support_dashboard(is_pro, open_tickets),
                parse_mode="HTML",
            )

        elif query.data == "sup_status":
            status = f"🟢 <b>Active</b> — {days_left} days remaining" if is_pro else "🔴 <b>Inactive</b> — Standard Tier"
            pro_features = (
                "\n<b>Pro Features:</b>\n"
                "• 15 open tickets (vs 3 free)\n"
                "• AI auto-response\n"
                "• Priority support\n"
                "• Custom FAQ builder\n"
                "• Canned responses\n"
                "• Analytics\n"
                "• Auto-close tickets\n"
                "• Satisfaction ratings"
            )
            await query.edit_message_text(
                f"<b>💎 Zenith Pro</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Status:</b> {status}\n{pro_features}\n\n"
                f"<b>Activation:</b>\n<code>/activate ZENITH-XXXX-XXXX</code>\n\n"
                f"<i>User ID: {user_id}</i>",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "sup_my_tickets":
            tickets = await TicketRepo.get_user_tickets(user_id, open_only=False)
            if not tickets:
                await query.edit_message_text(
                    "🎫 <b>Your Tickets</b>\n\nNo tickets found. Use /ticket to create one.",
                    reply_markup=get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    "🎫 <b>Your Tickets</b>",
                    reply_markup=get_ticket_keyboard(tickets),
                    parse_mode="HTML",
                )

        elif query.data == "sup_faq":
            faqs = await FAQRepo.get_all_faqs(limit=50 if is_pro else 10)
            if not faqs:
                await query.edit_message_text(
                    "❓ <b>FAQ</b>\n\nNo FAQ entries available.",
                    reply_markup=get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    "❓ <b>Frequently Asked Questions</b>",
                    reply_markup=get_faq_keyboard(faqs),
                    parse_mode="HTML",
                )

        elif query.data == "sup_new_ticket":
            await query.edit_message_text(
                "🎫 <b>Create New Ticket</b>\n\n"
                "Use command: <code>/ticket [subject] | [description]</code>\n\n"
                "Example: <code>/ticket Login Issue | I can't log into my account</code>",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "sup_stats":
            if not is_pro:
                await query.edit_message_text(
                    "🔒 <b>Pro Feature: Analytics</b>\n\nUpgrade to Pro to view ticket statistics.",
                    reply_markup=get_back_button(),
                    parse_mode="HTML",
                )
                return
            
            stats = await TicketRepo.get_ticket_stats()
            await query.edit_message_text(
                f"📊 <b>Support Analytics</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Total Tickets:</b> {stats['total']}\n"
                f"<b>Open:</b> {stats['open']}\n"
                f"<b>In Progress:</b> {stats['in_progress']}\n"
                f"<b>Resolved:</b> {stats['resolved']}\n"
                f"<b>Closed:</b> {stats['closed']}\n\n"
                f"<b>Avg. Rating:</b> {stats['avg_rating']} / 5 ⭐",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "sup_canned":
            if not is_pro:
                await query.edit_message_text(
                    "🔒 <b>Pro Feature: Canned Responses</b>\n\nUpgrade to Pro to access saved reply templates.",
                    reply_markup=get_back_button(),
                    parse_mode="HTML",
                )
                return
            await query.edit_message_text(
                "💾 Use /savereply to add, /replies to view, /reply to use.",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_ticket_"):
            ticket_id = int(query.data.split("_")[-1])
            ticket = await TicketRepo.get_ticket(ticket_id)
            if not ticket:
                await query.edit_message_text("⚠️ Ticket not found.", reply_markup=get_back_button())
                return
            
            is_owner = ticket.user_id == user_id
            await query.edit_message_text(
                get_ticket_status_msg(ticket, is_pro),
                reply_markup=get_ticket_detail_keyboard(ticket.id, is_owner, is_pro, user_id == ADMIN_USER_ID),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_faq_"):
            faq_id = int(query.data.split("_")[-1])
            faq = await FAQRepo.get_faq(faq_id)
            if not faq:
                await query.edit_message_text("⚠️ FAQ not found.", reply_markup=get_back_button())
                return
            
            await query.edit_message_text(
                f"❓ <b>{faq.question}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{faq.answer}\n\n<i>Category: {faq.category}</i>",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_close_"):
            ticket_id = int(query.data.split("_")[-1])
            success = await TicketRepo.close_ticket(ticket_id, user_id)
            if success:
                await query.edit_message_text(
                    f"✅ Ticket #{ticket_id} closed.",
                    reply_markup=get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    "⚠️ Could not close ticket.",
                    reply_markup=get_back_button(),
                    parse_mode="HTML",
                )

        elif query.data.startswith("sup_priority_"):
            ticket_id = int(query.data.split("_")[-1])
            if not is_pro:
                await query.edit_message_text(
                    "🔒 Pro feature.",
                    reply_markup=get_back_button(),
                    parse_mode="HTML",
                )
                return
            await query.edit_message_text(
                f"Select priority for ticket #{ticket_id}:",
                reply_markup=get_priority_keyboard(ticket_id),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_prio_"):
            parts = query.data.split("_")
            ticket_id = int(parts[2])
            priority = parts[3]
            await TicketRepo.set_priority(ticket_id, priority)
            await query.edit_message_text(
                f"✅ Priority set to <b>{priority.upper()}</b>",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_resolve_"):
            ticket_id = int(query.data.split("_")[-1])
            if user_id != ADMIN_USER_ID:
                await query.edit_message_text("⛔ Admin only.", reply_markup=get_back_button())
                return
            await query.edit_message_text(
                f"✅ Use /resolve {ticket_id} [response] to resolve this ticket.",
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_noop"):
            pass

    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.error(f"UI Error: {e}")


async def auto_close_stale_tickets():
    while True:
        await asyncio.sleep(3600)
        try:
            stale_tickets = await TicketRepo.get_stale_tickets(days=7)
            for ticket in stale_tickets:
                await TicketRepo.update_ticket_status(ticket.id, "closed")
                logger.info(f"Auto-closed stale ticket #{ticket.id}")
        except Exception as e:
            logger.error(f"Auto-close error: {e}")


async def start_service():
    global bot_app
    if not SUPPORT_BOT_TOKEN:
        return

    await init_support_db()
    bot_app = ApplicationBuilder().token(SUPPORT_BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("ticket", cmd_ticket))
    bot_app.add_handler(CommandHandler("status", cmd_status))
    bot_app.add_handler(CommandHandler("mytickets", cmd_mytickets))
    bot_app.add_handler(CommandHandler("faq", cmd_faq))
    bot_app.add_handler(CommandHandler("close", cmd_close))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen))
    bot_app.add_handler(CommandHandler("extend", cmd_extend))
    
    bot_app.add_handler(CommandHandler("priority", lambda u, c: cmd_priority(u, c, True)))
    bot_app.add_handler(CommandHandler("savereply", lambda u, c: cmd_savereply(u, c, True)))
    bot_app.add_handler(CommandHandler("replies", lambda u, c: cmd_replies(u, c, True)))
    bot_app.add_handler(CommandHandler("reply", lambda u, c: cmd_reply(u, c, True)))
    bot_app.add_handler(CommandHandler("rate", lambda u, c: cmd_rate(u, c, True)))
    bot_app.add_handler(CommandHandler("stats", lambda u, c: cmd_stats(u, c, True)))
    bot_app.add_handler(CommandHandler("resolve", lambda u, c: cmd_resolve(u, c, True)))
    bot_app.add_handler(CommandHandler("addfaq", lambda u, c: cmd_addfaq(u, c, True, u.effective_user.id == ADMIN_USER_ID)))
    bot_app.add_handler(CommandHandler("delfaq", lambda u, c: cmd_delfaq(u, c, u.effective_user.id == ADMIN_USER_ID)))
    
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"
    if webhook_base:
        try:
            path = f"{webhook_base}/webhook/support/{WEBHOOK_SECRET}"
            await bot_app.bot.set_webhook(url=path, secret_token=WEBHOOK_SECRET, allowed_updates=Update.ALL_TYPES)
        except Exception:
            pass

    track_task(asyncio.create_task(safe_loop("auto_close", auto_close_stale_tickets)))


async def stop_service():
    for t in list(background_tasks):
        t.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_support_engine()


@router.post("/webhook/support/{secret}")
async def support_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook payload error: {e}")
        return Response(status_code=200)
