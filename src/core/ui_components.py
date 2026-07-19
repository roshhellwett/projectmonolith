"""
Shared UI primitives used across all Zenith bots.

Provides consistent components for:
- Back/home buttons
- Pro upgrade prompts
- Error displays
- Loading indicators
- Confirmation dialogs
- Pagination
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID


# ==========================================================
# Navigation Buttons
# ==========================================================
def back_button(callback_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Standard back button. Every screen should have one."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data=callback_data)]])


def home_button(callback_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Home button for deep navigation."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data=callback_data)]])


def back_and_home(back_data: str, home_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Combined back + home navigation."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀️ Back", callback_data=back_data),
            InlineKeyboardButton("🏠 Home", callback_data=home_data),
        ]
    ])


# ==========================================================
# Pro Upgrade Prompts
# ==========================================================
def pro_upgrade_keyboard(back_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Keyboard with upgrade link + back button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Get Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
        [InlineKeyboardButton("◀️ Back", callback_data=back_data)],
    ])


def pro_feature_locked_msg(feature_name: str) -> str:
    """Consistent locked feature message."""
    return (
        f"🔒 <b>{feature_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"This feature requires <b>Zenith Pro</b>.\n\n"
        f"💎 Upgrade to unlock:\n"
        f"• {feature_name}\n"
        f"• All premium features across all bots\n\n"
        f"Use <code>/activate YOUR-KEY</code> to activate."
    )


# ==========================================================
# Error Displays
# ==========================================================
def error_msg(title: str, detail: str = "", suggestion: str = "") -> str:
    """Consistent error message format."""
    text = f"❌ <b>{title}</b>\n"
    if detail:
        text += f"\n{detail}\n"
    if suggestion:
        text += f"\n💡 <i>{suggestion}</i>"
    return text


def not_found_msg(item_type: str = "Item") -> str:
    """Generic not-found message."""
    return error_msg(
        f"{item_type} Not Found",
        f"The requested {item_type.lower()} could not be found.",
        "It may have been deleted or the ID is incorrect.",
    )


def empty_list_msg(item_type: str, add_command: str = "") -> str:
    """Generic empty list message."""
    text = (
        f"📭 <b>No {item_type} Found</b>\n\n"
        f"You don't have any {item_type.lower()} yet."
    )
    if add_command:
        text += f"\n\nUse <code>{add_command}</code> to get started."
    return text


# ==========================================================
# Loading Indicators
# ==========================================================
def loading_msg(action: str = "Processing") -> str:
    """Standard loading message."""
    return f"⏳ <i>{action}...</i>"


def scanning_msg(subject: str = "") -> str:
    """Scanning/analyzing loading message."""
    if subject:
        return f"🔍 <i>Analyzing {subject}...</i>"
    return "🔍 <i>Scanning...</i>"


# ==========================================================
# Confirmation Dialogs
# ==========================================================
def confirm_keyboard(
    confirm_data: str,
    cancel_data: str = "ui_main_menu",
    confirm_text: str = "✅ Confirm",
    cancel_text: str = "❌ Cancel",
) -> InlineKeyboardMarkup:
    """Standard confirmation dialog buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(confirm_text, callback_data=confirm_data)],
        [InlineKeyboardButton(cancel_text, callback_data=cancel_data)],
    ])


def confirm_msg(action: str, detail: str = "") -> str:
    """Standard confirmation prompt."""
    text = f"⚠️ <b>Confirm: {action}</b>\n"
    if detail:
        text += f"\n{detail}\n"
    text += "\nThis action cannot be undone."
    return text


# ==========================================================
# Pagination
# ==========================================================
def paginate_items(
    items: list,
    page: int,
    per_page: int = 8,
    item_callback_prefix: str = "item_",
    nav_callback_prefix: str = "page_",
    back_data: str = "ui_main_menu",
) -> InlineKeyboardMarkup:
    """
    Create a paginated inline keyboard from a list of (label, id) tuples.

    Args:
        items: List of (display_label, callback_id) tuples
        page: Current page (0-indexed)
        per_page: Items per page
        item_callback_prefix: Prefix for item callback data
        nav_callback_prefix: Prefix for navigation callback data
        back_data: Callback data for back button
    """
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))

    start = page * per_page
    end = min(start + per_page, len(items))
    page_items = items[start:end]

    keyboard = []
    for label, item_id in page_items:
        keyboard.append([InlineKeyboardButton(label, callback_data=f"{item_callback_prefix}{item_id}")])

    # Navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"{nav_callback_prefix}{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"{nav_callback_prefix}{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    # Back button
    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data=back_data)])

    return InlineKeyboardMarkup(keyboard)


# ==========================================================
# Status Indicators
# ==========================================================
def tier_badge(tier_name: str, days_left: int = 0) -> str:
    """Render a tier badge string."""
    if tier_name == "owner":
        return "👑 Owner"
    elif tier_name == "pro":
        return f"💎 Pro ({days_left}d left)"
    return "📊 Free"


def status_indicator(is_active: bool, label: str = "") -> str:
    """Green/red status indicator."""
    icon = "✅" if is_active else "⚠️"
    status = "Active" if is_active else "Inactive"
    if label:
        return f"{icon} {label}: {status}"
    return f"{icon} {status}"


def divider(char: str = "━", length: int = 20) -> str:
    """Visual divider line."""
    return char * length


def progress_bar(
    current: int, total: int, length: int = 15, filled: str = "█", empty: str = "░"
) -> str:
    """Render a progress bar."""
    if total <= 0:
        pct = 0
        fill = 0
    else:
        pct = int(100 * current / total)
        fill = int(length * current / total)
    bar = filled * fill + empty * (length - fill)
    return f"{bar} {pct}%"
