import asyncio
import html

from fastapi import APIRouter, Request
from fastapi.responses import Response
from telegram import Update
from telegram.error import BadRequest, RetryAfter
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from core.config import SUPPORT_BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL, is_owner
from core.database import dispose_engine
from core.error_handler import handle_bot_error
from core.logger import setup_logger
from core.permissions import resolve_tier
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_support_bot import ui as support_ui
from zenith_support_bot.ai_responder import generate_ai_response
from zenith_support_bot.notifications import notify_admin_new_ticket, set_notification_bot
from zenith_support_bot.pro_handlers import (
    cmd_addfaq,
    cmd_delfaq,
    cmd_priority,
    cmd_rate,
    cmd_replies,
    cmd_reply,
    cmd_resolve,
    cmd_savereply,
    cmd_stats,
)
from zenith_support_bot.repository import FAQRepo, TicketRepo, seed_default_faq
from zenith_support_bot.scheduler import start_ticket_scheduler, stop_ticket_scheduler
from zenith_support_bot.user_handlers import (
    handle_ticket_cancel_reply_callback,
    handle_ticket_close_callback,
    handle_ticket_reply_callback,
    handle_ticket_reply_message,
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
    is_owner_user = is_owner(user_id)
    open_tickets = await TicketRepo.count_open_tickets(user_id)

    await update.message.reply_text(
        support_ui.get_welcome_msg(first_name, is_pro, days_left, open_tickets, is_owner_user),
        reply_markup=support_ui.get_support_dashboard(is_pro, open_tickets, is_owner_user),
        parse_mode="HTML",
    )


async def cmd_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_owner_user = is_owner(user_id)
    days_left = await SubscriptionRepo.get_days_left(user_id)

    if not is_owner_user and days_left <= 0:
        await update.message.reply_text(support_ui.get_subs_only_msg(), parse_mode="HTML")
        return

    is_pro = days_left > 0
    max_tickets = 999 if is_owner_user else (15 if is_pro else 3)
    open_tickets = await TicketRepo.count_open_tickets(user_id)

    if open_tickets >= max_tickets:
        upgrade_msg = ""
        if not is_owner_user and not is_pro:
            upgrade_msg = "Upgrade to Pro for 15 tickets!"
        await update.message.reply_text(support_ui.get_ticket_limit_msg(open_tickets, max_tickets, upgrade_msg), parse_mode="HTML")
        return

    if not context.args:
        await update.message.reply_text(support_ui.get_ticket_help(), parse_mode="HTML")
        return

    args = " ".join(context.args).split(" | ")
    if len(args) < 2:
        await update.message.reply_text(support_ui.get_ticket_pipe_error(), parse_mode="HTML")
        return

    subject = args[0].strip()
    description = args[1].strip()
    username = update.effective_user.username or update.effective_user.first_name or "Unknown"

    msg = await update.message.reply_text("Creating ticket...")
    ticket = await TicketRepo.create_ticket(user_id, username, subject, description)
    asyncio.create_task(notify_admin_new_ticket(ticket.id, user_id, username, subject, description))

    ai_response = None
    if is_pro or is_owner_user:
        try:
            ai_response = await generate_ai_response(subject, description)
            if ai_response:
                await TicketRepo.set_ai_response(ticket.id, ai_response)
        except Exception as e:
            logger.error(f"AI response failed: {e}")

    await msg.edit_text(
        support_ui.get_ticket_created_msg(ticket.id, ai_response),
        reply_markup=support_ui.get_back_button(),
        parse_mode="HTML",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(support_ui.get_status_usage(), parse_mode="HTML")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(support_ui.get_status_invalid())
        return

    ticket = await TicketRepo.get_ticket(ticket_id)
    if not ticket:
        await update.message.reply_text(support_ui.get_status_not_found())
        return

    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    is_owner_user = is_owner(user_id)

    await update.message.reply_text(
        support_ui.get_ticket_status_msg(ticket, is_pro, is_owner_user),
        reply_markup=support_ui.get_ticket_detail_keyboard(
            ticket.id, is_owner_user, is_pro, is_owner_user, ticket.user_id == user_id
        ),
        parse_mode="HTML",
    )


async def cmd_mytickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tickets = await TicketRepo.get_user_tickets(user_id, open_only=False)

    if not tickets:
        await update.message.reply_text(support_ui.get_my_tickets_empty(), parse_mode="HTML")
        return

    await update.message.reply_text(
        "<b>Your Tickets</b>",
        reply_markup=support_ui.get_ticket_keyboard(tickets),
        parse_mode="HTML",
    )


async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    is_owner_user = is_owner(user_id)

    faqs = await FAQRepo.get_all_faqs(limit=50 if (is_pro or is_owner_user) else 10)
    if not faqs:
        await update.message.reply_text(support_ui.get_faq_empty(), parse_mode="HTML")
        return

    await update.message.reply_text(
        support_ui.get_faq_loaded(),
        reply_markup=support_ui.get_faq_keyboard(faqs),
        parse_mode="HTML",
    )


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(support_ui.get_close_usage(), parse_mode="HTML")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(support_ui.get_close_invalid())
        return

    user_id = update.effective_user.id
    is_owner_user = is_owner(user_id)

    if is_owner_user:
        success = await TicketRepo.admin_close_ticket(ticket_id)
    else:
        success = await TicketRepo.close_ticket(ticket_id, user_id)

    if success:
        await update.message.reply_text(support_ui.get_close_success(ticket_id), parse_mode="HTML")
    else:
        await update.message.reply_text(support_ui.get_close_failure(), parse_mode="HTML")


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(support_ui.get_activate_help(), parse_mode="HTML")
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    await update.message.reply_text(msg, parse_mode="HTML")


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    first_name = html.escape(update.effective_user.first_name or "User")
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    is_owner_user = is_owner(user_id)

    try:
        if query.data == "sup_main_menu":
            open_tickets = await TicketRepo.count_open_tickets(user_id)
            await query.edit_message_text(
                support_ui.get_welcome_msg(first_name, is_pro, days_left, open_tickets, is_owner_user),
                reply_markup=support_ui.get_support_dashboard(is_pro, open_tickets, is_owner_user),
                parse_mode="HTML",
            )

        elif query.data == "sup_status":
            await query.edit_message_text(
                support_ui.get_pro_status_msg(is_pro, days_left, is_owner_user),
                reply_markup=support_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "sup_my_tickets":
            tickets = await TicketRepo.get_user_tickets(user_id, open_only=False)
            if not tickets:
                await query.edit_message_text(
                    support_ui.get_my_tickets_empty(),
                    reply_markup=support_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    "<b>Your Tickets</b>",
                    reply_markup=support_ui.get_ticket_keyboard(tickets),
                    parse_mode="HTML",
                )

        elif query.data == "sup_faq":
            faqs = await FAQRepo.get_all_faqs(limit=50 if (is_pro or is_owner_user) else 10)
            if not faqs:
                await query.edit_message_text(
                    support_ui.get_faq_empty(),
                    reply_markup=support_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    support_ui.get_faq_loaded(),
                    reply_markup=support_ui.get_faq_keyboard(faqs),
                    parse_mode="HTML",
                )

        elif query.data == "sup_new_ticket":
            await query.edit_message_text(
                support_ui.get_new_ticket_guide(),
                reply_markup=support_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "sup_stats":
            if not is_pro and not is_owner_user:
                await query.edit_message_text(
                    support_ui.get_stats_pro_feature_msg(),
                    reply_markup=support_ui.get_back_button(),
                    parse_mode="HTML",
                )
                return

            stats = await TicketRepo.get_ticket_stats()
            await query.edit_message_text(
                support_ui.get_stats_msg(stats),
                reply_markup=support_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "sup_canned":
            if not is_pro and not is_owner_user:
                await query.edit_message_text(
                    support_ui.get_canned_feature_msg(),
                    reply_markup=support_ui.get_back_button(),
                    parse_mode="HTML",
                )
                return
            await query.edit_message_text(
                support_ui.get_canned_help_msg(),
                reply_markup=support_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_ticket_"):
            ticket_id = int(query.data.split("_")[-1])
            ticket = await TicketRepo.get_ticket(ticket_id)
            if not ticket:
                await query.edit_message_text(support_ui.get_ticket_not_found_msg(), reply_markup=support_ui.get_back_button())
                return

            is_ticket_owner = ticket.user_id == user_id
            await query.edit_message_text(
                support_ui.get_ticket_status_msg(ticket, is_pro, is_owner_user),
                reply_markup=support_ui.get_ticket_detail_keyboard(
                    ticket.id, is_owner_user, is_pro, is_owner_user, is_ticket_owner
                ),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_faq_"):
            faq_id = int(query.data.split("_")[-1])
            faq = await FAQRepo.get_faq(faq_id)
            if not faq:
                await query.edit_message_text(support_ui.get_ticket_not_found_msg(), reply_markup=support_ui.get_back_button())
                return

            await query.edit_message_text(
                support_ui.get_faq_detail(faq.question, faq.answer, faq.category),
                reply_markup=support_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_close_confirm_"):
            ticket_id = int(query.data.split("_")[-1])
            await query.edit_message_text(
                support_ui.get_confirm_close_ticket_msg(ticket_id),
                reply_markup=support_ui.get_confirm_close_ticket(ticket_id),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_close_"):
            ticket_id = int(query.data.split("_")[-1])
            if is_owner_user:
                success = await TicketRepo.admin_close_ticket(ticket_id)
            else:
                success = await TicketRepo.close_ticket(ticket_id, user_id)
            if success:
                await query.edit_message_text(
                    support_ui.get_close_success(ticket_id),
                    reply_markup=support_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    support_ui.get_close_failure(),
                    reply_markup=support_ui.get_back_button(),
                    parse_mode="HTML",
                )

        elif query.data.startswith("sup_priority_"):
            ticket_id = int(query.data.split("_")[-1])
            if not is_pro and not is_owner_user:
                msg, kb = support_ui.get_pro_feature_msg("Priority Support")
                await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")
                return
            await query.edit_message_text(
                f"Select priority for ticket #{ticket_id}:",
                reply_markup=support_ui.get_priority_keyboard(ticket_id),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_prio_"):
            parts = query.data.split("_")
            ticket_id = int(parts[2])
            priority = parts[3]
            await TicketRepo.set_priority(ticket_id, priority)
            await query.edit_message_text(
                support_ui.get_priority_success(ticket_id, priority),
                reply_markup=support_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("sup_resolve_"):
            ticket_id = int(query.data.split("_")[-1])
            if not is_owner_user:
                await query.edit_message_text(support_ui.get_admin_only_msg(), reply_markup=support_ui.get_back_button())
                return
            await query.edit_message_text(
                f"Use /resolve {ticket_id} [response] to resolve this ticket.",
                reply_markup=support_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "sup_all_tickets":
            if not is_owner_user:
                await query.edit_message_text(support_ui.get_admin_only_msg(), reply_markup=support_ui.get_back_button())
                return
            tickets = await TicketRepo.get_all_tickets(limit=50)
            if not tickets:
                await query.edit_message_text(
                    support_ui.get_all_tickets_empty(),
                    reply_markup=support_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    support_ui.get_all_tickets_loaded(),
                    reply_markup=support_ui.get_all_tickets_keyboard(tickets),
                    parse_mode="HTML",
                )

        elif query.data == "sup_add_faq_admin":
            if not is_owner_user:
                await query.edit_message_text(support_ui.get_admin_only_msg(), reply_markup=support_ui.get_back_button())
                return
            await query.edit_message_text(
                support_ui.get_addfaq_help(),
                reply_markup=support_ui.get_back_button(),
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

    try:
        await seed_default_faq()
    except Exception as e:
        logger.warning(f"FAQ seeding skipped (DB unavailable): {e}")

    bot_app = ApplicationBuilder().token(SUPPORT_BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("ticket", cmd_ticket))
    bot_app.add_handler(CommandHandler("status", cmd_status))
    bot_app.add_handler(CommandHandler("mytickets", cmd_mytickets))
    bot_app.add_handler(CommandHandler("faq", cmd_faq))
    bot_app.add_handler(CommandHandler("close", cmd_close))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))

    def with_tier(handler_func, pass_pro=True):
        async def wrapper(u: Update, c: ContextTypes.DEFAULT_TYPE):
            tier = await resolve_tier(u.effective_user.id)
            if pass_pro:
                await handler_func(u, c, tier.is_pro, tier.is_owner)
            else:
                await handler_func(u, c, tier.is_owner)
        return wrapper

    bot_app.add_handler(CommandHandler("priority", with_tier(cmd_priority)))
    bot_app.add_handler(CommandHandler("savereply", with_tier(cmd_savereply)))
    bot_app.add_handler(CommandHandler("replies", with_tier(cmd_replies)))
    bot_app.add_handler(CommandHandler("reply", with_tier(cmd_reply)))
    bot_app.add_handler(CommandHandler("rate", with_tier(cmd_rate)))
    bot_app.add_handler(CommandHandler("stats", with_tier(cmd_stats)))
    bot_app.add_handler(CommandHandler("addfaq", with_tier(cmd_addfaq)))
    bot_app.add_handler(CommandHandler("resolve", with_tier(cmd_resolve, pass_pro=False)))
    bot_app.add_handler(CommandHandler("delfaq", with_tier(cmd_delfaq, pass_pro=False)))

    bot_app.add_handler(CallbackQueryHandler(handle_ticket_reply_callback, pattern=r"^ticket_reply_"))
    bot_app.add_handler(CallbackQueryHandler(handle_ticket_cancel_reply_callback, pattern=r"^ticket_cancel_reply_"))
    bot_app.add_handler(CallbackQueryHandler(handle_ticket_close_callback, pattern=r"^ticket_close_user_"))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))
    bot_app.add_error_handler(handle_bot_error)

    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticket_reply_message))

    set_notification_bot(bot_app)

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"
    if webhook_base:
        try:
            path = f"{webhook_base}/webhook/support/{WEBHOOK_SECRET}"
            await bot_app.bot.set_webhook(url=path, secret_token=WEBHOOK_SECRET, allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.warning(f"Failed to set webhook: {e}")

    track_task(asyncio.create_task(safe_loop("auto_close", auto_close_stale_tickets)))
    await start_ticket_scheduler()


async def stop_service():
    await stop_ticket_scheduler()
    for t in list(background_tasks):
        t.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_engine()


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
