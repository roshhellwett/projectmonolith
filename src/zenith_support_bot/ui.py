from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.formatters import (
    format_alert,
    format_card,
    format_divider,
    format_header,
    format_kv,
    format_progress_bar,
)

# ── Keyboards ──────────────────────────────────────────────


def get_back_button(label: str = "Back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="sup_main_menu")]])


def get_support_dashboard(is_pro: bool, open_tickets: int = 0, is_owner: bool = False) -> InlineKeyboardMarkup:
    ticket_limit = 999 if is_owner else 15 if is_pro else 3
    tier_label = "👑 OWNER ACCESS" if is_owner else "💎 PRO VIP SUPPORT" if is_pro else "⚪ STANDARD FREE TIER"

    keyboard = [
        [InlineKeyboardButton(tier_label, callback_data="sup_status")],
        [
            InlineKeyboardButton("📂 My Tickets", callback_data="sup_my_tickets"),
            InlineKeyboardButton("❓ Knowledge Base", callback_data="sup_faq"),
        ],
    ]
    if is_owner or is_pro:
        keyboard.append([InlineKeyboardButton("➕ Open New Ticket", callback_data="sup_new_ticket")])
        keyboard.append(
            [
                InlineKeyboardButton("📊 Support Telemetry", callback_data="sup_stats"),
                InlineKeyboardButton("📋 Canned Templates", callback_data="sup_canned"),
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"➕ Open New Ticket ({open_tickets}/{ticket_limit})", callback_data="sup_new_ticket"
                )
            ]
        )
    if is_owner:
        keyboard.append(
            [
                InlineKeyboardButton("👑 Admin: All Tickets", callback_data="sup_all_tickets"),
                InlineKeyboardButton("👑 Admin: Add FAQ", callback_data="sup_add_faq_admin"),
            ]
        )
    return InlineKeyboardMarkup(keyboard)


