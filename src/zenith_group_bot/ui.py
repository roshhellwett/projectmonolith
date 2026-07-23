from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID
from core.formatters import (
    format_card,
    format_header,
    format_kv,
)

# ============================================================
# KEYBOARD BUILDERS
# ============================================================


def get_admin_dashboard(is_pro: bool, groups: list, usage: dict = None) -> InlineKeyboardMarkup:
    group_limit = 5 if is_pro else 1
    group_count = len(groups)

    tier_label = "💎 PRO SHIELD ACTIVE" if is_pro else "⚪ STANDARD FREE TIER"
    rows = [
        [InlineKeyboardButton(tier_label, callback_data="grp_status")],
        [
            InlineKeyboardButton("🚀 Features", callback_data="grp_features"),
            InlineKeyboardButton("❓ Help & Commands", callback_data="grp_help"),
        ],
    ]

    if is_pro:
        rows.extend(
            [
                [
                    InlineKeyboardButton("📊 Analytics Dashboard", callback_data="grp_analytics_pick"),
                    InlineKeyboardButton("📜 Security Audit Log", callback_data="grp_audit_pick"),
                ],
                [
                    InlineKeyboardButton("🚫 Custom Word Filters", callback_data="grp_words_help"),
                    InlineKeyboardButton("⏰ Automated Schedules", callback_data="grp_schedule_help"),
                ],
                [InlineKeyboardButton("👋 Custom Welcome Protocol", callback_data="grp_welcome_help")],
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    "💎 Upgrade to Pro Shield (Unlimited Protection)", url=f"tg://user?id={ADMIN_USER_ID}"
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def get_group_picker(groups: list, action_prefix: str, is_pro: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for g in groups[:5]:
        name = g.group_name or f"Group {g.chat_id}"
        status = "Active" if g.is_active else "Inactive"
        members = getattr(g, "member_count", None)
        label = f"{name} — {status}"
        if members is not None:
            label += f" ({members})"
        rows.append([InlineKeyboardButton(label, callback_data=f"{action_prefix}_{g.chat_id}")])

    if not is_pro and len(groups) >= 1:
        rows.append([InlineKeyboardButton("Upgrade for More Groups", url=f"tg://user?id={ADMIN_USER_ID}")])

    rows.append([InlineKeyboardButton("Back", callback_data="grp_main_menu")])
    return InlineKeyboardMarkup(rows)


def get_group_settings_keyboard(chat_id: int, group_settings: dict = None) -> InlineKeyboardMarkup:
    anti_spam = group_settings.get("anti_spam", True) if group_settings else True
    anti_abuse = group_settings.get("anti_abuse", True) if group_settings else True
    flood_control = group_settings.get("flood_control", True) if group_settings else True

    rows = [
        [
            InlineKeyboardButton(
                f"Anti-Spam: {'On' if anti_spam else 'Off'}", callback_data=f"grp_toggle_spam_{chat_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"Anti-Abuse: {'On' if anti_abuse else 'Off'}", callback_data=f"grp_toggle_abuse_{chat_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"Flood Control: {'On' if flood_control else 'Off'}", callback_data=f"grp_toggle_flood_{chat_id}"
            )
        ],
        [InlineKeyboardButton("Configure", callback_data=f"grp_config_{chat_id}")],
        [InlineKeyboardButton("Back to Dashboard", callback_data="grp_dash")],
    ]
    return InlineKeyboardMarkup(rows)


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="grp_main_menu")]])


# ============================================================
# CONFIRMATION DIALOGS
# ============================================================


def get_confirm_forgive(user_id: int, user_name: str = None, strikes: int = 0) -> tuple:
    name = user_name or f"User {user_id}"
    msg = (
        f"<b>Confirm Forgive</b>\n\n"
        f"User: {name}\n"
        f"Current strikes: {strikes}\n\n"
        f"This will clear all strikes for this user."
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, Forgive", callback_data=f"grp_forgive_{user_id}")],
            [InlineKeyboardButton("Cancel", callback_data="grp_dash")],
        ]
    )
    return msg, kb


