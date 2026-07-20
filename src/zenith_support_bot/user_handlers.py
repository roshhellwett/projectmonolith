import contextlib

from telegram import Update
from telegram.ext import ContextTypes

from core.logger import setup_logger
from zenith_support_bot import ui as support_ui
from zenith_support_bot.repository import TicketRepo

logger = setup_logger("SUPPORT_USER")


async def handle_ticket_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()

    ticket_id = int(query.data.split("_")[-1])
    ticket = await TicketRepo.get_ticket(ticket_id)

    if not ticket or ticket.user_id != update.effective_user.id:
        await query.edit_message_text(support_ui.get_user_close_denied())
        return

    context.user_data["pending_ticket_reply"] = ticket_id
    text, kb = support_ui.get_user_reply_prompt(ticket_id)
    await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")


async def handle_ticket_cancel_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer("Reply cancelled.")
    context.user_data.pop("pending_ticket_reply", None)

    ticket_id = int(query.data.split("_")[-1])
    ticket = await TicketRepo.get_ticket(ticket_id)
    if not ticket:
        await query.edit_message_text(support_ui.get_ticket_not_found_msg(), reply_markup=support_ui.get_back_button())
        return

    user_id = update.effective_user.id
    from core.permissions import resolve_tier

    tier = await resolve_tier(user_id)

    await query.edit_message_text(
        support_ui.get_ticket_status_msg(ticket, tier.is_pro, tier.is_owner),
        reply_markup=support_ui.get_ticket_detail_keyboard(
            ticket.id, tier.is_owner, tier.is_pro, tier.is_owner, ticket.user_id == user_id
        ),
        parse_mode="HTML",
    )


async def handle_ticket_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()

    ticket_id = int(query.data.split("_")[-1])
    ticket = await TicketRepo.get_ticket(ticket_id)

    if not ticket or ticket.user_id != update.effective_user.id:
        await query.edit_message_text(support_ui.get_user_close_denied())
        return

    if ticket.status == "closed":
        await query.edit_message_text(support_ui.get_user_close_already())
        return

    if ticket.status not in ["open", "in_progress", "resolved"]:
        await query.edit_message_text(support_ui.get_user_close_cannot())
        return

    success = await TicketRepo.close_ticket(ticket_id, update.effective_user.id)
    if success:
        await query.edit_message_text(support_ui.get_user_close_success(ticket_id), parse_mode="HTML")
    else:
        await query.edit_message_text(support_ui.get_user_close_failure())


async def handle_ticket_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticket_id = context.user_data.get("pending_ticket_reply")
    if not ticket_id:
        return False

    ticket = await TicketRepo.get_ticket(ticket_id)
    if not ticket or ticket.user_id != update.effective_user.id:
        return False

    user_reply = update.message.text
    success = await TicketRepo.set_user_reply(ticket_id, user_reply)
    if success:
        await update.message.reply_text(support_ui.get_user_reply_success(ticket_id), parse_mode="HTML")
        await update.message.reply_text(
            support_ui.get_user_what_next_msg(),
            reply_markup=support_ui.get_user_what_next_keyboard(),
        )
    else:
        await update.message.reply_text(support_ui.get_user_reply_failure(), parse_mode="HTML")

    context.user_data.pop("pending_ticket_reply", None)
    return True
