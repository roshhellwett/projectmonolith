from telegram import Update
from telegram.ext import ContextTypes

from core.validators import validate_priority
from core.animation import send_typing_action
from zenith_support_bot.repository import TicketRepo, FAQRepo, CannedRepo
from zenith_support_bot.ui import (
    get_priority_keyboard, get_canned_keyboard, get_faq_keyboard,
    get_confirm_close_ticket, get_confirm_close_ticket_msg,
    get_rating_keyboard, get_rating_thanks_msg, get_limit_reached_msg,
    get_pro_feature_msg,
)


async def cmd_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool):
    if not is_pro:
        msg, kb = get_pro_feature_msg("Priority Support")
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "🏷️ <b>Set Ticket Priority</b>\n\n"
            "<b>Usage:</b> <code>/priority [TICKET_ID] [low|normal|high|urgent]</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/priority 5 high</code>\n"
            "• <code>/priority 12 urgent</code>\n\n"
            "<i>💡 Urgent tickets get faster response</i>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "⚠️ <b>Invalid Ticket ID</b>\n\n"
            "Ticket ID must be a number.\n\n"
            "Use <code>/tickets</code> to see your tickets.",
            parse_mode="HTML"
        )
        return

    priority = context.args[1].lower()
    
    validation = validate_priority(priority)
    if not validation.is_valid:
        await update.message.reply_text(
            f"⚠️ <b>Invalid Priority</b>\n\n{validation.error_message}\n\n"
            "Valid options: low, normal, high, urgent",
            parse_mode="HTML"
        )
        return
    
    priority = validation.sanitized_value

    success = await TicketRepo.set_priority(ticket_id, priority)
    if success:
        emoji = {"low": "⬇️", "normal": "➡️", "high": "⬆️", "urgent": "🚨"}.get(priority, "➡️")
        await update.message.reply_text(
            f"✅ <b>Priority Updated</b>\n\n"
            f"Ticket #{ticket_id} priority set to {emoji} <b>{priority.upper()}</b>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "⚠️ <b>Ticket Not Found</b>\n\n"
            "The ticket may not exist or is already closed.\n\n"
            "Use <code>/tickets</code> to see your tickets.",
            parse_mode="HTML"
        )


async def cmd_savereply(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool):
    if not is_pro:
        msg, kb = get_pro_feature_msg("Canned Responses")
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "💾 <b>Save Canned Response</b>\n\n"
            "<b>Usage:</b> <code>/savereply [tag] | [content]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/savereply greeting | Hello! Thank you for contacting support.</code>\n\n"
            "<i>💡 Use | to separate tag and content</i>",
            parse_mode="HTML",
        )
        return

    args = " ".join(context.args).split(" | ")
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Invalid Format</b>\n\n"
            "Use <code>|</code> to separate tag and content.\n\n"
            "<b>Example:</b>\n"
            "<code>/savereply greeting | Hello! Thank you for contacting support.</code>",
            parse_mode="HTML",
        )
        return

    tag = args[0].strip()
    content = args[1].strip()

    if len(tag) > 50:
        await update.message.reply_text(
            "⚠️ <b>Tag Too Long</b>\n\n"
            "Tag must be under 50 characters.",
            parse_mode="HTML"
        )
        return
    
    if len(content) < 5:
        await update.message.reply_text(
            "⚠️ <b>Content Too Short</b>\n\n"
            "Content must be at least 5 characters.",
            parse_mode="HTML"
        )
        return

    count = await CannedRepo.count_canned()
    limit = 50
    if count >= limit:
        msg = get_limit_reached_msg("Canned Responses", count, limit)
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    await CannedRepo.add_canned(tag, content, update.effective_user.id)
    await update.message.reply_text(
        f"✅ <b>Canned Response Saved</b>\n\n"
        f"🏷️ <b>Tag:</b> <code>{tag}</code>\n\n"
        f"📝 <b>Content:</b>\n{content[:200]}...",
        parse_mode="HTML",
    )


async def cmd_replies(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool):
    if not is_pro:
        await update.message.reply_text(
            "🔒 <b>Pro Feature: Canned Responses</b>\n\n"
            "Upgrade to Pro to access saved reply templates.",
            parse_mode="HTML",
        )
        return

    canned_list = await CannedRepo.get_all_canned()
    if not canned_list:
        await update.message.reply_text(
            "💾 <b>Canned Responses</b>\n\nNo saved responses yet.\n"
            "Use /savereply [tag] | [content] to create one.",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        "💾 <b>Saved Responses</b>",
        reply_markup=get_canned_keyboard(canned_list),
        parse_mode="HTML",
    )