def get_confirm_reset(group_name: str = None, chat_id: int = None) -> tuple:
    name = group_name or "this group"
    cb_data = f"grp_reset_confirm_{chat_id}" if chat_id else "grp_reset_confirm"
    msg = (
        f"<b>Reset {escape(name.upper())}?</b>\n\n"
        f"<b>This will:</b>\n"
        f"\u2022 Delete all group settings\n"
        f"\u2022 Remove all custom words\n"
        f"\u2022 Clear all scheduled messages\n"
        f"\u2022 Clear all moderation history\n\n"
        f"This action cannot be undone."
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, Reset Everything", callback_data=cb_data)],
            [InlineKeyboardButton("Cancel", callback_data="grp_dash")],
        ]
    )
    return msg, kb


def get_confirm_add_word(word: str) -> tuple:
    msg = (
        f"<b>Add Banned Word?</b>\n\n"
        f"Word: <code>{escape(word)}</code>\n\n"
        f"This word will be automatically deleted when posted."
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Add Word", callback_data=f"grp_addword_confirm_{word}")],
            [InlineKeyboardButton("Cancel", callback_data="grp_words_help")],
        ]
    )
    return msg, kb


def get_confirm_delete_word(word: str) -> tuple:
    msg = (
        f"<b>Remove Banned Word?</b>\n\n"
        f"Word: <code>{escape(word)}</code>\n\n"
        f"This word will no longer be filtered."
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Remove Word", callback_data=f"grp_delword_confirm_{word}")],
            [InlineKeyboardButton("Cancel", callback_data="grp_words_help")],
        ]
    )
    return msg, kb


def get_confirm_schedule(time_str: str, schedule_text: str) -> tuple:
    msg = f"<b>Confirm Schedule?</b>\n\n" f"Time (UTC): {time_str}\n" f"Message: {escape(schedule_text[:100])}..."
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm", callback_data=f"grp_schedule_confirm_{time_str}")],
            [InlineKeyboardButton("Cancel", callback_data="grp_schedule_help")],
        ]
    )
    return msg, kb


# ============================================================
# DASHBOARD MESSAGES
# ============================================================


def get_start_group_msg() -> str:
    return "Use /setup in your group to get started. Message me in DMs for the dashboard."


def get_dashboard_main_msg(is_pro: bool, groups: list, days_left: int = 0) -> str:
    max_groups = 5 if is_pro else 1
    active = sum(1 for g in groups if g.is_active)
    status_badge = f"PRO ACTIVE ({days_left}d)" if is_pro else "FREE TIER"

    items = [
        f"Protected Communities: <code>{active} / {max_groups}</code>",
        f"Security Shield: <b>{'🛡️ Enterprise Pro Lockdown' if is_pro else '⚪ Basic Public Shield'}</b>",
        f"Automated Filters: <b>{'Anti-Raid + Custom Regex + AI Scans' if is_pro else 'Default Spam Filter'}</b>",
    ]
    if is_pro:
        items.append(f"Pro Access Remaining: <b>{days_left} Days</b>")

    text = (
        f"{format_header('Zenith Group Shield', 'Autonomous Community Protection Matrix', status_badge)}\n"
        f"{format_card('System Telemetry', items, '⚡')}\n\n"
        "<i>Use the dashboard below to navigate the terminal.</i>"
    )
    if not is_pro:
        text += "\n\n<i>💎 Tip: Upgrade to Pro Shield (/activate) to unlock custom word filters, anti-raid lockdown, and 5 groups.</i>"
    return text


