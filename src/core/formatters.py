def format_progress_bar(
    current: int, total: int, length: int = 15, filled_char: str = "█", empty_char: str = "░"
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
