from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from core.logger import setup_logger
from zenith_support_bot.repository import TicketRepo

logger = setup_logger("SUPPORT_USER")


async def cmd_my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tickets = await TicketRepo.get_user_tickets(user_id, open_only=False)
    
    if not tickets:
        await update.message.reply_text(
            "📋 <b>Your Tickets</b>\n\n"
            "You haven't created any tickets yet.\n\n"
            "Use <code>/ticket [subject] | [description]</code> to create one.",
            parse_mode="HTML",
        )
        return

    lines = ["<b>📋 YOUR TICKETS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
    
    for ticket in tickets[:10]:
        status_emoji = {
            "open": "🟢",
            "in_progress": "🟡",
            "resolved": "✅",
            "closed": "❌",
        }.get(ticket.status, "⚪")
        
        status_text = ticket.status.replace("_", " ").upper()
        created = ticket.created_at.strftime("%d %b %H:%M") if ticket.created_at else "N/A"
        
        has_reply = " 👤" if ticket.last_admin_reply_at else ""
        
        lines.append(
            f"{status_emoji} <b>#{ticket.id}</b> {ticket.subject[:30]}\n"
            f"   Status: {status_text} | Created: {created}{has_reply}"
        )

    if len(tickets) > 10:
        lines.append(f"\n<i>...and {len(tickets) - 10} more tickets</i>")

    keyboard = []
    if any(t.status in ["open", "in_progress", "resolved"] for t in tickets):
        keyboard.append([InlineKeyboardButton("🎫 Create New Ticket", callback_data="support_new_ticket")])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        parse_mode="HTML",
    )


async def cmd_ticket_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🎫 <b>Ticket Status</b>\n\n"
            "<b>Usage:</b> <code>/status [TICKET_ID]</code>\n\n"
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

    if ticket.user_id != update.effective_user.id:
        await update.message.reply_text("⛔ You can only view your own tickets.")
        return

    status_emoji = {
        "open": "🟢",
        "in_progress": "🟡",
        "resolved": "✅",
        "closed": "❌",
    }.get(ticket.status, "⚪")

    created = ticket.created_at.strftime("%d %b %Y %H:%M") if ticket.created_at else "N/A"
    updated = ticket.updated_at.strftime("%d %b %Y %H:%M") if ticket.updated_at else "N/A"

    lines = [
        f"🎫 <b>TICKET #{ticket.id}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>Subject:</b> {ticket.subject}",
        f"<b>Status:</b> {status_emoji} {ticket.status.upper()}",
        f"<b>Priority:</b> {ticket.priority.upper()}",
        f"<b>Created:</b> {created}",
        f"<b>Updated:</b> {updated}",
    ]

    if ticket.description:
        lines.append(f"\n<b>Description:</b>\n{ticket.description[:500]}")

    if ticket.admin_response:
        admin_time = ticket.last_admin_reply_at.strftime("%d %b %H:%M") if ticket.last_admin_reply_at else "N/A"
        lines.append(f"\n<b>Admin Response:</b>\n{ticket.admin_response[:500]}")
        lines.append(f"<i>Replied: {admin_time}</i>")

    keyboard = []
    if ticket.status in ["open", "in_progress", "resolved"]:
        keyboard.append([InlineKeyboardButton("💬 Reply to Ticket", callback_data=f"ticket_reply_{ticket.id}")])
    if ticket.status in ["open", "in_progress"]:
        keyboard.append([InlineKeyboardButton("❌ Close Ticket", callback_data=f"ticket_close_user_{ticket.id}")])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        parse_mode="HTML",
    )


async def handle_ticket_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ticket_id = int(query.data.split("_")[-1])
    ticket = await TicketRepo.get_ticket(ticket_id)
    
    if not ticket or ticket.user_id != update.effective_user.id:
        await query.edit_message_text("⛔ Ticket not found or access denied.")
        return

    context.user_data["pending_ticket_reply"] = ticket_id
    
    await query.edit_message_text(
        f"💬 <b>Reply to Ticket #{ticket.id}</b>\n\n"
        "Please send your reply to this ticket.\n\n"
        "Type your response below:",
        parse_mode="HTML",
    )


async def handle_ticket_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ticket_id = int(query.data.split("_")[-1])
    ticket = await TicketRepo.get_ticket(ticket_id)
    
    if not ticket or ticket.user_id != update.effective_user.id:
        await query.edit_message_text("⛔ Ticket not found or access denied.")
        return
    
    if ticket.status == "closed":
        await query.edit_message_text("⛔ This ticket is already closed.")
        return
    
    if ticket.status not in ["open", "in_progress", "resolved"]:
        await query.edit_message_text("⛔ This ticket cannot be closed.")
        return
    
    success = await TicketRepo.close_ticket(ticket_id, update.effective_user.id)
    
    if success:
        await query.edit_message_text(
            f"✅ <b>Ticket #{ticket.id} Closed</b>\n\n"
            "This ticket has been marked as resolved/closed.\n\n"
            "Thank you for using our support!",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text(
            "⚠️ Failed to close ticket. Please try again.",
            parse_mode="HTML",
        )


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
        await update.message.reply_text(
            f"✅ <b>Reply Sent</b>\n\n"
            f"Your reply to Ticket #{ticket_id} has been submitted.\n\n"
            "Our team will review your response shortly.",
            parse_mode="HTML",
        )
        
        keyboard = [[InlineKeyboardButton("📋 View All Tickets", callback_data="support_my_tickets")]]
        await update.message.reply_text(
            "What would you like to do next?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.message.reply_text(
            "⚠️ Failed to send reply. Please try again.",
            parse_mode="HTML",
        )

    context.user_data.pop("pending_ticket_reply", None)
    return True