def get_status_msg(is_pro: bool, days: int = 0) -> str:
    if is_pro:
        items = [
            "Protection across up to 5 Telegram communities",
            "Custom word & regex auto-delete filters (200/group)",
            "Instant Anti-Raid emergency lockdown shield",
            "Comprehensive moderation analytics & top violators",
            "Automated recurring scheduled announcements",
            "Personalized welcome protocols for new members",
            "Complete forensic audit log of all admin actions",
        ]
        return (
            f"{format_header('Subscription Status', 'Zenith Pro Shield Suite', 'ACTIVE')}\n"
            f"{format_kv('Days Remaining', f'{days} days', '🗓️')}\n"
            f"{format_kv('System Tier', 'Enterprise Group Shield', '💎')}\n\n"
            f"{format_card('Unlocked Shield Capabilities', items, '✨')}"
        )
    items = [
        "1 group protection limit",
        "Standard word filter list only",
        "Basic spam and flood protection",
    ]
    return (
        f"{format_header('Subscription Status', 'Standard Tier Access', 'FREE')}\n"
        f"{format_card('Current Tier Limitations', items, '🔒')}\n\n"
        f"⚡ <i>Unlock full community security and automation with Pro Shield. Contact @roshhellwett or use <code>/activate YOUR-KEY</code>.</i>"
    )


def get_group_list_msg(groups: list) -> str:
    if not groups:
        return (
            f"{format_header('Protected Communities', 'Active Group Registry', '0 GROUPS')}\n"
            f"📭 No communities currently linked.\nAdd Zenith to your group as an admin and run <code>/setup</code> inside the group chat!"
        )

    lines = [
        format_header("Protected Communities", "Active Group Registry", f"{len(groups)} GROUPS"),
        "<b>Linked Communities:</b>",
    ]
    for g in groups:
        status = "🟢 Active Shield" if g.is_active else "🔴 Inactive"
        name = g.group_name or f"Group {g.chat_id}"
        lines.append(f"  ▫️ <b>{escape(name)}</b> — {status}")
    lines.append("\n<i>Select a group below to manage anti-spam, custom filters, and security settings.</i>")
    return "\n".join(lines)


def get_dashboard_help_msg(callback: str) -> str:
    help_texts = {
        "grp_analytics_pick": ("<b>Analytics</b>\n\nUse in your group:\n" "/analytics"),
        "grp_audit_pick": ("<b>Audit Log</b>\n\nUse in your group:\n" "/auditlog [count]"),
        "grp_words_help": (
            "<b>Custom Words</b>\n\nUse in group:\n" "/addword [word]\n" "/delword [word]\n" "/wordlist"
        ),
        "grp_schedule_help": (
            "<b>Schedules</b>\n\nUse in group:\n" "/schedule HH:MM [message]\n" "/schedules\n" "/delschedule [id]"
        ),
        "grp_welcome_help": ("<b>Welcome</b>\n\nUse in group:\n" "/welcome Hello {name}!\n" "/welcomeoff"),
    }
    return help_texts.get(callback, "")


def get_activate_help() -> str:
    return "<b>Activate Pro</b>\n\nUsage: /activate [YOUR_KEY]"


# ============================================================
# PRO FEATURE MESSAGES
# ============================================================


def get_word_help() -> str:
    return (
        "<b>Custom Word Filter</b>\n\n"
        "Usage: /addword [WORD]\n\n"
        "Example:\n"
        "/addword scam\n\n"
        "Added words will trigger automatic deletion."
    )


def get_addword_result(word: str, count: int, success: bool = True) -> str:
    if success:
        return (
            f"Word Added\n\n"
            f"<code>{escape(word)}</code> will now trigger message deletion.\n\n"
            f"Total custom words: {count}/200"
        )
    return "Already Added\n\nThis word is already in the filter."


def get_delword_result(word: str, success: bool = True) -> str:
    if success:
        return f"Word Removed\n\n<code>{escape(word)}</code> is no longer filtered."
    return "Word Not Found\n\n" "This word is not in your filter list.\n" "Use /wordlist to see all filtered words."


def get_delword_help() -> str:
    return "<b>Remove Custom Word</b>\n\n" "Usage: /delword [WORD]\n\n" "Example:\n" "/delword scam"


