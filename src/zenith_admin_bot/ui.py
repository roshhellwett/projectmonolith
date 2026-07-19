from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.formatters import format_divider

# ── Keyboards ──────────────────────────────────────────────

def get_admin_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("System Overview", callback_data="admin_overview")],
        [InlineKeyboardButton("Ticket Management", callback_data="admin_tickets")],
        [InlineKeyboardButton("Key Management", callback_data="admin_keys")],
        [InlineKeyboardButton("Bulk KeyGen", callback_data="admin_bulk_keys")],
        [InlineKeyboardButton("User Management", callback_data="admin_users")],
        [InlineKeyboardButton("Group Management", callback_data="admin_groups")],
        [InlineKeyboardButton("Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("Bot Health", callback_data="admin_health")],
        [InlineKeyboardButton("Revenue Analytics", callback_data="admin_revenue")],
        [InlineKeyboardButton("System Stats", callback_data="admin_db_stats")],
        [InlineKeyboardButton("Audit Log", callback_data="admin_audit")],
        [InlineKeyboardButton("Security Panel", callback_data="admin_security")],
        [InlineKeyboardButton("Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin_main")]])


def get_tickets_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("All Tickets", callback_data="admin_tickets_all")],
        [InlineKeyboardButton("Open", callback_data="admin_tickets_open")],
        [InlineKeyboardButton("In Progress", callback_data="admin_tickets_progress")],
        [InlineKeyboardButton("Resolved", callback_data="admin_tickets_resolved")],
        [InlineKeyboardButton("Stale Tickets", callback_data="admin_tickets_stale")],
        [InlineKeyboardButton("Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_system_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Database Stats", callback_data="admin_db_stats")],
        [InlineKeyboardButton("Key History", callback_data="admin_key_history")],
        [InlineKeyboardButton("FAQ & Canned", callback_data="admin_faq_menu")],
        [InlineKeyboardButton("Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_bulk_keygen_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("5 Keys (30d)", callback_data="admin_bulk_5_30")],
        [InlineKeyboardButton("10 Keys (30d)", callback_data="admin_bulk_10_30")],
        [InlineKeyboardButton("5 Keys (90d)", callback_data="admin_bulk_5_90")],
        [InlineKeyboardButton("10 Keys (90d)", callback_data="admin_bulk_10_90")],
        [InlineKeyboardButton("Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_faq_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("List FAQs", callback_data="admin_faq_list")],
        [InlineKeyboardButton("Add FAQ", callback_data="admin_faq_add")],
        [InlineKeyboardButton("Delete FAQ", callback_data="admin_faq_delete")],
        [InlineKeyboardButton("Canned Responses", callback_data="admin_canned_list")],
        [InlineKeyboardButton("Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ── Messages / Formatting ──────────────────────────────────

def get_admin_dashboard() -> str:
    return (
        "<b>Zenith Admin Panel</b>\n"
        f"{format_divider()}\n\n"
        "Welcome to the central admin dashboard.\n"
        "Select an option below to manage your bots."
    )


def format_system_overview(stats: dict, ticket_stats: dict) -> str:
    return (
        f"<b>System Overview</b>\n{format_divider()}\n\n"
        f"Total Users: {stats.get('total_users', 0):,}\n"
        f"Pro Users: {stats.get('pro_users', 0):,}\n"
        f"Free Users: {stats.get('free_users', 0):,}\n\n"
        f"Active Subscriptions: {stats.get('active_subscriptions', 0):,}\n"
        f"Expiring (7 days): {stats.get('expiring_within_7_days', 0):,}\n\n"
        f"<b>Support Tickets</b>\n"
        f"Total: {ticket_stats.get('total', 0)}\n"
        f"Open: {ticket_stats.get('open', 0)}\n"
        f"In Progress: {ticket_stats.get('in_progress', 0)}\n"
        f"Resolved: {ticket_stats.get('resolved', 0)}"
    )


def format_key_management(keys: list) -> str:
    if not keys:
        return f"<b>Key Management</b>\n{format_divider()}\n\nNo unused activation keys found."
    lines = [f"<b>Unused Activation Keys</b>\n{format_divider()}"]
    for key in keys:
        days = key.duration_days
        created = key.created_at.strftime("%d %b %Y") if key.created_at else "N/A"
        lines.append(f"\u2022 <code>{key.key_string}</code> ({days}d) \u2014 {created}")
    return "\n".join(lines)


def format_user_management(user_id: int, sub_details: dict) -> str:
    if not sub_details.get("has_subscription", False):
        return (
            f"<b>User: {user_id}</b>\n{format_divider()}\n\n"
            f"Subscription: None\n"
            f"Status: Free tier"
        )
    expires = sub_details.get("expires_at")
    expires_str = expires.strftime("%d %b %Y") if expires else "N/A"
    return (
        f"<b>User: {user_id}</b>\n{format_divider()}\n\n"
        f"Subscription: Active\n"
        f"Days Remaining: {sub_details.get('days_left', 0)}\n"
        f"Expires: {expires_str}"
    )


def format_bot_health(bots: list) -> str:
    if not bots:
        return f"<b>Bot Health</b>\n{format_divider()}\n\nNo bots registered."
    lines = [f"<b>Monitored Bots</b>\n{format_divider()}"]
    for bot in bots:
        status_icon = "Active" if bot.status == "active" else ("Error" if bot.status == "error" else "Unknown")
        health = bot.health_status or "unknown"
        last_check = bot.last_health_check.strftime("%d %b %H:%M") if bot.last_health_check else "Never"
        lines.append(
            f"<b>{bot.bot_name}</b>\n"
            f"   Status: {status_icon} | Health: {health}\n"
            f"   Last check: {last_check}"
        )
    return "\n".join(lines)


def format_audit_log(logs: list) -> str:
    if not logs:
        return f"<b>Audit Log</b>\n{format_divider()}\n\nNo recent admin actions."
    lines = [f"<b>Recent Admin Actions</b>\n{format_divider()}"]
    for log in logs[:15]:
        time_str = log.created_at.strftime("%d %b %H:%M") if log.created_at else "N/A"
        target = f"User: {log.target_user_id}" if log.target_user_id else ""
        details = f" \u2014 {log.details}" if log.details else ""
        lines.append(f"<b>{log.action.value.upper()}</b> {time_str}\n   {target}{details}")
    return "\n".join(lines)


def format_revenue_analytics(stats: dict) -> str:
    pro_users = stats.get("pro_users", 0)
    active_subs = stats.get("active_subscriptions", 0)
    avg_value_per_user = 149
    estimated_mrr = active_subs * avg_value_per_user
    return (
        f"<b>Revenue Analytics</b>\n{format_divider()}\n\n"
        f"Pro Users: {pro_users:,}\n"
        f"Active Subs: {active_subs:,}\n"
        f"At Risk (7d): {stats.get('expiring_within_7_days', 0):,}\n\n"
        f"<b>Estimated MRR</b>\n"
        f"Active Subs x \u20b9149: \u20b9{estimated_mrr:,.2f}\n\n"
        "Note: Based on \u20b9149/month base plan (India)"
    )


def format_subscription_list(subscriptions: list) -> str:
    if not subscriptions:
        return f"<b>Active Subscriptions</b>\n{format_divider()}\n\nNo active subscriptions."
    lines = [f"<b>Active Subscriptions</b>\n{format_divider()}"]
    for sub in subscriptions[:20]:
        expires = sub.expires_at.strftime("%d %b %Y") if sub.expires_at else "N/A"
        days_left = (sub.expires_at - datetime.now()).days if sub.expires_at else 0
        lines.append(f"\u2022 <code>{sub.user_id}</code> \u2014 {expires} ({days_left}d)")
    if len(subscriptions) > 20:
        lines.append(f"\n...and {len(subscriptions) - 20} more")
    return "\n".join(lines)


def format_group_list(groups: list) -> str:
    if not groups:
        return f"<b>Group Management</b>\n{format_divider()}\n\nNo active groups found."
    lines = [f"<b>Active Groups</b>\n{format_divider()}"]
    for g in groups[:20]:
        status = "Active" if g.is_active else "Inactive"
        features = []
        if g.ai_enabled:
            features.append("AI")
        if g.crypto_enabled:
            features.append("Crypto")
        features_str = ", ".join(features) if features else "None"
        lines.append(
            f"<b>{g.group_name or 'Unnamed'}</b>\n"
            f"   ID: <code>{g.chat_id}</code> | Owner: <code>{g.owner_id}</code>\n"
            f"   Status: {status} | Features: {features_str}"
        )
    if len(groups) > 20:
        lines.append(f"\n...and {len(groups) - 20} more groups")
    return "\n".join(lines)


def format_group_search(groups: list) -> str:
    if not groups:
        return f"<b>Group Search</b>\n{format_divider()}\n\nNo groups found."
    lines = [f"<b>Groups</b>\n{format_divider()}"]
    for g in groups:
        features = []
        if g.ai_enabled:
            features.append("AI")
        if g.crypto_enabled:
            features.append("Crypto")
        features_str = ", ".join(features) if features else "None"
        lines.append(
            f"<b>{g.group_name or 'Unnamed'}</b>\n"
            f"   ID: <code>{g.chat_id}</code> | Owner: <code>{g.owner_id}</code>\n"
            f"   Features: {features_str}"
        )
    return "\n".join(lines)


def format_banned_users(users: list) -> str:
    if not users:
        return f"<b>Banned Users</b>\n{format_divider()}\n\nNo banned users."
    lines = [f"<b>Banned Users</b>\n{format_divider()}"]
    for u in users[:20]:
        reason = u.get("reason", "No reason") if isinstance(u, dict) else "No reason"
        lines.append(f"<code>{u.get('user_id', 'N/A')}</code> \u2014 {reason}")
    return "\n".join(lines)


def format_broadcast_preview(message: str, recipient_count: int) -> str:
    return (
        f"<b>Broadcast Preview</b>\n"
        f"{format_divider()}\n\n"
        f"Recipients: {recipient_count:,} users\n"
        f"Message:\n{message[:500]}...\n\n"
        "This message will be sent to all recipients."
    )


def format_ticket_list(tickets: list, title: str = "Tickets") -> str:
    if not tickets:
        return f"<b>{title}</b>\n{format_divider()}\n\nNo tickets found."
    lines = [f"<b>{title}</b>\n{format_divider()}"]
    for ticket in tickets[:15]:
        status_text = ticket.status.replace("_", " ").upper()
        priority_text = ticket.priority.upper()
        created = ticket.created_at.strftime("%d %b %H:%M") if ticket.created_at else "N/A"
        has_reply = " \u2022 Has Reply" if ticket.last_admin_reply_at else ""
        lines.append(
            f"<b>#{ticket.id}</b> {status_text} | {priority_text}\n"
            f"   User: <code>{ticket.user_id}</code> | {created}{has_reply}"
        )
    if len(tickets) > 15:
        lines.append(f"\n...and {len(tickets) - 15} more")
    return "\n".join(lines)


def format_ticket_detail(ticket) -> str:
    status_text = ticket.status.replace("_", " ").upper()
    priority_text = ticket.priority.upper()
    created = ticket.created_at.strftime("%d %b %Y %H:%M") if ticket.created_at else "N/A"
    updated = ticket.updated_at.strftime("%d %b %Y %H:%M") if ticket.updated_at else "N/A"

    lines = [
        f"<b>Ticket #{ticket.id}</b>\n{format_divider()}",
        f"Subject: {ticket.subject}",
        f"Status: {status_text}",
        f"Priority: {priority_text}",
        f"User: <code>{ticket.user_id}</code>",
        f"Username: {ticket.username or 'N/A'}",
        f"Created: {created}",
        f"Updated: {updated}",
    ]
    if ticket.description:
        lines.append(f"\nDescription:\n{ticket.description[:500]}")
    if ticket.ai_response:
        lines.append(f"\nAI Response:\n{ticket.ai_response[:300]}")
    if ticket.admin_response:
        admin_time = ticket.last_admin_reply_at.strftime("%d %b %H:%M") if ticket.last_admin_reply_at else "N/A"
        lines.append(f"\nAdmin Response:\n{ticket.admin_response[:300]}")
        lines.append(f"Replied: {admin_time}")
    if ticket.rating:
        lines.append(f"\nRating: {ticket.rating}/5")
    return "\n".join(lines)


def format_ticket_metrics(metrics: dict) -> str:
    return (
        f"<b>Ticket Metrics</b>\n{format_divider()}\n\n"
        f"Total Tickets: {metrics.get('total', 0):,}\n"
        f"Open: {metrics.get('open', 0):,}\n"
        f"In Progress: {metrics.get('in_progress', 0):,}\n"
        f"Resolved: {metrics.get('resolved', 0):,}\n"
        f"Closed: {metrics.get('closed', 0):,}\n\n"
        f"Stale (48h+): {metrics.get('stale', 0):,}\n"
        f"Resolved (7d): {metrics.get('resolved_7d', 0):,}\n\n"
        f"Avg Rating: {metrics.get('avg_rating', 0):.1f}/5"
    )


def format_user_list(users: list) -> str:
    if not users:
        return f"<b>User Search</b>\n{format_divider()}\n\nNo users found."
    lines = [f"<b>Users</b>\n{format_divider()}"]
    for user in users[:20]:
        alerts = "On" if user.alerts_enabled else "Off"
        lines.append(f"\u2022 <code>{user.user_id}</code> | Alerts: {alerts}")
    if len(users) > 20:
        lines.append(f"\n...and {len(users) - 20} more")
    return "\n".join(lines)


def format_db_stats(stats: dict) -> str:
    return (
        f"<b>Database Stats</b>\n{format_divider()}\n\n"
        f"Crypto Users: {stats.get('crypto_users', 0):,}\n"
        f"Subscriptions: {stats.get('subscriptions', 0):,}\n"
        f"Activation Keys: {stats.get('activation_keys', 0):,}\n"
        f"Support Tickets: {stats.get('support_tickets', 0):,}\n"
        f"FAQs: {stats.get('faqs', 0):,}\n"
        f"Canned Responses: {stats.get('canned_responses', 0):,}\n"
        f"Groups: {stats.get('groups', 0):,}\n"
        f"Moderation Logs: {stats.get('moderation_logs', 0):,}"
    )


def format_revenue_detailed(report: dict) -> str:
    return (
        f"<b>Revenue Report</b>\n{format_divider()}\n\n"
        f"Active Subscriptions: {report.get('active_subscriptions', 0):,}\n"
        f"Keys Redeemed (Month): {report.get('keys_redeemed_month', 0):,}\n"
        f"Total Keys Redeemed: {report.get('total_keys_redeemed', 0):,}\n\n"
        f"<b>Estimated Revenue</b>\n"
        f"MRR: \u20b9{report.get('estimated_mrr', 0):,.2f}\n"
        f"Annual: \u20b9{report.get('estimated_annual', 0):,.2f}\n\n"
        "Based on \u20b9149/month base plan"
    )


def format_key_history(keys: list) -> str:
    if not keys:
        return f"<b>Key Usage History</b>\n{format_divider()}\n\nNo used keys found."
    lines = [f"<b>Recently Used Keys</b>\n{format_divider()}"]
    for key in keys[:15]:
        used_at = key.used_at.strftime("%d %b %Y") if key.used_at else "N/A"
        lines.append(f"\u2022 <code>{key.key_string}</code>\n   {key.duration_days}d \u2192 <code>{key.used_by}</code> | {used_at}")
    return "\n".join(lines)


def format_faq_list(faqs: list) -> str:
    if not faqs:
        return f"<b>FAQ Management</b>\n{format_divider()}\n\nNo FAQs found."
    lines = [f"<b>FAQs</b>\n{format_divider()}"]
    for faq in faqs[:15]:
        lines.append(
            f"Q: {faq.question[:50]}...\n"
            f"A: {faq.answer[:80]}...\n"
            f"Category: {faq.category} | <code>#{faq.id}</code>\n"
        )
    return "\n".join(lines)


def format_canned_list(canned: list) -> str:
    if not canned:
        return f"<b>Canned Responses</b>\n{format_divider()}\n\nNo canned responses found."
    lines = [f"<b>Canned Responses</b>\n{format_divider()}"]
    for c in canned[:15]:
        lines.append(f"<b>{c.tag}</b>\n{c.content[:60]}...\nUsed: {c.usage_count}x\n")
    return "\n".join(lines)


# ── Inline Helpers ─────────────────────────────────────────

def get_user_management_help() -> str:
    return (
        "<b>User Management</b>\n"
        f"{format_divider()}\n\n"
        "Use commands:\n"
        "\u2022 <code>/lookup [USER_ID]</code> \u2014 View user subscription\n"
        "\u2022 <code>/extend [USER_ID] [DAYS]</code> \u2014 Extend subscription\n"
        "\u2022 <code>/revoke [USER_ID]</code> \u2014 Revoke subscription"
    )


def get_bulk_keygen_help() -> str:
    return (
        "<b>Bulk Key Generation</b>\n"
        f"{format_divider()}\n\n"
        "Select quick options or use command:\n"
        "<code>/bulkkeygen [COUNT] [DAYS]</code>\n\n"
        "Example: <code>/bulkkeygen 10 30</code>"
    )


def get_bulk_keygen_success(count: int, days: int, keys: list) -> str:
    keys_text = "\n".join([f"<code>{k}</code>" for k in keys])
    return (
        f"<b>Bulk Key Generated</b>\n"
        f"{format_divider()}\n\n"
        f"Count: {count} keys\n"
        f"Duration: {days} days\n\n"
        f"Keys:\n{keys_text}"
    )


def get_keygen_success(key: str, days: int) -> str:
    return (
        f"<b>Key Generated</b>\n"
        f"{format_divider()}\n\n"
        f"<code>{key}</code>\n\n"
        f"Duration: {days} days"
    )


def get_broadcast_result(user_ids: list, pro_user_ids: list, group_ids: list, sent: int, failed: int) -> str:
    return (
        f"<b>Broadcast Complete</b>\n"
        f"{format_divider()}\n\n"
        f"Users: {len(user_ids)}\n"
        f"Pro Users: {len(pro_user_ids)}\n"
        f"Groups: {len(group_ids)}\n"
        f"Sent: {sent}\n"
        f"Failed: {failed}"
    )


def get_resolve_success(ticket_id: int) -> str:
    return f"<b>Ticket Resolved</b>\n\nTicket #{ticket_id} has been resolved. User has been notified."


def get_ticket_inprogress_success(ticket_id: int) -> str:
    return f"<b>Ticket In-Progress</b>\n\nTicket #{ticket_id} is now being worked on."


def get_ticket_close_success(ticket_id: int) -> str:
    return f"<b>Ticket Closed</b>\n\nTicket #{ticket_id} has been closed."


def get_ticket_not_found_msg() -> str:
    return "Ticket not found or cannot be closed."


def get_faq_menu_msg(faq_count: int, canned_count: int) -> str:
    return (
        f"<b>FAQ & Canned Management</b>\n"
        f"{format_divider()}\n\n"
        f"FAQs: {faq_count}\n"
        f"Canned Responses: {canned_count}\n\n"
        f"Use commands to manage:\n"
        f"<code>/faq list</code> \u2014 List FAQs\n"
        f"<code>/faq add</code> \u2014 Add FAQ\n"
        f"<code>/canned list</code> \u2014 List canned responses"
    )


def get_rate_limit_msg(seconds: int) -> str:
    return f"Please wait {seconds} seconds between commands."


def get_unauthorized_msg() -> str:
    return "Unauthorized."
