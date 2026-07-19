"""
Shared UI primitives used across all Zenith bots.

Provides precision-crafted components for:
- Back/home buttons with clean navigation ergonomics
- Pro upgrade prompts with luxury aesthetic
- Error displays and alert boxes
- Loading indicators and animated stage strings
- Confirmation dialogs
- Pagination controls
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID
from core.formatters import format_alert, format_divider, format_header, format_progress_bar, format_status_pill


# ==========================================================
# Navigation Buttons
# ==========================================================
def back_button(callback_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Standard back button. Every screen should have one."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Dashboard", callback_data=callback_data)]])


def home_button(callback_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Home button for deep navigation."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Dashboard", callback_data=callback_data)]])


def back_and_home(back_data: str, home_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Combined back + home navigation."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("« Back", callback_data=back_data),
            InlineKeyboardButton("🏠 Home", callback_data=home_data),
        ]
    ])


# ==========================================================
# Pro Upgrade Prompts
# ==========================================================
def pro_upgrade_keyboard(back_data: str = "ui_main_menu") -> InlineKeyboardMarkup:
    """Keyboard with upgrade link + back button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Unlock Pro Access", url=f"tg://user?id={ADMIN_USER_ID}")],
        [InlineKeyboardButton("🔑 Activate License Key", callback_data="ui_activate_help")],
        [InlineKeyboardButton("« Back", callback_data=back_data)],
    ])


def pro_feature_locked_msg(feature_name: str) -> str:
    """Consistent locked feature message with God-Level UI hierarchy."""
    return (
        f"🔒 <b>RESTRICTED FEATURE: {feature_name.upper()}</b>\n"
        f"{format_divider('⎯', 25)}\n\n"
        f"This capability is reserved exclusively for <b>Zenith Pro</b> license holders.\n\n"
        f"<b>💎 Pro Subscription Benefits:</b>\n"
        f"  ▫️ Instant access to <b>{feature_name}</b>\n"
        f"  ▫️ Real-time on-chain & smart money intelligence\n"
        f"  ▫️ Full GoPlus security scans without redactions\n"
        f"  ▫️ All 6 AI Personas + 70B Versatile/Deep-Seek Models\n"
        f"  ▫️ Automated group anti-raid protection & 200 custom filters\n\n"
        f"<i>To activate your membership, contact @roshhellwett or use <code>/activate YOUR-KEY</code>.</i>"
    )


# ==========================================================
# Error Displays
# ==========================================================
def error_msg(title: str, detail: str = "", suggestion: str = "") -> str:
    """Consistent error message format using format_alert."""
    text = f"❌ <b>{title.upper()}</b>\n{format_divider('─', 22)}"
    if detail:
        text += f"\n{detail}\n"
    if suggestion:
        text += f"\n💡 <i>Recommendation: {suggestion}</i>"
    return text


def not_found_msg(item_type: str = "Item") -> str:
    """Generic not-found message."""
    return error_msg(
        f"{item_type} Not Found",
        f"The requested {item_type.lower()} could not be located in your active workspace.",
        "Verify the ID or ensure it has not been previously removed.",
    )


def empty_list_msg(item_type: str, add_command: str = "") -> str:
    """Generic empty list message with minimal aesthetic."""
    text = (
        f"📭 <b>NO {item_type.upper()} FOUND</b>\n"
        f"{format_divider('⎯', 22)}\n\n"
        f"Your {item_type.lower()} registry is currently empty."
    )
    if add_command:
        text += f"\n\n⚡ <i>Initialize using <code>{add_command}</code> to get started.</i>"
    return text


# ==========================================================
# Loading Indicators
# ==========================================================
def loading_msg(action: str = "Processing request") -> str:
    """Standard loading message with modern aesthetic."""
    return f"⚡ <b>ZENITH CORE</b> » <i>{action}...</i>"


def scanning_msg(subject: str = "") -> str:
    """Scanning/analyzing loading message."""
    if subject:
        return f"🔍 <b>ANALYSIS IN PROGRESS</b> » <i>Scanning {subject}...</i>"
    return "🔍 <b>SYSTEM SCAN</b> » <i>Querying network matrices...</i>"


# ==========================================================
# Confirmation Dialogs
# ==========================================================
def confirm_keyboard(
    confirm_data: str,
    cancel_data: str = "ui_main_menu",
    confirm_text: str = "✅ Confirm Action",
    cancel_text: str = "✕ Cancel",
) -> InlineKeyboardMarkup:
    """Standard confirmation dialog buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(confirm_text, callback_data=confirm_data)],
        [InlineKeyboardButton(cancel_text, callback_data=cancel_data)],
    ])


def confirm_msg(action: str, detail: str = "") -> str:
    """Standard confirmation prompt with precision aesthetic."""
    text = (
        f"⚠️ <b>CONFIRMATION REQUIRED</b>\n"
        f"{format_divider('⎯', 24)}\n\n"
        f"<b>Action:</b> {action}"
    )
    if detail:
        text += f"\n<b>Detail:</b> {detail}"
    text += "\n\n<i>Note: This operation cannot be undone once executed.</i>"
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
    """Create a paginated inline keyboard from a list of (label, id) tuples with precision navigation."""
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
        nav_row.append(InlineKeyboardButton("« Prev", callback_data=f"{nav_callback_prefix}{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"• {page + 1}/{total_pages} •", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next »", callback_data=f"{nav_callback_prefix}{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    # Back button
    keyboard.append([InlineKeyboardButton("« Back to Dashboard", callback_data=back_data)])

    return InlineKeyboardMarkup(keyboard)


# ==========================================================
# Status Indicators
# ==========================================================
def tier_badge(tier_name: str, days_left: int = 0) -> str:
    """Render a tier badge string."""
    if tier_name == "owner":
        return "👑 OWNER TIER"
    elif tier_name == "pro":
        return f"💎 PRO TIER ({days_left}d left)"
    return "⚪ FREE TIER"


def status_indicator(is_active: bool, label: str = "") -> str:
    """Green/red status indicator."""
    return format_status_pill("🟢 ACTIVE" if is_active else "🔴 INACTIVE", label)


def divider(char: str = "⎯", length: int = 24) -> str:
    """Visual divider line."""
    return format_divider(char, length)


def progress_bar(
    current: int, total: int, length: int = 15, filled: str = "▰", empty: str = "▱"
) -> str:
    """Render a progress bar."""
    return format_progress_bar(current, total, length, filled, empty)