def get_wordlist_msg(words: list, count: int, limit: int = 200) -> str:
    if not words:
        return "<b>Custom Word Filter</b>\n\nNo custom words added yet.\n/addword [WORD]"

    word_list = ", ".join(f"<code>{escape(w)}</code>" for w in words[:50])
    return f"<b>Custom Word Filter ({count}/{limit})</b>\n\n{word_list}"


def get_word_limit_msg(current: int, limit: int) -> str:
    return (
        f"<b>Word Limit Reached</b>\n\n"
        f"You've added {current}/{limit} custom words.\n\n"
        f"Remove some words to add more, or upgrade to PRO for {limit} words."
    )


def get_schedule_help() -> str:
    return (
        "<b>Scheduled Messages</b>\n\n"
        "Format: /schedule [HH:MM] [MESSAGE]\n\n"
        "Examples:\n"
        "\u2022 /schedule 09:00 Good morning!\n"
        "\u2022 /schedule 20:00 Please read the pinned rules.\n\n"
        "Times are in UTC. Messages repeat daily."
    )


def get_schedule_time_error() -> str:
    return (
        "<b>Invalid Time Format</b>\n\n"
        "Use HH:MM in 24-hour format.\n\n"
        "Examples:\n"
        "\u2022 09:00 (9 AM)\n"
        "\u2022 14:30 (2:30 PM)\n"
        "\u2022 23:59 (11:59 PM)"
    )


def get_schedule_length_error() -> str:
    return "<b>Message Too Long</b>\n\nMessage must be under 1000 characters."


def get_schedule_limit_reached(limit: int) -> str:
    return (
        f"<b>Schedule Limit Reached</b>\n\n"
        f"You've reached the maximum of {limit} scheduled messages.\n\n"
        f"Delete some to add more."
    )


def get_schedule_success(hour: int, minute: int, message_text: str, sid: int) -> str:
    return (
        f"Message Scheduled\n\n"
        f"Time: {hour:02d}:{minute:02d} UTC (daily)\n"
        f"Message: {escape(message_text[:100])}...\n\n"
        f"ID: <code>{sid}</code>\n\n"
        f"Delete with /delschedule {sid}"
    )


def get_schedules_list(items: list) -> str:
    if not items:
        return "<b>Scheduled Messages</b>\n\nNo active schedules.\n/schedule 09:00 Good morning!"

    lines = ["<b>Scheduled Messages</b>", ""]
    for s in items:
        preview = s.message_text[:60] + "..." if len(s.message_text) > 60 else s.message_text
        lines.append(f"<b>#{s.id}</b> \u2014 {s.hour:02d}:{s.minute:02d} UTC")
        lines.append(f"  <i>{escape(preview)}</i>\n")
    lines.append("Delete with /delschedule [ID]")
    return "\n".join(lines)


def get_delschedule_result(deleted: bool) -> str:
    return "Schedule removed." if deleted else "Schedule not found or not owned by you."


def get_welcome_help() -> str:
    return (
        "<b>Custom Welcome Message</b>\n\n"
        "Format: /welcome [MESSAGE]\n\n"
        "<b>Variables:</b>\n"
        "\u2022 {name} \u2014 User's first name\n"
        "\u2022 {username} \u2014 User's @username\n"
        "\u2022 {group} \u2014 Group name\n\n"
        "Example:\n"
        "/welcome Welcome {name}! Please read the pinned rules.\n\n"
        "Disable with /welcomeoff"
    )


def get_welcome_length_error() -> str:
    return "Welcome message must be under 500 characters."


def get_welcome_success(preview: str) -> str:
    return f"Welcome Message Set\n\n" f"Preview:\n" f"<i>{escape(preview)}</i>\n\n" f"Disable with /welcomeoff"


def get_welcomeoff_result(disabled: bool) -> str:
    return "Custom welcome disabled." if disabled else "No active welcome config found."