async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool):
    if not is_pro:
        await update.message.reply_text(
            "🔒 <b>Pro Feature: Canned Responses</b>\n\n"
            "Upgrade to Pro to use canned responses.",
            parse_mode="HTML",
        )
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/reply [TICKET_ID] [tag]</code>\n\n"
            "Example: <code>/reply 5 greeting</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID.")
        return

    tag = context.args[1].strip()
    canned = await CannedRepo.get_canned(tag)

    if not canned:
        await update.message.reply_text(f"⚠️ Canned response '{tag}' not found. Use /replies to see available responses.")
        return

    await CannedRepo.increment_usage(tag)

    success = await TicketRepo.set_admin_response(ticket_id, canned.content)
    if success:
        await update.message.reply_text(
            f"✅ <b>Response Applied</b>\n\nTicket #{ticket_id} replied with: {canned.content[:200]}...",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("⚠️ Ticket not found.")


async def cmd_addfaq(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_admin: bool = False):
    if not is_admin:
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/addfaq [question] | [answer]</code>\n\n"
            "Example: <code>/addfaq How do I reset password? | Click on settings and...</code>\n\n"
            "Categories: general, billing, tickets, technical",
            parse_mode="HTML",
        )
        return

    args = " ".join(context.args).split(" | ")
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ Use <code>|</code> to separate question and answer.\n"
            "Example: <code>/addfaq Question | Answer</code>",
            parse_mode="HTML",
        )
        return

    question = args[0].strip()
    answer = args[1].strip()
    category = "general"

    if len(args) > 2:
        category = args[2].strip().lower()

    count = await FAQRepo.count_faqs()
    if count >= 100:
        await update.message.reply_text("⚠️ Maximum 100 FAQ entries allowed.")
        return

    faq = await FAQRepo.add_faq(question, answer, category, update.effective_user.id)
    await update.message.reply_text(
        f"✅ <b>FAQ Added</b>\n\nID: <code>{faq.id}</code>\n"
        f"Q: {question[:50]}...\n"
        f"Category: {category}",
        parse_mode="HTML",
    )


async def cmd_delfaq(update: Update, context: ContextTypes.DEFAULT_TYPE, is_admin: bool = False):
    if not is_admin:
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/delfaq [ID]</code>", parse_mode="HTML")
        return

    try:
        faq_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid FAQ ID.")
        return

    success = await FAQRepo.delete_faq(faq_id)
    if success:
        await update.message.reply_text(f"✅ FAQ #{faq_id} deleted.")
    else:
        await update.message.reply_text("⚠️ FAQ not found.")


async def cmd_rate(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool):
    if not is_pro:
        await update.message.reply_text(
            "🔒 <b>Pro Feature: Satisfaction Ratings</b>\n\n"
            "Upgrade to Pro to rate resolved tickets.",
            parse_mode="HTML",
        )
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/rate [TICKET_ID] [1-5]</code>\n\n"
            "Example: <code>/rate 5 5</code>",
            parse_mode="HTML",
        )
        return

    try:
        ticket_id = int(context.args[0])
        rating = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ticket ID or rating.")
        return

    if rating < 1 or rating > 5:
        await update.message.reply_text("⚠️ Rating must be between 1 and 5.")
        return

    ticket = await TicketRepo.get_ticket(ticket_id)
    if not ticket:
        await update.message.reply_text("⚠️ Ticket not found.")
        return

    if ticket.user_id != update.effective_user.id:
        await update.message.reply_text("⚠️ You can only rate your own tickets.")
        return

    if ticket.status not in ["resolved", "closed"]:
        await update.message.reply_text("⚠️ Can only rate resolved tickets.")
        return

    success = await TicketRepo.set_rating(ticket_id, rating)
    if success:
        stars = "⭐" * rating
        await update.message.reply_text(
            f"✅ <b>Rating Submitted</b>\n\nTicket #{ticket_id}: {stars}\n\nThank you for your feedback!",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("⚠️ Failed to submit rating.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool):
    if not is_pro:
        await update.message.reply_text(
            "🔒 <b>Pro Feature: Ticket Analytics</b>\n\n"
            "Upgrade to Pro to view ticket statistics.",
            parse_mode="HTML",
        )
        return

    stats = await TicketRepo.get_ticket_stats()

    msg = f"""📊 <b>Support Analytics</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>Total Tickets:</b> {stats['total']}
<b>Open:</b> {stats['open']}
<b>In Progress:</b> {stats['in_progress']}
<b>Resolved:</b> {stats['resolved']}
<b>Closed:</b> {stats['closed']}

<b>Avg. Rating:</b> {stats['avg_rating']} / 5 ⭐"""

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE, is_admin: bool = False):
    if not is_admin:
        await update.message.reply_text("⛔ Admin only.")
        return

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
        await update.message.reply_text(
            f"✅ <b>Ticket Resolved</b>\n\nTicket #{ticket_id} has been resolved with your response.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("⚠️ Ticket not found.")
