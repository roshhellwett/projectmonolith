"""
Zenith God-Level UI Formatter Engine.
Provides precision-crafted typographic hierarchy, minimalist layout primitives, and visual polish across all bots.
"""


def format_progress_bar(
    current: int, total: int, length: int = 15, filled_char: str = "▰", empty_char: str = "▱"
) -> str:
    if total <= 0:
        percentage = 0
        filled = 0
    else:
        percentage = int(100 * current / total)
        filled = int(length * current / total)

    bar = filled_char * filled + empty_char * (length - filled)
    return f"{bar} {percentage}%"


def format_address(address: str, start_chars: int = 6, end_chars: int = 4, separator: str = "...") -> str:
    if not address or len(address) < start_chars + end_chars:
        return address
    return f"{address[:start_chars]}{separator}{address[-end_chars:]}"


def format_divider(char: str = "━", length: int = 20) -> str:
    return char * length


def format_header(title: str, subtitle: str = "", badge: str = "") -> str:
    """Render an ultra-premium minimalist header with optional badge and subtitle."""
    badge_part = f" [{badge}]" if badge else ""
    lines = [
        f"✦ <b>{title.upper()}{badge_part}</b> ✦",
        format_divider("⎯", 24),
    ]
    if subtitle:
        lines.append(f"<i>{subtitle}</i>\n")
    return "\n".join(lines)


def format_card(title: str, items: list[str], icon: str = "❖") -> str:
    """Render a structured data card with geometric bullets and clean line spacing."""
    lines = [f"<b>{icon} {title}</b>"]
    for item in items:
        lines.append(f"  ▫️ {item}")
    return "\n".join(lines)


def format_kv(key: str, value: str, icon: str = "▫️", code_val: bool = False) -> str:
    """Render a precision key-value row."""
    val_str = f"<code>{value}</code>" if code_val else str(value)
    return f"{icon} <b>{key}:</b> {val_str}"


def format_status_pill(status: str, label: str = "") -> str:
    """Render a sleek status badge."""
    if not label:
        return f"[ {status} ]"
    return f"[ {status} • <b>{label}</b> ]"


def format_alert(title: str, message: str, level: str = "INFO") -> str:
    """Render a clean alert box."""
    icons = {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "SUCCESS": "✅",
        "PRO": "💎",
    }
    icon = icons.get(level.upper(), "⚡")
    return f"{icon} <b>{title}</b>\n" f"{format_divider('─', 20)}\n" f"{message}"