def get_analytics_msg(day_stats: dict, week_stats: dict, total: int, top_violators: list) -> str:
    deleted_24h = day_stats.get("DELETED", 0)
    warned_24h = day_stats.get("WARNED", 0)
    banned_24h = day_stats.get("BANNED", 0)
    quarantine_24h = day_stats.get("QUARANTINE", 0)

    deleted_7d = week_stats.get("DELETED", 0)
    warned_7d = week_stats.get("WARNED", 0)
    banned_7d = week_stats.get("BANNED", 0)

    lines = [
        "<b>Moderation Analytics</b>",
        "",
        "<b>Last 24 Hours:</b>",
        f"  Messages Deleted: {deleted_24h}",
        f"  Warnings Issued: {warned_24h}",
        f"  Users Banned: {banned_24h}",
        f"  Quarantine Blocks: {quarantine_24h}",
        "",
        "<b>Last 7 Days:</b>",
        f"  Deleted: {deleted_7d} | Warned: {warned_7d} | Banned: {banned_7d}",
        "",
        f"<b>Total All-Time Actions:</b> {total}",
    ]

    if top_violators:
        lines.extend(
            [
                "",
                "<b>Top Violators (7 Days):</b>",
            ]
        )
        for rank, (username, uid, count) in enumerate(top_violators, 1):
            name = f"@{username}" if username else f"<code>{uid}</code>"
            lines.append(f"  {rank}. {name} \u2014 {count} violations")

    return "\n".join(lines)


def get_audit_log_msg(entries: list) -> str:
    if not entries:
        return "<b>Audit Log</b>\n\nNo moderation actions recorded yet."

    lines = ["<b>Moderation Audit Log</b>", ""]
    action_icons = {"DELETED": "Deleted", "WARNED": "Warned", "BANNED": "Banned", "QUARANTINE": "Restricted"}

    for log in entries:
        action_label = action_icons.get(log.action, log.action)
        name = f"@{log.username}" if log.username else f"ID:{log.user_id}"
        time_str = log.created_at.strftime("%d/%m %H:%M") if log.created_at else "?"
        reason_short = (log.reason[:40] + "...") if log.reason and len(log.reason) > 40 else (log.reason or "N/A")
        lines.append(f"<b>{action_label}</b> | {name} | {time_str}")
        lines.append(f"   <i>{escape(reason_short)}</i>")

    return "\n".join(lines)


def get_antiraid_status_msg(is_active: bool, expiry: str = None) -> str:
    if is_active:
        msg = (
            "<b>Anti-Raid: Active</b>\n\n"
            "All messages from non-admin members will be deleted.\n"
            "New joins will be auto-restricted."
        )
        if expiry:
            msg += f"\n\nExpires: {expiry}"
        msg += "\n\nDisable with /antiraid off"
    else:
        msg = (
            "<b>Anti-Raid: Inactive</b>\n\n"
            "Usage:\n"
            "\u2022 /antiraid on \u2014 Enable lockdown\n"
            "\u2022 /antiraid off \u2014 Disable lockdown\n\n"
            "When active: all new members are auto-muted. "
            "No messages from non-admins for the duration."
        )
    return msg


def get_antiraid_toggle_msg(activated: bool) -> str:
    if activated:
        return (
            "<b>Anti-Raid Lockdown Activated</b>\n\n"
            "All messages from non-admin members will be deleted.\n"
            "New joins will be auto-restricted.\n\n"
            "Disable with /antiraid off"
        )
    return "<b>Anti-Raid Lockdown Deactivated</b>\n\n" "Normal moderation resumed."


# ============================================================
# FORGIVE / RESET MESSAGES
# ============================================================


def get_forgive_admin_error() -> str:
    return "Admin only. Ask a group admin to perform this action."


def get_forgive_id_error() -> str:
    return "Invalid user ID."


def get_forgive_no_target() -> str:
    return "Reply to a user or provide their ID."


