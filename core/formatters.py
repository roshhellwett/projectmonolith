from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import math


def format_card(
    title: str,
    body: str,
    footer: Optional[str] = None,
    border_color: str = "🟦"
) -> str:
    """
    Format a styled card message.
    
    Args:
        title: Card title (bold)
        body: Main content
        footer: Optional footer text
        border_color: Emoji for border decoration
    
    Returns:
        Formatted HTML card
    """
    lines = [
        f"<b>{border_color} {title}</b>",
        "━" * 20,
        body,
    ]
    
    if footer:
        lines.extend([
            "━" * 20,
            f"<i>{footer}</i>"
        ])
    
    return "\n".join(lines)


def format_list_item(
    number: int,
    text: str,
    icon: str = "•",
    max_length: int = 60
) -> str:
    """Format a numbered list item."""
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    return f"{number}. {icon} {text}"


def format_progress_bar(
    current: int,
    total: int,
    length: int = 15,
    filled_char: str = "█",
    empty_char: str = "░"
) -> str:
    """Create a text-based progress bar."""
    if total <= 0:
        percentage = 0
        filled = 0
    else:
        percentage = int(100 * current / total)
        filled = int(length * current / total)
    
    bar = filled_char * filled + empty_char * (length - filled)
    return f"{bar} {percentage}%"


def format_countdown(seconds: int, style: str = "compact") -> str:
    """
    Format a countdown timer.
    
    Styles:
    - compact: "5m 30s"
    - detailed: "5 minutes 30 seconds"
    - emoji: "⏰ 5m 30s"
    """
    if seconds < 0:
        seconds = 0
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if style == "detailed":
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if secs > 0 or not parts:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")
        return " ".join(parts)
    
    elif style == "emoji":
        if days > 0:
            return f"⏰ {days}d {hours}h"
        elif hours > 0:
            return f"⏰ {hours}h {minutes}m"
        elif minutes > 0:
            return f"⏰ {minutes}m {secs}s"
        else:
            return f"⏰ {secs}s"
    
    else:  # compact
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


def format_usage_meter(
    current: int,
    limit: int,
    label: str = "Usage",
    show_numbers: bool = True
) -> str:
    """Format a usage meter with visual bar."""
    bar = format_progress_bar(current, limit)
    
    if show_numbers:
        return f"<b>{label}</b>\n\n{bar}\n<i>{current}/{limit}</i>"
    else:
        return f"<b>{label}</b>\n\n{bar}"


def format_price_change(
    change: float,
    percentage: Optional[float] = None,
    show_arrow: bool = True
) -> str:
    """
    Format price change with color and arrow.
    
    Args:
        change: Absolute change value
        percentage: Optional percentage change
        show_arrow: Whether to show arrow emoji
    
    Returns:
        Formatted string like "+$500 (+" or "-5.2%)$500 (-5.2%)"
    """
    emoji = "📈" if change >= 0 else "📉"
    sign = "+" if change >= 0 else ""
    
    formatted_change = f"${abs(change):,.2f}"
    
    result = f"{emoji} {sign}{formatted_change}"
    
    if percentage is not None:
        pct_sign = "+" if percentage >= 0 else ""
        result += f" ({pct_sign}{percentage:.2f}%)"
    elif show_arrow:
        result = f"{emoji} {result}"
    
    return result


def format_pnl(
    pnl: float,
    percentage: Optional[float] = None,
    show_color: bool = True
) -> str:
    """
    Format profit/loss display.
    
    Args:
        pnl: PnL value (positive = profit, negative = loss)
        percentage: Optional percentage
        show_color: Use emoji colors
    
    Returns:
        Formatted PnL string
    """
    if show_color:
        emoji = "🟢" if pnl >= 0 else "🔴"
    else:
        emoji = ""
    
    sign = "+" if pnl >= 0 else ""
    formatted = f"{sign}${pnl:,.2f}"
    
    if percentage is not None:
        pct_sign = "+" if percentage >= 0 else ""
        return f"{emoji} {formatted} ({pct_sign}{percentage:.2f}%)"
    
    return f"{emoji} {formatted}"


def format_time_remaining(expires_at: datetime) -> str:
    """Format time remaining until a datetime."""
    now = datetime.now(expires_at.tzinfo)
    delta = expires_at - now
    
    if delta.total_seconds() <= 0:
        return "Expired"
    
    seconds = int(delta.total_seconds())
    return format_countdown(seconds, "emoji")


