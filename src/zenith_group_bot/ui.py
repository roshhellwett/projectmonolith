from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID


def get_admin_dashboard(is_pro: bool, groups: list, usage: dict = None) -> InlineKeyboardMarkup:
    group_limit = 5 if is_pro else 1
    group_count = len(groups)

    rows = [
        [
            InlineKeyboardButton(
                f"{'💎' if is_pro else '🆓'} {'PRO ACTIVE' if is_pro else 'FREE TIER'}", callback_data="grp_status"
            )
        ],
        [InlineKeyboardButton(f"📋 My Groups ({group_count}/{group_limit})", callback_data="grp_list")],
    ]

    if is_pro:
        rows.extend(
            [
                [
                    InlineKeyboardButton("📊 Analytics", callback_data="grp_analytics_pick"),
                    InlineKeyboardButton("📜 Audit Log", callback_data="grp_audit_pick"),
                ],
                [
                    InlineKeyboardButton("📝 Custom Words", callback_data="grp_words_help"),
                    InlineKeyboardButton("⏰ Schedules", callback_data="grp_schedule_help"),
                ],
                [InlineKeyboardButton("👋 Welcome", callback_data="grp_welcome_help")],
            ]
        )
    else:
        rows.append([InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")])
    return InlineKeyboardMarkup(rows)


def get_group_picker(groups: list, action_prefix: str, is_pro: bool = False) -> InlineKeyboardMarkup:
    rows = []

    for g in groups[:5]:
        name = g.group_name or f"Group {g.chat_id}"
        status = "✅" if g.is_active else "⏸️"
        members = getattr(g, "member_count", "N/A")

        label = f"{status} {name}"
        if members != "N/A":
            label += f" ({members}👥)"

        rows.append([InlineKeyboardButton(label, callback_data=f"{action_prefix}_{g.chat_id}")])

    if not is_pro and len(groups) >= 1:
        rows.append([InlineKeyboardButton("💎 Upgrade to Add More Groups", url=f"tg://user?id={ADMIN_USER_ID}")])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="grp_main_menu")])
    return InlineKeyboardMarkup(rows)


def get_group_settings_keyboard(chat_id: int, group_settings: dict = None) -> InlineKeyboardMarkup:
    """Get settings keyboard for a specific group."""
    anti_spam = group_settings.get("anti_spam", True) if group_settings else True
    anti_abuse = group_settings.get("anti_abuse", True) if group_settings else True
    flood_control = group_settings.get("flood_control", True) if group_settings else True

    rows = [
        [
            InlineKeyboardButton(
                f"🤖 Anti-Spam {'✅' if anti_spam else '❌'}", callback_data=f"grp_toggle_spam_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔞 Anti-Abuse {'✅' if anti_abuse else '❌'}", callback_data=f"grp_toggle_abuse_{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🌊 Flood Control {'✅' if flood_control else '❌'}", callback_data=f"grp_toggle_flood_{chat_id}"
            ),
        ],
        [InlineKeyboardButton("⚙️ Configure", callback_data=f"grp_config_{chat_id}")],
        [InlineKeyboardButton("🔙 Back to Groups", callback_data="grp_list")],
    ]

    return InlineKeyboardMarkup(rows)


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="grp_main_menu")]])


def get_confirm_forgive(user_id: int, user_name: str = None, strikes: int = 0) -> tuple:
    """Get confirmation message and keyboard for forgiving strikes."""
    name = user_name or f"User {user_id}"

    message = (
        f"⚠️ <b>Confirm Forgive?</b>\n\n"
        f"<b>User:</b> {name}\n"
        f"<b>Current Strikes:</b> {strikes}\n\n"
        f"This will clear all strikes for this user."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Yes, Forgive", callback_data=f"grp_forgive_{user_id}")],
            [InlineKeyboardButton("✖ Cancel", callback_data="grp_list")],
        ]
    )

    return message, keyboard


def get_confirm_reset(group_name: str = None) -> tuple:
    """Get confirmation for resetting group settings."""
    name = group_name or "this group"

    message = (
        f"🚨 <b>⚠️ RESET {name.upper()}?</b>\n\n"
        f"This will:\n"
        f"• Delete all group settings\n"
        f"• Remove all custom words\n"
        f"• Clear all scheduled messages\n"
        f"• Clear all moderation history\n\n"
        f"<b>This action cannot be undone!</b>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚨 Yes, Reset Everything", callback_data="grp_reset_confirm")],
            [InlineKeyboardButton("✖ Cancel", callback_data="grp_list")],
        ]
    )

    return message, keyboard


