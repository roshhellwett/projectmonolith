from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.formatters import format_progress_bar


def get_support_dashboard(is_pro: bool, open_tickets: int = 0, is_owner: bool = False) -> InlineKeyboardMarkup:
    ticket_limit = 999 if is_owner else 15 if is_pro else 3
    ticket_bar = format_progress_bar(open_tickets, ticket_limit)

    keyboard = [
        [
            InlineKeyboardButton(
                f"{'👑' if is_owner else '💎' if is_pro else '🆓'} {'OWNER' if is_owner else 'PRO ACTIVE' if is_pro else 'FREE TIER'}",
                callback_data="sup_status",
            )
        ],
        [InlineKeyboardButton(f"🎫 My Tickets {ticket_bar}", callback_data="sup_my_tickets")],
        [InlineKeyboardButton("❓ FAQ", callback_data="sup_faq")],
    ]

    if is_owner or is_pro:
        keyboard.extend(
            [
                [InlineKeyboardButton("➕ New Ticket", callback_data="sup_new_ticket")],
                [InlineKeyboardButton("📊 Analytics", callback_data="sup_stats")],
                [InlineKeyboardButton("💾 Canned Responses", callback_data="sup_canned")],
            ]
        )
    else:
        keyboard.append(
            [InlineKeyboardButton(f"➕ New Ticket ({open_tickets}/{ticket_limit})", callback_data="sup_new_ticket")]
        )

    if is_owner:
        keyboard.extend(
            [
                [InlineKeyboardButton("🎫 All Tickets (Admin)", callback_data="sup_all_tickets")],
                [InlineKeyboardButton("➕ Add FAQ (Admin)", callback_data="sup_add_faq_admin")],
            ]
        )

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="sup_main_menu")]])