def get_forgive_result(success: bool) -> str:
    return "Strikes cleared." if success else "No strikes found for this user."


def get_reset_private_error() -> str:
    return "Use this in the group you want to reset."


def get_reset_admin_error() -> str:
    return "Admin only."


def get_reset_not_configured() -> str:
    return "This group is not configured. Run /setup to begin."


def get_reset_owner_error() -> str:
    return "Only the group owner can reset."


def get_reset_result(success: bool) -> str:
    return "Group data wiped. Run /setup to reconfigure." if success else "Reset failed."


# ============================================================
# SETUP WIZARD MESSAGES
# ============================================================


def get_setup_group_error() -> str:
    return "Add this bot to your group and use /setup in the group chat."


def get_setup_not_admin() -> str:
    return "Only group admins can run /setup."


def get_setup_verify_error() -> str:
    return "Cannot verify admin status. Make sure I'm an admin."


def get_setup_limit_reached(existing_groups: int, max_groups: int, is_pro: bool) -> str:
    msg = f"<b>Group limit reached</b>\n\n" f"You have {existing_groups}/{max_groups} active groups.\n\n"
    if not is_pro:
        msg += "Upgrade to Zenith Pro for up to 5 groups.\n/activate [YOUR_KEY]"
    else:
        msg += "Pro limit: 5 groups. Use /reset in an old group to free up a slot."
    return msg


def get_setup_dm_sent() -> str:
    return "Check your DMs \u2014 I sent the setup wizard!"


def get_setup_dm_failed() -> str:
    return "I can't DM you. Start a private chat with me first."


def get_setup_expired() -> str:
    return "Session expired. Run /setup again in your group."


def get_setup_start_msg(group_name: str, step: int = 1, total_steps: int = 2) -> str:
    return f"<b>Setup: {escape(group_name)}</b>\n" "" f"<b>Step {step}/{total_steps}:</b> Select protection features:"


def get_setup_step2_msg(group_name: str, feature: str) -> str:
    return (
        f"<b>Setup: {escape(group_name)}</b>\n"
        ""
        f"Features: <b>{feature.capitalize()}</b>\n\n"
        f"<b>Step 2/2:</b> Select enforcement strength:"
    )


def get_setup_complete_msg(group_name: str, feature: str, strength: str, is_pro: bool) -> str:
    lines = [
        "<b>Setup Complete</b>",
        "",
        f"Group: {escape(group_name)}",
        f"Features: {feature.capitalize()}",
        f"Strength: {strength.capitalize()}",
        "Status: Active",
    ]
    if is_pro:
        lines += [
            "",
            "<b>Pro Commands:</b>",
            "\u2022 /addword [word] \u2014 Custom word filter",
            "\u2022 /antiraid on/off \u2014 Anti-raid lockdown",
            "\u2022 /analytics \u2014 Moderation stats",
            "\u2022 /schedule HH:MM [msg] \u2014 Scheduled messages",
            "\u2022 /welcome [msg] \u2014 Custom welcome",
            "\u2022 /auditlog \u2014 View audit log",
        ]
    lines += [
        "",
        "<b>Core Commands:</b>",
        "\u2014 /forgive \u2014 Clear user strikes",
        "\u2014 /reset \u2014 Wipe group data",
        "\u2014 /setup \u2014 Reconfigure",
    ]
    return "\n".join(lines)


def get_setup_failed() -> str:
    return "Setup failed. Please try again."


# ============================================================
# AI / CRYPTO GROUP MESSAGES
# ============================================================


def get_ai_ask_help() -> str:
    return "<b>Ask Zenith AI</b>\n\n" "Usage: /ask [your question]\n\n" "Example: /ask What's the weather like today?"


def get_ai_error() -> str:
    return "AI service temporarily unavailable. Please try again in a few moments."


def get_ai_truncation_notice(is_pro: bool = False) -> str:
    if is_pro:
        return ""
    return "\n\nUpgrade to Pro for longer responses."