def get_ticket_keyboard(tickets: list) -> InlineKeyboardMarkup:
    keyboard = []
    for ticket in tickets[:10]:
        status_text = ticket.status.replace("_", " ").upper()
        label = f"#{ticket.id} {status_text} \u2014 {ticket.subject[:25]}..."
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sup_ticket_{ticket.id}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_all_tickets_keyboard(tickets: list) -> InlineKeyboardMarkup:
    keyboard = []
    for ticket in tickets[:20]:
        user_label = f"@{ticket.username}" if ticket.username else f"ID:{ticket.user_id}"
        status_text = ticket.status.replace("_", " ").upper()
        label = f"#{ticket.id} {status_text} {ticket.subject[:20]}... ({user_label})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sup_ticket_{ticket.id}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_ticket_detail_keyboard(
    ticket_id: int, is_owner: bool = False, is_pro: bool = False, is_admin: bool = False, is_ticket_owner: bool = False
) -> InlineKeyboardMarkup:
    keyboard = []
    if is_ticket_owner or is_owner:
        keyboard.append([InlineKeyboardButton("Close Ticket", callback_data=f"sup_close_confirm_{ticket_id}")])
    if is_pro or is_owner:
        keyboard.append([InlineKeyboardButton("Set Priority", callback_data=f"sup_priority_{ticket_id}")])
    if is_admin or is_owner:
        keyboard.append([InlineKeyboardButton("Resolve", callback_data=f"sup_resolve_{ticket_id}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="sup_my_tickets")])
    return InlineKeyboardMarkup(keyboard)


def get_faq_keyboard(faqs: list) -> InlineKeyboardMarkup:
    keyboard = []
    for faq in faqs[:15]:
        keyboard.append([InlineKeyboardButton(f"{faq.question[:40]}...", callback_data=f"sup_faq_{faq.id}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_priority_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Low", callback_data=f"sup_prio_{ticket_id}_low")],
            [InlineKeyboardButton("Normal", callback_data=f"sup_prio_{ticket_id}_normal")],
            [InlineKeyboardButton("High", callback_data=f"sup_prio_{ticket_id}_high")],
            [InlineKeyboardButton("Urgent", callback_data=f"sup_prio_{ticket_id}_urgent")],
        ]
    )


def get_canned_keyboard(canned_list: list) -> InlineKeyboardMarkup:
    keyboard = []
    for canned in canned_list:
        keyboard.append([InlineKeyboardButton(canned.tag, callback_data=f"sup_canned_{canned.tag}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_rating_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    keyboard = []
    for i in range(1, 6):
        keyboard.append([InlineKeyboardButton(f"{i}/5", callback_data=f"sup_rate_{ticket_id}_{i}")])
    keyboard.append([InlineKeyboardButton("Skip", callback_data=f"sup_ticket_{ticket_id}")])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_close_ticket(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, Close Ticket", callback_data=f"sup_close_{ticket_id}")],
            [InlineKeyboardButton("Cancel", callback_data=f"sup_ticket_{ticket_id}")],
        ]
    )


# ── Message Builders ───────────────────────────────────────


def get_confirm_close_ticket_msg(ticket_id: int) -> str:
    return (
        f"Close Ticket #{ticket_id}?\n\n"
        "Are you sure you want to close this ticket?\n"
        "You can always create a new ticket if needed."
    )


def get_welcome_msg(
    first_name: str, is_pro: bool, days_left: int = 0, ticket_count: int = 0, is_owner: bool = False
) -> str:
    if is_owner:
        tier_info = "👑 Owner (Full System Access)"
        ticket_limit = 999
        badge = "OWNER VIP"
    elif is_pro:
        tier_info = f"💎 Pro Support Suite ({days_left}d remaining)"
        ticket_limit = 15
        badge = "PRO VIP"
    else:
        tier_info = "⚪ Standard Tier"
        ticket_limit = 3
        badge = "FREE TIER"

    stats = [
        f"Client Account: <b>{first_name}</b>",
        f"Service Level: <b>{tier_info}</b>",
        f"Open Tickets: {format_progress_bar(ticket_count, ticket_limit)} <code>({ticket_count}/{ticket_limit})</code>",
    ]
    commands = [
        "<code>/ticket [subject] | [description]</code> — Submit a new support request",
        "<code>/my_tickets</code> — Review your active & resolved inquiries",
        "<code>/faq</code> — Consult our instant knowledge base answers",
    ]
    text = (
        f"{format_header('Zenith VIP Support', 'Automated Concierge & Ticketing Portal', badge)}\n"
        f"{format_card('Account Summary', stats, '👤')}\n\n"
        f"{format_card('Quick Actions', commands, '🛠️')}"
    )
    if not (is_pro or is_owner):
        text += "\n\n<i>⚡ Tip: Upgrade to Pro for 15 concurrent tickets, instant AI troubleshooting, and priority routing.</i>"
    return text


def get_pro_status_msg(is_pro: bool, days_left: int, is_owner: bool) -> str:
    if is_owner:
        features = [
            "<b>Unlimited Support Tickets</b> & instantaneous triage routing",
            "<b>Full Administrative Portal</b> access across all client cases",
            "<b>Canned Response Management</b> & dynamic template creation",
            "<b>Global Support Analytics</b> & agent performance telemetry",
        ]
        return (
            f"{format_header('Subscription Status', 'Zenith Owner VIP Portal', 'OWNER')}\n"
            f"{format_kv('System Role', 'System Administrator & Owner', '👑')}\n\n"
            f"{format_card('Owner Privileges', features, '✨')}"
        )
    elif is_pro:
        features = [
            "<b>15 Concurrent Open Tickets</b> (vs 3 standard tier)",
            "<b>Instant AI Troubleshooting Concierge</b> auto-responses",
            "<b>Priority Agent Escalation</b> & expedited queue placement",
            "<b>Full Access to Canned Responses</b> & custom FAQ builder",
            "<b>Personalized Ticket Telemetry</b> & resolution statistics",
        ]
        return (
            f"{format_header('Subscription Status', 'Zenith Pro Support Suite', 'PRO ACTIVE')}\n"
            f"{format_kv('Days Remaining', f'{days_left} days', '🗓️')}\n"
            f"{format_kv('Service Level', 'Priority VIP SLA', '⚡')}\n\n"
            f"{format_card('Pro Suite Benefits', features, '✨')}"
        )
    else:
        features = [
            "3 maximum open tickets limit",
            "Standard queue placement & response time",
            "Basic knowledge base access",
        ]
        return (
            f"{format_header('Subscription Status', 'Standard Free Support Tier', 'FREE')}\n"
            f"{format_card('Current Tier Limitations', features, '🔒')}\n\n"
            f"⚡ <i>Upgrade to Pro VIP Support for instant AI resolution and priority triage. Use <code>/activate YOUR-KEY</code> to unlock.</i>"
        )


def get_ticket_created_msg(ticket_id: int, ai_response: str = None) -> str:
    items = [
        f"Ticket Reference: <code>#{ticket_id}</code>",
        "Queue Placement: <b>Dispatched to Triage Agents</b>",
        f"Tracking Command: <code>/status {ticket_id}</code>",
    ]
    msg = (
        f"{format_header('Ticket Dispatched', 'Your Support Inquiry Has Been Registered', 'OPEN')}\n"
        f"{format_card('Inquiry Summary', items, '📋')}"
    )
    if ai_response:
        msg += f"\n\n{format_alert(ai_response[:500], '🤖 AI Instant Troubleshooting Suggestion', 'INFO')}"
    return msg


def get_ticket_status_msg(ticket, is_pro: bool = False, is_owner: bool = False) -> str:
    status_text = ticket.status.replace("_", " ").upper()
    priority_text = ticket.priority.upper()

    msg = (
        f"<b>Ticket #{ticket.id}</b>\n"
        ""
        f"Subject: {ticket.subject}\n"
        f"Status: {status_text}\n"
        f"Priority: {priority_text}\n\n"
        f"Description:\n{ticket.description[:500]}"
    )
    if ticket.ai_response:
        msg += f"\n\nAI Response:\n{ticket.ai_response[:500]}"
    if ticket.admin_response:
        msg += f"\n\nAdmin Response:\n{ticket.admin_response[:500]}"
    if ticket.rating:
        msg += f"\n\nRating: {ticket.rating}/5"
    msg += f"\n\nCreated: {ticket.created_at.strftime('%d %b %Y %H:%M UTC')}"
    return msg


def get_limit_reached_msg(feature: str, current: int, limit: int, is_pro: bool = False) -> str:
    if is_pro:
        return f"Limit Reached: {feature}\n\nYou've used {current}/{limit}.\n\nPlease close or resolve existing tickets to open a new one."
    return (
        f"Limit Reached: {feature}\n\nYou've used {current}/{limit}.\n\nClose some tickets or upgrade to PRO for more."
    )


def get_no_tickets_msg() -> str:
    return "<b>No Tickets</b>\n\nYou don't have any open tickets.\n\nCreate a new ticket with:\n/ticket [subject] | [description]"


def get_my_tickets_empty() -> str:
    return "<b>Your Tickets</b>\n\nYou haven't created any tickets yet.\n\nUse /ticket [subject] | [description] to create one."


def get_subs_only_msg() -> str:
    return "Subscribers Only\n\nYou need an active subscription to create support tickets.\n\nUse /activate [KEY] to activate your subscription."


def get_ticket_limit_msg(open_tickets: int, max_tickets: int, upgrade_msg: str = "") -> str:
    return (
        f"Ticket Limit Reached\n\n"
        f"You have {open_tickets} open ticket(s). Maximum allowed: {max_tickets}\n\n"
        f"{upgrade_msg}"
    )


def get_ticket_help() -> str:
    return (
        "<b>Create Support Ticket</b>\n\n"
        "Format: /ticket [subject] | [description]\n\n"
        "Example: /ticket Login Issue | I can't log into my account"
    )


def get_ticket_pipe_error() -> str:
    return "Use | to separate subject and description.\n\nExample: /ticket Login Issue | I can't log into my account"


def get_status_usage() -> str:
    return "Usage: /status [TICKET_ID]\n\nExample: /status 5"


def get_status_invalid() -> str:
    return "Invalid ticket ID."


def get_status_not_found() -> str:
    return "Ticket not found."


def get_close_usage() -> str:
    return "Usage: /close [TICKET_ID]\n\nExample: /close 5"


def get_close_invalid() -> str:
    return "Invalid ticket ID."


def get_close_success(ticket_id: int) -> str:
    return f"<b>Ticket Closed</b>\n\nTicket #{ticket_id} has been closed."


def get_close_failure() -> str:
    return "Could not close ticket. It may already be closed or you don't own this ticket."


def get_activate_help() -> str:
    return "Invalid Format. Use: /activate [YOUR_KEY]"


def get_faq_empty() -> str:
    return "<b>FAQ</b>\n\nNo FAQ entries available."


def get_faq_loaded() -> str:
    return "<b>Frequently Asked Questions</b>"


def get_faq_detail(question: str, answer: str, category: str) -> str:
    return f"<b>{question}</b>\n" f"{format_divider()}\n\n" f"{answer}\n\n" f"Category: {category}"


def get_priority_help() -> str:
    return (
        "<b>Set Ticket Priority</b>\n\n"
        "Format: /priority [TICKET_ID] [low|normal|high|urgent]\n\n"
        "Examples:\n"
        "\u2022 /priority 5 high\n"
        "\u2022 /priority 12 urgent"
    )


def get_priority_invalid_id() -> str:
    return "Invalid Ticket ID.\n\nTicket ID must be a number."


def get_priority_invalid_value(err: str) -> str:
    return f"Invalid Priority\n\n{err}\n\nValid options: low, normal, high, urgent"


def get_priority_success(ticket_id: int, priority: str) -> str:
    return f"<b>Priority Updated</b>\n\nTicket #{ticket_id} priority set to {priority.upper()}"


def get_priority_not_found() -> str:
    return "Ticket Not Found\n\nThe ticket may not exist or is already closed.\n\nUse /tickets to see your tickets."


def get_savereply_help() -> str:
    return (
        "<b>Save Canned Response</b>\n\n"
        "Format: /savereply [tag] | [content]\n\n"
        "Example: /savereply greeting | Hello! Thank you for contacting support."
    )


def get_savereply_pipe_error() -> str:
    return "Invalid Format\n\nUse | to separate tag and content."


def get_savereply_tag_long() -> str:
    return "Tag must be under 50 characters."


def get_savereply_short() -> str:
    return "Content must be at least 5 characters."


def get_savereply_success(tag: str, content: str) -> str:
    return f"<b>Canned Response Saved</b>\n\nTag: <code>{tag}</code>\n\nContent:\n{content[:200]}..."


def get_replies_help() -> str:
    return "<b>Canned Responses</b>\n\nNo saved responses yet.\nUse /savereply [tag] | [content] to create one."


def get_replies_loaded() -> str:
    return "<b>Saved Responses</b>"


def get_reply_usage() -> str:
    return "Usage: /reply [TICKET_ID] [tag]\n\nExample: /reply 5 greeting"


def get_reply_tag_not_found(tag: str) -> str:
    return f"Canned response '{tag}' not found. Use /replies to see available responses."


def get_reply_success(ticket_id: int, content: str) -> str:
    return f"<b>Response Applied</b>\n\nTicket #{ticket_id} replied with: {content[:200]}...\n\nUser has been notified."


def get_reply_not_found() -> str:
    return "Ticket not found."


def get_addfaq_admin_only() -> str:
    return "Admin only."


def get_addfaq_help() -> str:
    return (
        "Usage: /addfaq [question] | [answer]\n\n"
        "Example: /addfaq How do I reset password? | Click on settings and...\n\n"
        "Categories: general, billing, tickets, technical"
    )


def get_addfaq_pipe_error() -> str:
    return "Use | to separate question and answer.\nExample: /addfaq Question | Answer"


def get_addfaq_limit() -> str:
    return "Maximum 100 FAQ entries allowed."


def get_addfaq_success(faq_id: int, question: str, category: str) -> str:
    return f"<b>FAQ Added</b>\n\nID: <code>{faq_id}</code>\nQ: {question[:50]}...\nCategory: {category}"


def get_delfaq_usage() -> str:
    return "Usage: /delfaq [ID]"


def get_delfaq_invalid() -> str:
    return "Invalid FAQ ID."


def get_delfaq_success(faq_id: int) -> str:
    return f"FAQ #{faq_id} deleted."


def get_delfaq_not_found() -> str:
    return "FAQ not found."


def get_pro_feature_msg(feature: str) -> tuple:
    msg = (
        f"<b>Pro Feature: {feature}</b>\n\n"
        f"This feature is available exclusively for PRO members.\n\n"
        f"Pro Benefits:\n"
        f"\u2022 15 open tickets (vs 3 free)\n"
        f"\u2022 AI auto-response\n"
        f"\u2022 Priority support\n"
        f"\u2022 Custom FAQ builder\n"
        f"\u2022 Canned responses\n"
        f"\u2022 Analytics"
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Activate Key", callback_data="sup_activate_help")],
            [InlineKeyboardButton("Back", callback_data="sup_main_menu")],
        ]
    )
    return msg, kb


def get_new_ticket_guide() -> str:
    return (
        "<b>Create New Ticket</b>\n\n"
        "Use command: /ticket [subject] | [description]\n\n"
        "Example: /ticket Login Issue | I can't log into my account"
    )


def get_ticket_priority_msg(priority: str) -> str:
    info = {
        "low": ("Low", "Will be addressed when possible"),
        "normal": ("Normal", "Standard response time"),
        "high": ("High", "Will be addressed soon"),
        "urgent": ("Urgent", "Immediate attention required"),
    }
    emoji, desc = info.get(priority, ("Normal", "Standard response time"))
    return f"{emoji} Priority\n\n{desc}"


def get_stats_pro_feature_msg() -> str:
    return "Pro Feature: Analytics\n\nUpgrade to Pro to view ticket statistics."


def get_stats_msg(stats: dict) -> str:
    return (
        f"<b>Support Analytics</b>\n"
        ""
        f"Total Tickets: {stats['total']}\n"
        f"Open: {stats['open']}\n"
        f"In Progress: {stats['in_progress']}\n"
        f"Resolved: {stats['resolved']}\n"
        f"Closed: {stats['closed']}\n\n"
        f"Avg. Rating: {stats['avg_rating']} / 5"
    )


def get_rate_usage() -> str:
    return "Usage: /rate [TICKET_ID] [1-5]\n\nExample: /rate 5 5"


def get_rate_invalid() -> str:
    return "Invalid ticket ID or rating."


def get_rate_out_of_range() -> str:
    return "Rating must be between 1 and 5."


def get_rate_not_found() -> str:
    return "Ticket not found."


def get_rate_not_owner() -> str:
    return "You can only rate your own tickets."


def get_rate_not_resolved() -> str:
    return "Can only rate resolved tickets."


def get_rate_success(rating: int) -> str:
    return f"<b>Rating Submitted</b>\n\nTicket rated: {rating}/5\n\nThank you for your feedback!"


def get_rate_failure() -> str:
    return "Failed to submit rating."


def get_resolve_usage() -> str:
    return "Usage: /resolve [TICKET_ID] [response]\n\nExample: /resolve 5 The issue has been fixed."


def get_resolve_success(ticket_id: int) -> str:
    return f"<b>Ticket Resolved</b>\n\nTicket #{ticket_id} has been resolved with your response.\n\nUser has been notified."


def get_resolve_not_found() -> str:
    return "Ticket not found."


def get_admin_only_msg() -> str:
    return "Admin only."


def get_ticket_status_help() -> str:
    return "<b>Ticket Status</b>\n\nFormat: /status [TICKET_ID]\n\nExample: /status 5"


def get_ticket_status_not_found() -> str:
    return "Ticket not found."


def get_ticket_status_not_owner() -> str:
    return "You can only view your own tickets."


def get_canned_feature_msg() -> str:
    return "Pro Feature: Canned Responses\n\nUpgrade to Pro to access saved reply templates."


def get_canned_help_msg() -> str:
    return "Use /savereply to add, /replies to view, /reply to use."


def get_canned_pro_reply_msg() -> str:
    return "Pro Feature: Canned Responses\n\nUpgrade to Pro to use canned responses."


def get_points_default_msg() -> str:
    return "Points: Default 10 per interaction."


def get_all_tickets_empty() -> str:
    return "No tickets yet."


def get_all_tickets_loaded() -> str:
    return "<b>All Tickets (Admin View)</b>"


def get_ticket_not_found_msg() -> str:
    return "Ticket not found."


def get_rate_pro_feature_msg() -> str:
    return "Pro Feature: Satisfaction Ratings\n\nUpgrade to Pro to rate resolved tickets."


def get_ticket_status_card(ticket) -> str:
    status_text = ticket.status.replace("_", " ").upper()
    created = ticket.created_at.strftime("%d %b %Y %H:%M") if ticket.created_at else "N/A"
    updated = ticket.updated_at.strftime("%d %b %Y %H:%M") if ticket.updated_at else "N/A"

    lines = [
        f"<b>Ticket #{ticket.id}</b>",
        f"{format_divider()}",
        f"Subject: {ticket.subject}",
        f"Status: {status_text}",
        f"Priority: {ticket.priority.upper()}",
        f"Created: {created}",
        f"Updated: {updated}",
    ]
    if ticket.description:
        lines.append(f"\nDescription:\n{ticket.description[:500]}")
    if ticket.admin_response:
        admin_time = ticket.last_admin_reply_at.strftime("%d %b %H:%M") if ticket.last_admin_reply_at else "N/A"
        lines.append(f"\nAdmin Response:\n{ticket.admin_response[:500]}")
        lines.append(f"Replied: {admin_time}")
    return "\n".join(lines)


def get_user_reply_prompt(ticket_id: int) -> tuple:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    text = f"<b>Reply to Ticket #{ticket_id}</b>\n\nPlease send your reply to this ticket.\n\nType your response below:"
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❌ Cancel Reply", callback_data=f"ticket_cancel_reply_{ticket_id}")],
            [InlineKeyboardButton("◀️ Back to Dashboard", callback_data="sup_main_menu")],
        ]
    )
    return text, kb


def get_user_close_denied() -> str:
    return "Ticket not found or access denied."


def get_user_close_already() -> str:
    return "This ticket is already closed."


def get_user_close_cannot() -> str:
    return "This ticket cannot be closed."


def get_user_close_success(ticket_id: int) -> str:
    return f"<b>Ticket #{ticket_id} Closed</b>\n\nThis ticket has been marked as resolved/closed.\n\nThank you for using our support!"


def get_user_close_failure() -> str:
    return "Failed to close ticket. Please try again."


def get_user_reply_success(ticket_id: int) -> str:
    return f"<b>Reply Sent</b>\n\nYour reply to Ticket #{ticket_id} has been submitted.\n\nOur team will review your response shortly."


def get_user_reply_failure() -> str:
    return "Failed to send reply. Please try again."


def get_ticket_status_keyboard(ticket):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = []
    if ticket.status in ["open", "in_progress", "resolved"]:
        keyboard.append([InlineKeyboardButton("Reply", callback_data=f"ticket_reply_{ticket.id}")])
    if ticket.status in ["open", "in_progress"]:
        keyboard.append([InlineKeyboardButton("Close", callback_data=f"ticket_close_user_{ticket.id}")])
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def get_user_what_next_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("View All Tickets", callback_data="sup_my_tickets")],
            [InlineKeyboardButton("◀️ Back to Dashboard", callback_data="sup_main_menu")],
        ]
    )


def get_user_what_next_msg() -> str:
    return "What would you like to do next?"