def get_ticket_keyboard(tickets: list, user_id: int = None) -> InlineKeyboardMarkup:
    keyboard = []
    for ticket in tickets[:10]:
        status_emoji = {"open": "🟢", "in_progress": "🟡", "resolved": "✅", "closed": "🔴"}.get(ticket.status, "⚪")
        priority_emoji = {"low": "⬇️", "normal": "➡️", "high": "⬆️", "urgent": "🚨"}.get(ticket.priority, "➡️")
        label = f"{status_emoji} #{ticket.id} {priority_emoji} {ticket.subject[:25]}..."
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sup_ticket_{ticket.id}")])

    keyboard.append([InlineKeyboardButton("🔙 Dashboard", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_all_tickets_keyboard(tickets: list) -> InlineKeyboardMarkup:
    keyboard = []
    for ticket in tickets[:20]:
        status_emoji = {"open": "🟢", "in_progress": "🟡", "resolved": "✅", "closed": "🔴"}.get(ticket.status, "⚪")
        priority_emoji = {"low": "⬇️", "normal": "➡️", "high": "⬆️", "urgent": "🚨"}.get(ticket.priority, "➡️")
        user_label = f"@{ticket.username}" if ticket.username else f"ID:{ticket.user_id}"
        label = f"{status_emoji} #{ticket.id} {priority_emoji} {ticket.subject[:20]}... ({user_label})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"sup_ticket_{ticket.id}")])

    keyboard.append([InlineKeyboardButton("🔙 Dashboard", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_ticket_detail_keyboard(
    ticket_id: int, is_owner: bool = True, is_pro: bool = False, is_admin: bool = False, is_ticket_owner: bool = True
) -> InlineKeyboardMarkup:
    keyboard = []

    if is_ticket_owner or is_owner:
        keyboard.append([InlineKeyboardButton("❌ Close Ticket", callback_data=f"sup_close_confirm_{ticket_id}")])

    if is_pro or is_owner:
        keyboard.append([InlineKeyboardButton("🏷️ Set Priority", callback_data=f"sup_priority_{ticket_id}")])

    if is_admin or is_owner:
        keyboard.append([InlineKeyboardButton("✅ Resolve", callback_data=f"sup_resolve_{ticket_id}")])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="sup_my_tickets")])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_close_ticket(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Yes, Close Ticket", callback_data=f"sup_close_{ticket_id}")],
            [InlineKeyboardButton("✖ Cancel", callback_data=f"sup_ticket_{ticket_id}")],
        ]
    )


def get_confirm_close_ticket_msg(ticket_id: int) -> str:
    return (
        f"⚠️ <b>Close Ticket #{ticket_id}?</b>\n\n"
        "Are you sure you want to close this ticket?\n"
        "You can always create a new ticket if needed."
    )


def get_faq_keyboard(faqs: list) -> InlineKeyboardMarkup:
    keyboard = []
    for faq in faqs[:15]:
        keyboard.append([InlineKeyboardButton(f"❓ {faq.question[:40]}...", callback_data=f"sup_faq_{faq.id}")])

    keyboard.append([InlineKeyboardButton("🔙 Dashboard", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_priority_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("⬇️ Low", callback_data=f"sup_prio_{ticket_id}_low")],
        [InlineKeyboardButton("➡️ Normal", callback_data=f"sup_prio_{ticket_id}_normal")],
        [InlineKeyboardButton("⬆️ High", callback_data=f"sup_prio_{ticket_id}_high")],
        [InlineKeyboardButton("🚨 Urgent", callback_data=f"sup_prio_{ticket_id}_urgent")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_canned_keyboard(canned_list: list) -> InlineKeyboardMarkup:
    keyboard = []
    for canned in canned_list:
        keyboard.append([InlineKeyboardButton(f"🏷️ {canned.tag}", callback_data=f"sup_canned_{canned.tag}")])

    keyboard.append([InlineKeyboardButton("🔙 Dashboard", callback_data="sup_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_rating_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """Star rating keyboard for ticket feedback."""
    stars = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    keyboard = []

    for i, star in enumerate(stars, 1):
        keyboard.append([InlineKeyboardButton(star, callback_data=f"sup_rate_{ticket_id}_{i}")])

    keyboard.append([InlineKeyboardButton("Skip", callback_data=f"sup_ticket_{ticket_id}")])

    return InlineKeyboardMarkup(keyboard)


def get_ticket_created_msg(ticket_id: int, ai_response: str = None) -> str:
    msg = f"""🎫 <b>Ticket Created Successfully!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Ticket ID:</b> <code>{ticket_id}</code>

Your ticket has been submitted to our support team."""

    if ai_response:
        msg += f"""

<b>🤖 AI Suggestion:</b>
{ai_response[:500]}..."""

    msg += """

<i>We'll respond as soon as possible. Use /status to check progress.</i>"""
    return msg


def get_ticket_status_msg(ticket, is_pro: bool = False, is_owner: bool = False) -> str:
    status_map = {
        "open": "🟢 Open - Awaiting response",
        "in_progress": "🟡 In Progress - Being looked at",
        "resolved": "✅ Resolved - Awaiting your feedback",
        "closed": "🔴 Closed - Ticket archived",
    }
    priority_map = {
        "low": "⬇️ Low",
        "normal": "➡️ Normal",
        "high": "⬆️ High",
        "urgent": "🚨 Urgent",
    }

    status = status_map.get(ticket.status, ticket.status)
    priority = priority_map.get(ticket.priority, "➡️ Normal")

    msg = f"""🎫 <b>Ticket #{ticket.id}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Subject:</b> {ticket.subject}
<b>Status:</b> {status}
<b>Priority:</b> {priority}

<b>Description:</b>
{ticket.description[:500]}"""

    if ticket.ai_response:
        msg += f"""

<b>🤖 AI Response:</b>
{ticket.ai_response[:500]}"""

    if ticket.admin_response:
        msg += f"""

<b>📝 Admin Response:</b>
{ticket.admin_response}"""

    if ticket.rating:
        stars = "⭐" * ticket.rating
        msg += f"""

<b>Your Rating:</b> {stars}"""

    msg += f"""

<i>Created: {ticket.created_at.strftime('%d %b %Y %H:%M UTC')}</i>"""

    return msg


def get_ticket_timeline(ticket) -> str:
    """Format ticket timeline visualization."""
    steps = [
        ("created", "Created", "🆕"),
        ("in_progress", "In Progress", "⏳"),
        ("resolved", "Resolved", "✅"),
        ("closed", "Closed", "🔴"),
    ]

    current_index = 0
    status_order = ["open", "in_progress", "resolved", "closed"]
    if ticket.status in status_order:
        current_index = status_order.index(ticket.status)

    timeline = "<b>📅 Timeline</b>\n\n"

    for i, (_key, label, _emoji) in enumerate(steps):
        if i < current_index:
            timeline += f"✅ {label}\n"
        elif i == current_index:
            timeline += f"🔄 {label} (current)\n"
        else:
            timeline += f"⚪ {label}\n"

    return timeline


def get_welcome_msg(
    first_name: str, is_pro: bool, days_left: int = 0, ticket_count: int = 0, is_owner: bool = False
) -> str:
    if is_owner:
        tier_info = "👑 <b>OWNER</b> (Full Access)"
    elif is_pro:
        tier_info = f"💎 <b>Pro</b> ({days_left} days left)"
    else:
        tier_info = "🆓 <b>Free Tier</b>"

    if is_owner:
        ticket_limit = 999
        ticket_bar = format_progress_bar(ticket_count, ticket_limit)
    else:
        ticket_limit = 15 if is_pro else 3
        ticket_bar = format_progress_bar(ticket_count, ticket_limit)

    free_features = "• 3 open tickets\n• FAQ access\n• Status check"
    pro_features = "• 15 open tickets\n• AI auto-response\n• Priority support\n• Custom FAQ builder\n• Canned responses\n• Analytics\n• Auto-close tickets\n• Satisfaction ratings"
    owner_features = (
        "• Unlimited tickets\n• All Pro features\n• Admin panel\n• View all tickets\n• Manage FAQs\n• Resolve tickets"
    )

    msg = f"""👋 <b>Welcome to Zenith Support, {first_name}!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Your Tier:</b> {tier_info}

<b>📊 Ticket Usage:</b>
{ticket_bar}

<b>Free Features:</b>
{free_features}

<b>Pro Features:</b>
{pro_features}"""

    if is_owner:
        msg += f"""

<b>👑 Owner Features:</b>
{owner_features}"""

    msg += """

━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 Need help? Create a ticket and we'll assist you!

<i>Use /ticket [subject] | [description] to create a ticket</i>"""
    return msg


def get_limit_reached_msg(feature: str, current: int, limit: int) -> str:
    return (
        f"🚫 <b>Limit Reached: {feature}</b>\n\n"
        f"You've used {current}/{limit}.\n\n"
        "Close some tickets or upgrade to PRO for more."
    )


def get_no_tickets_msg() -> str:
    return (
        "🎫 <b>No Tickets</b>\n\n"
        "You don't have any open tickets.\n\n"
        "Create a new ticket with:\n"
        "/ticket [subject] | [description]"
    )


def get_faq_answer_msg(question: str, answer: str) -> str:
    return f"❓ <b>{question}</b>\n\n" f"{answer}\n\n" "<i>Need more help? Create a ticket!</i>"


def get_rating_thanks_msg(rating: int) -> str:
    stars = "⭐" * rating
    return (
        f"<b>Thank you for your feedback!</b>\n\n"
        f"You rated: {stars}\n\n"
        "We appreciate your input and will use it to improve our support."
    )


def get_pro_feature_msg(feature: str) -> tuple:
    messages = {
        "analytics": (
            "📊 <b>Analytics (Pro)</b>\n\n"
            "View support analytics including response times and satisfaction rates.\n\n"
            "💎 <b>Pro Benefits (₹149/month):</b>\n"
            "• Priority support\n"
            "• Unlimited tickets\n"
            "• Ticket analytics"
        ),
        "canned": (
            "💾 <b>Canned Responses (Pro)</b>\n\n"
            "Create and manage pre-written responses for common questions.\n\n"
            "💎 <b>Pro Benefits (₹149/month):</b>\n"
            "• Priority support\n"
            "• Unlimited tickets\n"
            "• Canned responses"
        ),
        "priority": (
            "🏷️ <b>Priority Support (Pro)</b>\n\n"
            "Set priority levels on your tickets for faster response.\n\n"
            "💎 <b>Pro Benefits (₹149/month):</b>\n"
            "• Priority support\n"
            "• Unlimited tickets\n"
            "• Priority queue"
        ),
    }

    message = messages.get(feature, "Pro feature")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Buy Pro", url="tg://user?id=YOUR_ADMIN_ID")],
            [InlineKeyboardButton("🔙 Back", callback_data="sup_main_menu")],
        ]
    )

    return message, keyboard


def get_new_ticket_guide() -> str:
    return (
        "🎫 <b>Create New Ticket</b>\n\n"
        "<b>Format:</b>\n"
        "/ticket [subject] | [description]\n\n"
        "<b>Example:</b>\n"
        "/ticket Login Issue | I can't log into my account\n\n"
        "<b>Tips:</b>\n"
        "• Be specific about your issue\n"
        "• Include relevant details\n"
        "• Attach screenshots if helpful"
    )


def get_ticket_priority_msg(priority: str) -> str:
    priority_info = {
        "low": ("⬇️ Low", "Will be addressed when possible"),
        "normal": ("➡️ Normal", "Standard response time"),
        "high": ("⬆️ High", "Will be addressed soon"),
        "urgent": ("🚨 Urgent", "Immediate attention required"),
    }

    emoji, desc = priority_info.get(priority, ("➡️ Normal", "Standard response time"))
    return f"{emoji} <b>{priority.capitalize()} Priority</b>\n\n{desc}"