def get_ai_help_msg(is_pro: bool) -> str:
    lines = [
        "<b>Group Bot Help</b>",
        "",
        "<b>AI Commands:</b>",
        "\u2022 /ask [question] \u2014 Ask AI anything",
        "\u2022 /persona \u2014 View available personas (Pro)",
        "",
        "<b>Crypto Commands:</b>",
        "\u2022 /price [coin] \u2014 Get price info",
        "\u2022 /alert [coin] [above/below] [price] \u2014 Set alert (Pro)",
        "",
        "<b>Flood Protection:</b>",
        "\u2022 Free: 5 commands/min, 15s cooldown",
        "\u2022 Pro: 20 commands/min, 5s cooldown",
    ]
    if is_pro:
        lines += [
            "",
            "<b>Pro Features:</b>",
            "\u2022 Unlimited AI queries",
            "\u2022 All 7 AI personas",
            "\u2022 Deep research",
            "\u2022 Code generator",
            "\u2022 Price alerts",
            "\u2022 Wallet tracking",
        ]
    return "\n".join(lines)


def get_flood_cooldown(name: str, remaining: int) -> str:
    return f"{name}, please wait {remaining}s between commands."


def get_flood_warning(name: str) -> str:
    return f"{name}, you're sending too many commands!"


def get_flood_mute(name: str, duration: int) -> str:
    return f"{name} has been muted for {duration//3600}h due to spam."


def get_flood_kick(name: str) -> str:
    return f"{name} has been removed for repeated spam."


def get_token_not_found(symbol: str) -> str:
    return f"Token <code>{escape(symbol)}</code> not found."


def get_price_card(name: str, symbol: str, price: float, change: float, is_pro: bool, data: dict = None) -> str:
    direction = "Up" if change >= 0 else "Down"
    lines = [
        f"<b>{escape(name)} ({symbol})</b>",
        "",
        f"Price: ${price:,.2f}",
        f"24h: {direction} ({change:+.2f}%)",
    ]
    if is_pro and data:
        mc = data.get("market_cap")
        vol = data.get("total_volume")
        if mc is not None:
            lines.append(f"Market Cap: ${mc:,.0f}")
        if vol is not None:
            lines.append(f"Volume 24h: ${vol:,.0f}")
    return "\n".join(lines)


def get_alert_pro_msg() -> str:
    return (
        "<b>Price Alerts (Pro Only)</b>\n\n"
        "Create price alerts to get notified when tokens hit your target price.\n\n"
        "<b>Pro Benefits:</b>\n"
        "\u2022 Unlimited price alerts\n"
        "\u2022 Wallet tracking\n"
        "\u2022 Portfolio manager\n\n"
        "Contact @admin to upgrade."
    )


def get_alert_redirect() -> str:
    return (
        "<b>Price Alerts</b>\n\n"
        "Use /alert in private chat with @ZenithCryptoBot to create alerts.\n\n"
        "Example: /alert BTC above 100000"
    )


def get_market_overview(btc_data: dict, eth_data: dict, fng: dict = None, is_pro: bool = False) -> str:
    lines = [
        "<b>Market Overview</b>",
        "",
        f"BTC: ${btc_data.get('usd', 0):,.0f} ({btc_data.get('usd_24h_change', 0):+.1f}%)",
        f"ETH: ${eth_data.get('usd', 0):,.0f} ({eth_data.get('usd_24h_change', 0):+.1f}%)",
    ]
    if is_pro and fng:
        fng_val = fng.get("value", 0)
        fng_class = fng.get("classification", "N/A")
        lines.append(f"\nFear & Greed: {fng_val}/100 \u2014 {fng_class}")
    elif fng:
        lines.append("\nFear & Greed: [Pro Required]")
    return "\n".join(lines)


def get_gas_redirect() -> str:
    return "<b>Gas Tracker</b>\n\nUse /gas in private chat with @ZenithCryptoBot for gas prices."