def get_confirm_add_word(word: str) -> tuple:
    """Get confirmation for adding a custom word."""
    message = (
        f"⚠️ <b>Add Banned Word?</b>\n\n"
        f"<b>Word:</b> <code>{word}</code>\n\n"
        f"This word will be automatically deleted when posted."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Add Word", callback_data=f"grp_addword_confirm_{word}")],
            [InlineKeyboardButton("✖ Cancel", callback_data="grp_words_help")],
        ]
    )

    return message, keyboard


def get_confirm_delete_word(word: str) -> tuple:
    """Get confirmation for deleting a custom word."""
    message = (
        f"⚠️ <b>Remove Banned Word?</b>\n\n"
        f"<b>Word:</b> <code>{word}</code>\n\n"
        f"This word will no longer be filtered."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Remove Word", callback_data=f"grp_delword_confirm_{word}")],
            [InlineKeyboardButton("✖ Cancel", callback_data="grp_words_help")],
        ]
    )

    return message, keyboard


def get_word_list_msg(words: list, group_name: str = None) -> str:
    """Format custom word list."""
    name = group_name or "this group"

    if not words:
        return (
            f"📝 <b>Custom Words - {name}</b>\n\n"
            f"No custom words added yet.\n\n"
            f"Use /addword [word] to add filters."
        )

    message = f"📝 <b>Custom Words - {name}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, word in enumerate(words[:20], 1):
        message += f"{i}. <code>{word}</code>\n"

    if len(words) > 20:
        message += f"\n<i>...and {len(words) - 20} more</i>"

    message += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"<i>Total: {len(words)} words</i>"

    return message


def get_word_limit_msg(current: int, limit: int) -> str:
    """Message when word limit is reached."""
    return (
        f"🚫 <b>Word Limit Reached</b>\n\n"
        f"You've added {current}/{limit} custom words.\n\n"
        f"Remove some words to add more, or upgrade to PRO for 200 words."
    )


def get_schedule_list_msg(schedules: list, group_name: str = None) -> str:
    """Format scheduled messages list."""
    name = group_name or "this group"

    if not schedules:
        return (
            f"⏰ <b>Scheduled Messages - {name}</b>\n\n"
            f"No scheduled messages.\n\n"
            f"Use /schedule HH:MM [message] to create one."
        )

    message = f"⏰ <b>Scheduled Messages - {name}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, sched in enumerate(schedules[:10], 1):
        time = sched.get("time", "N/A")
        msg_preview = sched.get("message", "")[:30]
        if len(sched.get("message", "")) > 30:
            msg_preview += "..."

        message += f"{i}. 🕐 {time}\n   📝 {msg_preview}\n\n"

    message += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"<i>Total: {len(schedules)} scheduled messages</i>"

    return message


def get_confirm_schedule(time: str, message: str) -> tuple:
    """Get confirmation for scheduling a message."""
    message = f"⏰ <b>Confirm Schedule?</b>\n\n" f"<b>Time (UTC):</b> {time}\n" f"<b>Message:</b> {message[:100]}..."

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"grp_schedule_confirm_{time}")],
            [InlineKeyboardButton("✖ Cancel", callback_data="grp_schedule_help")],
        ]
    )

    return message, keyboard


def get_analytics_card(analytics: dict, period: str = "24h") -> str:
    """Format analytics card."""
    total_actions = analytics.get("total_actions", 0)
    deleted_count = analytics.get("deleted_messages", 0)
    banned_count = analytics.get("banned_users", 0)
    muted_count = analytics.get("muted_users", 0)

    message = f"""
<b>📊 Moderation Analytics - {period}</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>📈 Total Actions:</b> {total_actions}
<b>🗑️ Messages Deleted:</b> {deleted_count}
<b>🚫 Users Banned:</b> {banned_count}
<b>🔇 Users Muted:</b> {muted_count}

<b>📊 Action Breakdown:</b>
"""

    categories = analytics.get("categories", {})
    for cat, count in categories.items():
        if count > 0:
            message += f"• {cat}: {count}\n"

    message += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

    top_violators = analytics.get("top_violators", [])
    if top_violators:
        message += "<b>🔴 Top Violators:</b>\n"
        for i, (user, strikes) in enumerate(top_violators[:3], 1):
            message += f"{i}. {user}: {strikes} strikes\n"

    return message


