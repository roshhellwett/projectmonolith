from datetime import UTC, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.formatters import (
    format_card,
    format_divider,
    format_header,
    format_kv,
)

# ── Keyboards ──────────────────────────────────────────────


def get_admin_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 Overview", callback_data="admin_overview"),
            InlineKeyboardButton("🟢 Bot Health", callback_data="admin_health"),
        ],
        [
            InlineKeyboardButton("🪙 Crypto Bot Admin", callback_data="admin_crypto_menu"),
            InlineKeyboardButton("🛡️ Group Bot Admin", callback_data="admin_group_menu"),
        ],
        [
            InlineKeyboardButton("👥 User Registry", callback_data="admin_users"),
            InlineKeyboardButton("📡 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton("💰 Revenue & MRR", callback_data="admin_revenue"),
            InlineKeyboardButton("💾 Database Stats", callback_data="admin_db_stats"),
        ],
        [
            InlineKeyboardButton("📜 Audit Log", callback_data="admin_audit"),
            InlineKeyboardButton("🔒 Security Matrix", callback_data="admin_security"),
        ],
        [InlineKeyboardButton("◀️ Exit to Main Menu", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin_main")]])


def get_crypto_admin_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🔑 Gen Crypto Key (30d)", callback_data="admin_crypto_keygen_30"),
            InlineKeyboardButton("🔑 Gen Crypto Key (90d)", callback_data="admin_crypto_keygen_90"),
        ],
        [
            InlineKeyboardButton("📋 View Crypto Subs", callback_data="admin_crypto_subs"),
        ],
        [InlineKeyboardButton("Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_group_admin_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🔑 Gen Group Key (30d)", callback_data="admin_group_keygen_30"),
            InlineKeyboardButton("🔑 Gen Group Key (90d)", callback_data="admin_group_keygen_90"),
        ],
        [
            InlineKeyboardButton("📋 View Group Subs", callback_data="admin_group_subs"),
        ],
        [InlineKeyboardButton("Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_system_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Database Stats", callback_data="admin_db_stats")],
        [InlineKeyboardButton("Key History", callback_data="admin_key_history")],
        [InlineKeyboardButton("Back", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ── Messages / Formatting ──────────────────────────────────


def get_admin_dashboard() -> str:
    items = [
        "System Architecture: <b>Zenith Enterprise Multi-Bot Cluster</b>",
        "Security Authorization: <b>Verified Master Administrator</b>",
        "Telemetry Status: <b>Live Real-Time Event Sync</b>",
    ]
    return (
        f"{format_header('Zenith Master Command', 'Global Infrastructure & Bot Orchestration', 'OWNER VIP')}\n"
        f"{format_card('Cluster Status & Security Matrix', items, '⚡')}\n\n"
        f"<i>Select a control module below to inspect system health, manage tickets, or generate keys.</i>"
    )


def format_system_overview(stats: dict, ticket_stats: dict) -> str:
    user_items = [
        f"Total Registered Users: <code>{stats.get('total_users', 0):,}</code>",
        f"Pro VIP Subscribers: <code>{stats.get('pro_users', 0):,}</code>",
        f"Free Tier Accounts: <code>{stats.get('free_users', 0):,}</code>",
        f"Active Subscriptions: <code>{stats.get('active_subscriptions', 0):,}</code>",
        f"Expiring within 7 Days: <code>{stats.get('expiring_within_7_days', 0):,}</code>",
    ]
    ticket_items = [
        f"Total Inquiries: <code>{ticket_stats.get('total', 0)}</code>",
        f"Open Queue: <code>{ticket_stats.get('open', 0)}</code>",
        f"In Progress Triage: <code>{ticket_stats.get('in_progress', 0)}</code>",
        f"Resolved & Closed: <code>{ticket_stats.get('resolved', 0)}</code>",
    ]
    return (
        f"{format_header('Global Overview', 'System Demographics & Ticket Telemetry', 'LIVE')}\n"
        f"{format_card('User Registry Telemetry', user_items, '👥')}\n\n"
        f"{format_card('Support Ticket Queue Matrix', ticket_items, '🎫')}"
    )


def format_key_management(keys: list) -> str:
    if not keys:
        return (
            f"{format_header('License Key Registry', 'Active & Unused Activation Token Matrix', '0 KEYS')}\n"
            f"📭 No unused activation tokens available in the vault.\nUse <b>Bulk KeyGen</b> or create new keys via menu options."
        )
    lines = [
        format_header("License Key Registry", "Active & Unused Activation Token Matrix", f"{len(keys)} KEYS"),
        "<b>Available Activation Tokens:</b>",
    ]
    for key in keys:
        days = key.duration_days
        created = key.created_at.strftime("%d %b %Y") if key.created_at else "N/A"
        lines.append(f"  ▫️ <code>{key.key_string}</code> — <b>{days}d</b> (Created {created})")
    lines.append("\n<i>Share tokens with users to grant instant Pro suite authorization.</i>")
    return "\n".join(lines)


def format_user_management(user_id: int, sub_details: dict) -> str:
    if not sub_details.get("has_subscription", False):
        return (
            f"{format_header('User Dossier', f'Account Telemetry — ID: {user_id}', 'FREE TIER')}\n"
            f"{format_kv('Account Status', 'Standard Free Access', '👤')}\n"
            f"{format_kv('Subscription', 'None Active', '🚫')}\n\n"
            f"<i>Use /extend {user_id} [DAYS] to manually assign Pro VIP authorization.</i>"
        )
    expires = sub_details.get("expires_at")
    expires_str = expires.strftime("%d %b %Y") if expires else "N/A"
    days_left = sub_details.get("days_left", 0)
    return (
        f"{format_header('User Dossier', f'Account Telemetry — ID: {user_id}', 'PRO ACTIVE')}\n"
        f"{format_kv('Account Status', 'Enterprise Pro VIP Member', '💎')}\n"
        f"{format_kv('Days Remaining', f'{days_left} days', '🗓️')}\n"
        f"{format_kv('Expiration Date', expires_str, '⚡')}\n\n"
        f"<i>Use /extend or /revoke to manage this license.</i>"
    )


def format_bot_health(bots: list) -> str:
    from core.circuit_breaker import get_all_breaker_statuses
    from core.db_health import is_db_healthy

    db_icon = "🟢 Healthy & Synced" if is_db_healthy() else "🔴 Unhealthy Connection"
    lines = [
        format_header(
            "Cluster Diagnostics",
            "Real-Time Health & Circuit Breaker Telemetry",
            "HEALTHY" if is_db_healthy() else "ALERT",
        ),
        f"<b>Database Engine:</b> {db_icon}\n",
    ]

    breakers = get_all_breaker_statuses()
    if breakers:
        lines.append("<b>Circuit Breaker Matrix:</b>")
        for b in breakers:
            state_icon = "🟢" if b["state"] == "closed" else ("🔴" if b["state"] == "open" else "🟡")
            lines.append(
                f"  ▫️ <b>{b['name']}</b>: {state_icon} {b['state'].upper()} (Recent Fails: <code>{b['recent_failures']}</code>)"
            )
        lines.append("")

    if not bots:
        lines.append("📭 No bot instances currently registered in monitoring table.")
    else:
        lines.append("<b>Monitored Cluster Nodes:</b>")
        for bot in bots:
            status_icon = (
                "🟢 Active" if bot.status == "active" else ("🔴 Error" if bot.status == "error" else "⚪ Inactive")
            )
            health = bot.health_status or "unknown"
            last_check = bot.last_health_check.strftime("%d %b %H:%M") if bot.last_health_check else "Never"
            lines.append(f"  ▫️ <b>{bot.bot_name}</b>: {status_icon} | Health: {health.upper()} (Checked {last_check})")
    return "\n".join(lines)


def format_platform_metrics() -> str:
    from core.circuit_breaker import get_all_breaker_statuses
    from core.db_health import is_db_healthy

    db_status = "✅ Healthy" if is_db_healthy() else "❌ Unhealthy"
    breakers = get_all_breaker_statuses()
    breaker_lines = []
    for b in breakers:
        state = b.get("state", "unknown")
        icon = {"closed": "✅", "open": "🔴", "half-open": "⚠️"}.get(state, "❓")
        name = b.get("name", "unknown")
        breaker_lines.append(f"  {icon} <b>{name}</b>: {state}")

    items = [
        f"Database: {db_status}",
    ]
    if breaker_lines:
        items.append("<b>Circuit Breakers:</b>")
        items.extend(breaker_lines)

    return (
        f"{format_header('Platform Health', 'Service Status & Metrics', '')}\n"
        f"{format_card('Health Dashboard', items, '🖥️')}"
    )


def format_audit_log(logs: list) -> str:
    if not logs:
        return (
            f"{format_header('Forensic Audit Log', 'Administrator Action & Mutation History', '0 LOGS')}\n"
            f"📭 No recent administrative mutations recorded."
        )
    lines = [
        format_header("Forensic Audit Log", "Administrator Action & Mutation History", f"{len(logs)} LOGS"),
        "<b>Recent Admin Mutations:</b>",
    ]
    for log in logs[:15]:
        time_str = log.created_at.strftime("%d %b %H:%M") if log.created_at else "N/A"
        target = f"User: <code>{log.target_user_id}</code>" if log.target_user_id else ""
        details = f" — {log.details}" if log.details else ""
        lines.append(f"  ▫️ <b>{log.action.value.upper()}</b> ({time_str})\n     {target}{details}")
    return "\n".join(lines)


def format_revenue_analytics(stats: dict) -> str:
    pro_users = stats.get("pro_users", 0)
    active_subs = stats.get("active_subscriptions", 0)
    avg_value_per_user = 149
    estimated_mrr = active_subs * avg_value_per_user
    estimated_annual = estimated_mrr * 12

    items = [
        f"Active Pro Subscribers: <code>{pro_users:,}</code>",
        f"Total Active Subscriptions: <code>{active_subs:,}</code>",
        f"Expiring / At-Risk (7d): <code>{stats.get('expiring_within_7_days', 0):,}</code>",
        f"Monthly Recurring Revenue (MRR): <b>₹{estimated_mrr:,.2f}</b>",
        f"Annualized Run-Rate (ARR): <b>₹{estimated_annual:,.2f}</b>",
    ]
    return (
        f"{format_header('Revenue & MRR Telemetry', 'Monetization Metrics & Subscription Flow', 'ACTIVE')}\n"
        f"{format_card('Monetization Dashboard', items, '💰')}\n\n"
        f"<i>💡 Note: Calculation based on ₹149/month standard tier billing.</i>"
    )


def format_subscription_list(subscriptions: list) -> str:
    if not subscriptions:
        return "<b>Active Subscriptions</b>\n\nNo active subscriptions."
    lines = ["<b>Active Subscriptions</b>"]
    for sub in subscriptions[:20]:
        if sub.expires_at:
            expires = sub.expires_at.strftime("%d %b %Y")
            now_tz = (
                datetime.now(UTC)
                if getattr(sub.expires_at, "tzinfo", None) is not None
                else datetime.now(UTC).replace(tzinfo=None)
            )
            days_left = (sub.expires_at - now_tz).days
        else:
            expires = "N/A"
            days_left = 0
        lines.append(f"\u2022 <code>{sub.user_id}</code> \u2014 {expires} ({days_left}d)")
    if len(subscriptions) > 20:
        lines.append(f"\n...and {len(subscriptions) - 20} more")
    return "\n".join(lines)


def format_group_list(groups: list) -> str:
    if not groups:
        return "<b>Group Management</b>\n\nNo active groups found."
    lines = ["<b>Active Groups</b>"]
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
        return "<b>Group Search</b>\n\nNo groups found."
    lines = ["<b>Groups</b>"]
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
        return "<b>Banned Users</b>\n\nNo banned users."
    lines = ["<b>Banned Users</b>"]
    for u in users[:20]:
        reason = u.get("reason", "No reason") if isinstance(u, dict) else "No reason"
        lines.append(f"<code>{u.get('user_id', 'N/A')}</code> \u2014 {reason}")
    return "\n".join(lines)


def format_broadcast_preview(message: str, recipient_count: int) -> str:
    return (
        f"<b>Broadcast Preview</b>\n"
        ""
        f"Recipients: {recipient_count:,} users\n"
        f"Message:\n{message[:500]}...\n\n"
        "This message will be sent to all recipients."
    )


def format_ticket_list(tickets: list, title: str = "Tickets") -> str:
    if not tickets:
        return f"<b>{title}</b>\n\nNo tickets found."
    lines = [f"<b>{title}</b>"]
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
        f"<b>Ticket #{ticket.id}</b>",
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
        f"<b>Ticket Metrics</b>\n\n"
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
        return "<b>User Search</b>\n\nNo users found."
    lines = ["<b>Users</b>"]
    for user in users[:20]:
        alerts = "On" if user.alerts_enabled else "Off"
        lines.append(f"\u2022 <code>{user.user_id}</code> | Alerts: {alerts}")
    if len(users) > 20:
        lines.append(f"\n...and {len(users) - 20} more")
    return "\n".join(lines)


def format_db_stats(stats: dict) -> str:
    return (
        f"<b>Database Stats</b>\n\n"
        f"Crypto Users: {stats.get('crypto_users', 0):,}\n"
        f"Subscriptions: {stats.get('subscriptions', 0):,}\n"
        f"Activation Keys: {stats.get('activation_keys', 0):,}\n"
        f"Groups: {stats.get('groups', 0):,}\n"
        f"Moderation Logs: {stats.get('moderation_logs', 0):,}"
    )


def format_revenue_detailed(report: dict) -> str:
    return (
        f"<b>Revenue Report</b>\n\n"
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
        return "<b>Key Usage History</b>\n\nNo used keys found."
    lines = ["<b>Recently Used Keys</b>"]
    for key in keys[:15]:
        used_at = key.used_at.strftime("%d %b %Y") if key.used_at else "N/A"
        lines.append(
            f"\u2022 <code>{key.key_string}</code>\n   {key.duration_days}d \u2192 <code>{key.used_by}</code> | {used_at}"
        )
    return "\n".join(lines)


def format_faq_list(faqs: list) -> str:
    if not faqs:
        return "<b>FAQ Management</b>\n\nNo FAQs found."
    lines = ["<b>FAQs</b>"]
    for faq in faqs[:15]:
        lines.append(
            f"Q: {faq.question[:50]}...\n"
            f"A: {faq.answer[:80]}...\n"
            f"Category: {faq.category} | <code>#{faq.id}</code>\n"
        )
    return "\n".join(lines)


def format_canned_list(canned: list) -> str:
    if not canned:
        return "<b>Canned Responses</b>\n\nNo canned responses found."
    lines = ["<b>Canned Responses</b>"]
    for c in canned[:15]:
        lines.append(f"<b>{c.tag}</b>\n{c.content[:60]}...\nUsed: {c.usage_count}x\n")
    return "\n".join(lines)


# ── Inline Helpers ─────────────────────────────────────────


def get_user_management_help() -> str:
    return (
        "<b>User Management</b>\n"
        ""
        "Use commands:\n"
        "\u2022 <code>/lookup [USER_ID]</code> \u2014 View user subscription\n"
        "\u2022 <code>/extend [USER_ID] [DAYS]</code> \u2014 Extend subscription\n"
        "\u2022 <code>/revoke [USER_ID]</code> \u2014 Revoke subscription"
    )


def get_bulk_keygen_help() -> str:
    return (
        "<b>Bulk Key Generation</b>\n"
        ""
        "Select quick options or use command:\n"
        "<code>/bulkkeygen [COUNT] [DAYS]</code>\n\n"
        "Example: <code>/bulkkeygen 10 30</code>"
    )


def get_bulk_keygen_success(count: int, days: int, keys: list) -> str:
    keys_text = "\n".join([f"<code>{k}</code>" for k in keys])
    return f"<b>Bulk Key Generated</b>\n" "" f"Count: {count} keys\n" f"Duration: {days} days\n\n" f"Keys:\n{keys_text}"


def get_keygen_success(key: str, days: int) -> str:
    return f"<b>Key Generated</b>\n" f"{format_divider()}\n\n" f"<code>{key}</code>\n\n" f"Duration: {days} days"


def get_broadcast_result(user_ids: list, pro_user_ids: list, group_ids: list, sent: int, failed: int) -> str:
    return (
        f"<b>Broadcast Complete</b>\n"
        ""
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
        ""
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
