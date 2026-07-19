from telegram import Update
from telegram.ext import ContextTypes

from core.config import is_owner
from core.validators import validate_priority
from zenith_support_bot import ui as support_ui
from zenith_support_bot.notifications import notify_user_on_admin_reply
from zenith_support_bot.repository import CannedRepo, FAQRepo, TicketRepo


async def cmd_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_owner_user: bool = False):
    is_pro = is_pro or is_owner_user
    if not is_pro:
        msg, kb = support_ui.get_pro_feature_msg("Priority Support")
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(support_ui.get_priority_help(), parse_mode="HTML")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(support_ui.get_priority_invalid_id(), parse_mode="HTML")
        return

    priority = context.args[1].lower()
    validation = validate_priority(priority)
    if not validation.is_valid:
        await update.message.reply_text(support_ui.get_priority_invalid_value(validation.error_message), parse_mode="HTML")
        return

    priority = validation.sanitized_value
    success = await TicketRepo.set_priority(ticket_id, priority)
    if success:
        await update.message.reply_text(support_ui.get_priority_success(ticket_id, priority), parse_mode="HTML")
    else:
        await update.message.reply_text(support_ui.get_priority_not_found(), parse_mode="HTML")


async def cmd_savereply(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_owner_user: bool = False):
    is_pro = is_pro or is_owner_user
    if not is_pro:
        msg, kb = support_ui.get_pro_feature_msg("Canned Responses")
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(support_ui.get_savereply_help(), parse_mode="HTML")
        return

    args = " ".join(context.args).split(" | ")
    if len(args) < 2:
        await update.message.reply_text(support_ui.get_savereply_pipe_error(), parse_mode="HTML")
        return

    tag = args[0].strip()
    content = args[1].strip()

    if len(tag) > 50:
        await update.message.reply_text(support_ui.get_savereply_tag_long())
        return

    if len(content) < 5:
        await update.message.reply_text(support_ui.get_savereply_short())
        return

    count = await CannedRepo.count_canned()
    limit = 50
    if count >= limit:
        await update.message.reply_text(support_ui.get_limit_reached_msg("Canned Responses", count, limit), parse_mode="HTML")
        return

    await CannedRepo.add_canned(tag, content, update.effective_user.id)
    await update.message.reply_text(support_ui.get_savereply_success(tag, content), parse_mode="HTML")


async def cmd_replies(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_owner_user: bool = False):
    is_pro = is_pro or is_owner_user
    if not is_pro:
        await update.message.reply_text(support_ui.get_canned_feature_msg(), parse_mode="HTML")
        return

    canned_list = await CannedRepo.get_all_canned()
    if not canned_list:
        await update.message.reply_text(support_ui.get_replies_help(), parse_mode="HTML")
        return

    await update.message.reply_text(
        support_ui.get_replies_loaded(),
        reply_markup=support_ui.get_canned_keyboard(canned_list),
        parse_mode="HTML",
    )


async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_owner_user: bool = False):
    is_pro = is_pro or is_owner_user
    if not is_pro:
        await update.message.reply_text(support_ui.get_canned_pro_reply_msg(), parse_mode="HTML")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(support_ui.get_reply_usage(), parse_mode="HTML")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ticket ID.")
        return

    tag = context.args[1].strip()
    canned = await CannedRepo.get_canned(tag)
    if not canned:
        await update.message.reply_text(support_ui.get_reply_tag_not_found(tag))
        return

    await CannedRepo.increment_usage(tag)
    success = await TicketRepo.set_admin_response(ticket_id, canned.content)
    if success:
        ticket = await TicketRepo.get_ticket(ticket_id)
        if ticket:
            await notify_user_on_admin_reply(
                user_id=ticket.user_id,
                ticket_id=ticket_id,
                subject=ticket.subject,
                admin_response=canned.content,
            )
        await update.message.reply_text(support_ui.get_reply_success(ticket_id, canned.content), parse_mode="HTML")
    else:
        await update.message.reply_text(support_ui.get_reply_not_found())


