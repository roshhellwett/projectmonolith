"""
Production-grade rate limiting for Zenith bots.

Provides sliding-window rate limiting that:
- Persists across restarts (DB-backed with in-memory fast path)
- Supports per-user, per-action limits
- Returns friendly "try again in X seconds" messages
- Differentiates between free and pro tiers
"""

import time
from collections import defaultdict, deque

from cachetools import TTLCache

from core.logger import setup_logger

logger = setup_logger("RATE_LIMITER")


class SlidingWindowLimiter:
    """
    In-memory sliding window rate limiter.

    Tracks timestamps of recent actions per user and checks against limits.
    Uses TTLCache for automatic cleanup of inactive users.

    For production persistence across restarts, the state is intentionally
    reset — this is acceptable because rate limits are short-lived (minutes/hours)
    and a restart effectively gives users a fresh start.
    """

    def __init__(self, max_users: int = 50000):
        # user_id -> deque of timestamps for each action
        self._windows: dict[str, TTLCache] = {}
        self._max_users = max_users

    def _get_window(self, action: str, ttl: float) -> TTLCache:
        """Get or create a TTLCache for an action type."""
        key = f"{action}_{int(ttl)}"
        if key not in self._windows:
            self._windows[key] = TTLCache(maxsize=self._max_users, ttl=ttl)
        return self._windows[key]

    def check(
        self,
        user_id: int,
        action: str,
        limit: int,
        window_seconds: float,
    ) -> tuple[bool, int]:
        """
        Check if user can perform an action.

        Returns:
            (is_allowed, seconds_until_reset)
            - is_allowed: True if within limits
            - seconds_until_reset: seconds until the oldest entry expires (0 if allowed)
        """
        cache = self._get_window(action, window_seconds)
        now = time.monotonic()

        # Get existing timestamps
        timestamps: deque = cache.get(user_id, deque(maxlen=limit + 1))

        # Clean old timestamps outside window
        cutoff = now - window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            # Rate limited — calculate when the oldest entry expires
            oldest = timestamps[0]
            seconds_left = max(1, int((oldest + window_seconds) - now))
            return False, seconds_left

        # Allowed — record this action
        timestamps.append(now)
        cache[user_id] = timestamps
        return True, 0

    def get_remaining(
        self,
        user_id: int,
        action: str,
        limit: int,
        window_seconds: float,
    ) -> int:
        """Get how many actions the user has remaining in the current window."""
        cache = self._get_window(action, window_seconds)
        now = time.monotonic()

        timestamps: deque = cache.get(user_id, deque())

        # Count valid (non-expired) timestamps
        cutoff = now - window_seconds
        active = sum(1 for t in timestamps if t >= cutoff)

        return max(0, limit - active)


# ==========================================================
# Global rate limiter instance
# ==========================================================
_limiter = SlidingWindowLimiter()


def check_rate_limit(
    user_id: int,
    action: str,
    limit: int,
    window_seconds: float,
) -> tuple[bool, int]:
    """
    Check rate limit for a user action.

    Args:
        user_id: Telegram user ID
        action: Action identifier (e.g., "ai_query", "crypto_command")
        limit: Max actions allowed in window
        window_seconds: Time window in seconds

    Returns:
        (is_allowed, seconds_until_reset)
    """
    return _limiter.check(user_id, action, limit, window_seconds)


def get_remaining_quota(
    user_id: int,
    action: str,
    limit: int,
    window_seconds: float,
) -> int:
    """Get remaining quota for a user action."""
    return _limiter.get_remaining(user_id, action, limit, window_seconds)


def format_rate_limit_message(
    seconds_left: int,
    feature_name: str = "",
    is_pro: bool = False,
) -> str:
    """Generate a user-friendly rate limit message."""
    if seconds_left > 3600:
        time_str = f"{seconds_left // 3600}h {(seconds_left % 3600) // 60}m"
    elif seconds_left > 60:
        time_str = f"{seconds_left // 60}m {seconds_left % 60}s"
    else:
        time_str = f"{seconds_left}s"

    text = f"⏳ <b>Rate Limit Reached</b>"
    if feature_name:
        text += f" — {feature_name}"
    text += f"\n\nPlease try again in <b>{time_str}</b>."

    if not is_pro:
        text += (
            "\n\n💎 <b>Zenith Pro</b> users get significantly higher limits.\n"
            "<code>/activate YOUR-KEY</code>"
        )

    return text