# ============================================================
# VIOLATION NOTIFICATION
# ============================================================


def get_violation_notification(group_name: str, user_name: str, user_id: int, reason: str) -> str:
    return (
        f"<b>Violation Detected</b>\n"
        ""
        f"Group: <code>{escape(group_name)}</code>\n"
        f"User: {escape(user_name)} (<code>{user_id}</code>)\n"
        f"Reason: {escape(reason)}"
    )

def get_features_card(is_pro: bool) -> str:
    if is_pro:
        return (
            "🚀 <b>Zenith Group Shield PRO Active</b>\n\n"
            "▫️ ✅ <b>Basic Spam Filter</b> — Block basic Telegram spam\n"
            "▫️ ✅ <b>Member Verification</b> — Require new users to click buttons\n"
            "▫️ ✅ <b>Custom Filters</b> — Build an impenetrable auto-delete filter\n"
            "▫️ ✅ <b>Anti-Raid Lockdown</b> — 1-click emergency lockdown during coordinated attacks\n"
            "▫️ ✅ <b>Analytics Dashboard</b> — Track top violators and moderation metrics\n"
            "▫️ ✅ <b>Automated Schedules</b> — Program recurring daily community broadcasts\n"
            "▫️ ✅ <b>Welcome Protocols</b> — Design customized new member welcome messages\n"
            "▫️ ✅ <b>Forensic Audit Log</b> — Track exactly which admin did what\n\n"
            "<i>Your PRO account is fully unlocked. Your communities are secure.</i>"
        )
    else:
        return (
            "🚀 <b>Group Shield Modules</b>\n\n"
            "▫️ 🛡️ <b>Basic Spam Filter</b> — Block basic Telegram spam\n"
            "▫️ 👮 <b>Member Verification</b> — Require new users to click buttons\n\n"
            "🔒 <b>PRO EXCLUSIVE CAPABILITIES</b>\n"
            "▫️ 🚫 <b>Custom Filters</b> — Build an impenetrable auto-delete filter\n"
            "▫️ 🚨 <b>Anti-Raid Lockdown</b> — 1-click emergency lockdown during coordinated attacks\n"
            "▫️ 📊 <b>Analytics Dashboard</b> — Track top violators and moderation metrics\n"
            "▫️ ⏰ <b>Automated Schedules</b> — Program recurring daily community broadcasts\n"
            "▫️ 👋 <b>Welcome Protocols</b> — Design customized new member welcome messages\n"
            "▫️ 📜 <b>Forensic Audit Log</b> — Track exactly which admin did what\n\n"
            "⭐ <i>Upgrade to Pro Shield (/activate) to unlock enterprise community protection.</i>"
        )

def get_help_card() -> str:
    return (
        "❓ <b>Command Directory</b>\n\n"
        "🛡️ <b>Security & Filters</b>\n"
        "▫️ <code>/antiraid on/off</code> - Emergency group lockdown\n"
        "▫️ <code>/addword [word]</code> - Add word to auto-delete filter\n"
        "▫️ <code>/delword [word]</code> - Remove word from filter\n"
        "▫️ <code>/wordlist</code> - View all active filters\n\n"
        "🤖 <b>Automation</b>\n"
        "▫️ <code>/schedule HH:MM [msg]</code> - Set a daily recurring broadcast\n"
        "▫️ <code>/delschedule [id]</code> - Remove a scheduled broadcast\n"
        "▫️ <code>/schedules</code> - View all schedules\n"
        "▫️ <code>/welcome [msg]</code> - Set a custom welcome message\n"
        "▫️ <code>/welcomeoff</code> - Disable custom welcome\n\n"
        "📊 <b>Telemetry</b>\n"
        "▫️ <code>/analytics</code> - View moderation analytics\n"
        "▫️ <code>/auditlog [count]</code> - View recent admin actions\n"
        "▫️ <code>/setup</code> - Re-run the interactive setup wizard\n"
    )