async def cmd_addfaq(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_admin: bool = False):
    is_admin = is_admin or is_owner(update.effective_user.id)
    if not is_admin:
        await update.message.reply_text(support_ui.get_addfaq_admin_only())
        return

    if not context.args:
        await update.message.reply_text(support_ui.get_addfaq_help(), parse_mode="HTML")
        return

    args = " ".join(context.args).split(" | ")
    if len(args) < 2:
        await update.message.reply_text(support_ui.get_addfaq_pipe_error(), parse_mode="HTML")
        return

    question = args[0].strip()
    answer = args[1].strip()
    category = args[2].strip().lower() if len(args) > 2 else "general"

    count = await FAQRepo.count_faqs()
    if count >= 100:
        await update.message.reply_text(support_ui.get_addfaq_limit())
        return

    faq = await FAQRepo.add_faq(question, answer, category, update.effective_user.id)
    await update.message.reply_text(support_ui.get_addfaq_success(faq.id, question, category), parse_mode="HTML")


async def cmd_delfaq(update: Update, context: ContextTypes.DEFAULT_TYPE, is_admin: bool = False):
    is_admin = is_admin or is_owner(update.effective_user.id)
    if not is_admin:
        await update.message.reply_text(support_ui.get_addfaq_admin_only())
        return

    if not context.args:
        await update.message.reply_text(support_ui.get_delfaq_usage(), parse_mode="HTML")
        return

    try:
        faq_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(support_ui.get_delfaq_invalid())
        return

    success = await FAQRepo.delete_faq(faq_id)
    if success:
        await update.message.reply_text(support_ui.get_delfaq_success(faq_id))
    else:
        await update.message.reply_text(support_ui.get_delfaq_not_found())


async def cmd_rate(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_owner_user: bool = False):
    is_pro = is_pro or is_owner_user
    if not is_pro:
        await update.message.reply_text(support_ui.get_rate_pro_feature_msg(), parse_mode="HTML")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(support_ui.get_rate_usage(), parse_mode="HTML")
        return

    try:
        ticket_id = int(context.args[0])
        rating = int(context.args[1])
    except ValueError:
        await update.message.reply_text(support_ui.get_rate_invalid())
        return

    if rating < 1 or rating > 5:
        await update.message.reply_text(support_ui.get_rate_out_of_range())
        return

    ticket = await TicketRepo.get_ticket(ticket_id)
    if not ticket:
        await update.message.reply_text(support_ui.get_rate_not_found())
        return

    if ticket.user_id != update.effective_user.id:
        await update.message.reply_text(support_ui.get_rate_not_owner())
        return

    if ticket.status not in ["resolved", "closed"]:
        await update.message.reply_text(support_ui.get_rate_not_resolved())
        return

    success = await TicketRepo.set_rating(ticket_id, rating)
    if success:
        await update.message.reply_text(support_ui.get_rate_success(rating), parse_mode="HTML")
    else:
        await update.message.reply_text(support_ui.get_rate_failure())


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, is_pro: bool, is_owner_user: bool = False):
    is_pro = is_pro or is_owner_user
    if not is_pro:
        await update.message.reply_text(support_ui.get_stats_pro_feature_msg(), parse_mode="HTML")
        return

    stats = await TicketRepo.get_ticket_stats()
    await update.message.reply_text(support_ui.get_stats_msg(stats), parse_mode="HTML")


async def cmd_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE, is_admin: bool = False):
    is_admin = is_admin or is_owner(update.effective_user.id)
    if not is_admin:
        await update.message.reply_text(support_ui.get_admin_only_msg())
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(support_ui.get_resolve_usage(), parse_mode="HTML")
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
        await update.message.reply_text(support_ui.get_resolve_success(ticket_id), parse_mode="HTML")
    else:
        await update.message.reply_text(support_ui.get_resolve_not_found())