def format_datetime(dt: datetime, format_str: str = "default") -> str:
    """Format a datetime for display."""
    if dt is None:
        return "N/A"
    
    if format_str == "default":
        return dt.strftime("%d %b %Y %H:%M UTC")
    elif format_str == "date_only":
        return dt.strftime("%d %b %Y")
    elif format_str == "time_only":
        return dt.strftime("%H:%M UTC")
    elif format_str == "full":
        return dt.strftime("%d %b %Y %H:%M:%S UTC")
    else:
        return dt.strftime(format_str)


def format_address(
    address: str,
    start_chars: int = 6,
    end_chars: int = 4,
    separator: str = "..."
) -> str:
    """Format an address with ellipsis in the middle."""
    if not address or len(address) < start_chars + end_chars:
        return address
    
    return f"{address[:start_chars]}{separator}{address[-end_chars:]}"


def format_large_number(num: float, precision: int = 2) -> str:
    """Format large numbers with K, M, B suffixes."""
    if num is None:
        return "N/A"
    
    abs_num = abs(num)
    sign = "-" if num < 0 else ""
    
    if abs_num >= 1_000_000_000:
        return f"{sign}{abs_num/1_000_000_000:.{precision}f}B"
    elif abs_num >= 1_000_000:
        return f"{sign}{abs_num/1_000_000:.{precision}f}M"
    elif abs_num >= 1_000:
        return f"{sign}{abs_num/1_000:.{precision}f}K"
    else:
        return f"{sign}{abs_num:.{precision}f}"


def format_telegram_user(
    user_id: int,
    first_name: Optional[str] = None,
    username: Optional[str] = None
) -> str:
    """Format a Telegram user mention."""
    if username:
        return f"@{username}"
    elif first_name:
        return f"<a href=\"tg://user?id={user_id}\">{first_name}</a>"
    else:
        return f"<code>{user_id}</code>"


def format_divider(char: str = "━", length: int = 20) -> str:
    """Create a horizontal divider."""
    return char * length


def format_section(title: str, content: str, emoji: str = "") -> str:
    """Format a section with title and content."""
    prefix = f"{emoji} " if emoji else ""
    return f"<b>{prefix}{title}</b>\n\n{content}"


def format_key_value(
    key: str,
    value: str,
    key_width: int = 15,
    justify: bool = True
) -> str:
    """Format a key-value pair."""
    if justify:
        return f"{key:<{key_width}} : {value}"
    else:
        return f"<b>{key}</b>: {value}"


def format_bullet_list(
    items: List[str],
    emoji: str = "•",
    max_items: Optional[int] = None
) -> str:
    """Format a bullet list."""
    if max_items:
        items = items[:max_items]
    
    return "\n".join(f"{emoji} {item}" for item in items)


def format_numbered_list(
    items: List[str],
    start: int = 1,
    max_items: Optional[int] = None
) -> str:
    """Format a numbered list."""
    if max_items:
        items = items[:max_items]
    
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start))


def format_analytics_summary(
    total_actions: int,
    top_category: str,
    top_user: str,
    period: str = "24h"
) -> str:
    """Format an analytics summary card."""
    return f"""📊 <b>Moderation Summary ({period})</b>

<b>Total Actions:</b> {total_actions}
<b>Top Category:</b> {top_category}
<b>Top Violator:</b> {top_user}"""


def format_error_hint(suggestion: str) -> str:
    """Format a helpful hint for errors."""
    return f"<i>💡 {suggestion}</i>"


def format_feature_locked(
    feature: str,
    upgrade_cta: str = "Upgrade to PRO"
) -> str:
    """Format a feature locked message."""
    return f"""🔒 <b>Pro Feature: {feature}</b>

{upgrade_cta} to unlock this feature.

Use /activate [YOUR_KEY] to upgrade."""


def format_limit_reached(
    feature: str,
    current: int,
    limit: int,
    upgrade_benefit: str = "unlimited"
) -> str:
    """Format a limit reached message."""
    return f"""🚫 <b>Limit Reached: {feature}</b>

<b>Current:</b> {current}/{limit}
<b>Upgrade to PRO:</b> {upgrade_benefit}

Use /activate [YOUR_KEY] to upgrade."""


def format_already_done(
    action: str,
    details: str = ""
) -> str:
    """Format an 'already done' message."""
    msg = f"ℹ️ <b>Already {action}</b>"
    if details:
        msg += f"\n\n{details}"
    return msg


def format_success(
    action: str,
    details: Optional[str] = None,
    emoji: str = "✅"
) -> str:
    """Format a success message."""
    msg = f"<b>{emoji} {action}</b>"
    if details:
        msg += f"\n\n{details}"
    return msg


def format_warning(
    message: str,
    suggestion: Optional[str] = None
) -> str:
    """Format a warning message."""
    msg = f"⚠️ <b>Warning</b>\n\n{message}"
    if suggestion:
        msg += f"\n\n{format_error_hint(suggestion)}"
    return msg


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