def get_audit_log_msg(entries: list) -> str:
    """Format audit log."""
    if not entries:
        return "📜 <b>Audit Log</b>\n\nNo recent actions."

    message = "📜 <b>Recent Moderation Actions</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for entry in entries[:15]:
        action = entry.get("action", "Unknown")
        user = entry.get("user", "N/A")
        reason = entry.get("reason", "")[:30]
        timestamp = entry.get("timestamp", "")

        emoji = {
            "delete": "🗑️",
            "ban": "🚫",
            "mute": "🔇",
            "warn": "⚠️",
            "unmute": "🔊",
            "unban": "✅",
        }.get(action, "❓")

        message += f"{emoji} <b>{action.upper()}</b>\n"
        message += f"   👤 {user}\n"
        if reason:
            message += f"   📝 {reason}...\n"
        message += f"   🕐 {timestamp}\n\n"

    return message


def get_antiraid_status(is_active: bool, expiry: str = None) -> str:
    """Format anti-raid shield status."""
    status = "🛡️ <b>Anti-Raid Shield: ACTIVE</b>"
    if expiry:
        status += f"\n<i>Expires: {expiry}</i>"

    if not is_active:
        status = "🛡️ <b>Anti-Raid Shield: Inactive</b>"

    status += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    status += "When active:\n"
    status += "• New members are muted\n"
    status += "• Links and media restricted\n"
    status += "• Anti-raid mode auto-expires after 30 minutes"

    return status


def get_welcome_msg(name: str, is_pro: bool, days_left: int = 0, groups_count: int = 0) -> str:
    """Welcome message for group bot."""
    tier = "💎 PRO" if is_pro else "🆓 Free"
    group_limit = 5 if is_pro else 1

    message = f"""
<b>🛡️ Zenith Group Moderator</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👋 Welcome, <b>{name}</b>!

<b>Tier:</b> {tier}
<b>Groups:</b> {groups_count}/{group_limit}
"""

    if is_pro:
        message += f"\n<i>Pro expires in {days_left} days</i>"

    message += """
━━━━━━━━━━━━━━━━━━━━━━━━

<b>Setup in your group:</b>
1. Add bot to group
2. Make it admin
3. Use /setup to configure

<b>Commands:</b>
• /setup - Configure moderation
• /forgive - Remove user strikes
• /analytics - View stats
• /auditlog - View actions
"""

    if not is_pro:
        message += """
💎 <b>Upgrade to PRO:</b>
• Up to 5 groups
• 200 custom words
• Anti-raid shield
• Scheduled messages
• Custom welcome
"""

    return message


def get_pro_feature_msg(feature: str) -> tuple:
    """Message for pro-only features."""
    messages = {
        "custom_words": (
            "📝 <b>Custom Words (Pro)</b>\n\n"
            "Add custom banned words and phrases to filter specific content.\n\n"
            "Use /addword [word] to add."
        ),
        "schedules": (
            "⏰ <b>Scheduled Messages (Pro)</b>\n\n"
            "Schedule daily recurring messages in your group.\n\n"
            "Use /schedule HH:MM [message] to create."
        ),
        "welcome": (
            "👋 <b>Custom Welcome (Pro)</b>\n\n"
            "Set a personalized welcome message for new members.\n\n"
            "Use /welcome [message] to set.\n"
            "Use {name}, {username}, {group} as variables."
        ),
        "analytics": (
            "📊 <b>Analytics (Pro)</b>\n\n" "View detailed moderation statistics.\n\n" "Use /analytics to view."
        ),
        "antiraid": (
            "🛡️ <b>Anti-Raid Shield (Pro)</b>\n\n"
            "Enable instant lockdown when raid is detected.\n\n"
            "Use /antiraid on to enable."
        ),
    }

    message = messages.get(feature, "Pro feature")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
            [InlineKeyboardButton("🔙 Back", callback_data="grp_main_menu")],
        ]
    )

    return message, keyboard


def get_limit_reached_msg(feature: str, current: int, limit: int) -> str:
    """Message when limit is reached."""
    return (
        f"🚫 <b>Limit Reached: {feature}</b>\n\n"
        f"You've reached {current}/{limit}.\n\n"
        "Upgrade to PRO for higher limits."
    )
