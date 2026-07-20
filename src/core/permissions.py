"""
Unified tier-checking middleware for all Zenith bots.

Provides:
- TierContext: resolved user tier info (cached)
- resolve_tier(): single async call to get user's tier
- @require_pro / @require_owner decorators for handler functions
- Replaces 30+ inline tier-check patterns across all bots
"""

import contextlib
import functools
import inspect
from dataclasses import dataclass

from cachetools import TTLCache
from telegram import Update
from telegram.ext import ContextTypes

from core.config import is_owner
from core.logger import setup_logger

logger = setup_logger("PERMISSIONS")

# Cache tier lookups for 60 seconds to avoid DB spam
_tier_cache: TTLCache = TTLCache(maxsize=10000, ttl=60.0)


@dataclass
class TierContext:
    """Resolved tier information for a user."""

    user_id: int
    is_owner: bool
    is_pro: bool
    days_left: int
    tier_name: str  # "owner", "pro", "free"

    @property
    def can_access_pro(self) -> bool:
        return self.is_owner or self.is_pro


async def resolve_tier(user_id: int) -> TierContext:
    """
    Resolve a user's tier with caching.

    Single DB call, cached for 60 seconds. All handlers should use this
    instead of making their own SubscriptionRepo calls.
    """
    # Check cache first
    cached = _tier_cache.get(user_id)
    if cached is not None:
        return cached

    # Import here to avoid circular imports at module level
    from zenith_crypto_bot.repository import SubscriptionRepo

    owner = is_owner(user_id)

    if owner:
        ctx = TierContext(
            user_id=user_id,
            is_owner=True,
            is_pro=True,
            days_left=999,
            tier_name="owner",
        )
    else:
        days_left = await SubscriptionRepo.get_days_left(user_id)
        is_pro = days_left > 0
        ctx = TierContext(
            user_id=user_id,
            is_owner=False,
            is_pro=is_pro,
            days_left=days_left,
            tier_name="pro" if is_pro else "free",
        )

    _tier_cache[user_id] = ctx
    return ctx


def invalidate_tier_cache(user_id: int) -> None:
    """Invalidate cached tier for a user (call after subscription changes)."""
    _tier_cache.pop(user_id, None)


def _accepts_tier(func) -> bool:
    try:
        sig = inspect.signature(func)
        if "tier" in sig.parameters:
            return True
        return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values())
    except Exception:
        return True


def require_pro(locked_feature_name: str = "This feature"):
    """
    Decorator that gates a handler behind Pro tier.

    Usage:
        @require_pro("Deep Research")
        async def cmd_research(update, context, tier):
            # tier is injected as TierContext
            ...
    """

    def decorator(func):
        accepts_tier = _accepts_tier(func)

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            tier = await resolve_tier(user_id)

            if not tier.can_access_pro:
                from core.tier_limits import get_upgrade_text

                text = get_upgrade_text(locked_feature_name)
                if update.callback_query:
                    with contextlib.suppress(Exception):
                        await update.callback_query.answer()
                    with contextlib.suppress(Exception):
                        await update.callback_query.edit_message_text(text, parse_mode="HTML")
                elif update.message:
                    await update.message.reply_text(text, parse_mode="HTML")
                return

            if accepts_tier:
                return await func(update, context, *args, tier=tier, **kwargs)
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator


def require_owner(func):
    """
    Decorator that gates a handler behind owner/admin access.

    Usage:
        @require_owner
        async def cmd_admin_only(update, context, tier):
            ...
    """
    accepts_tier = _accepts_tier(func)

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        tier = await resolve_tier(user_id)

        if not tier.is_owner:
            text = "🔒 This command is restricted to the bot owner."
            if update.callback_query:
                with contextlib.suppress(Exception):
                    await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text)
            return

        if accepts_tier:
            return await func(update, context, *args, tier=tier, **kwargs)
        return await func(update, context, *args, **kwargs)

    return wrapper


async def get_tier_for_handler(update: Update) -> TierContext:
    """
    Convenience function for handlers that need tier info but don't use decorators.

    Usage:
        async def cmd_start(update, context):
            tier = await get_tier_for_handler(update)
            if tier.is_pro:
                ...
    """
    return await resolve_tier(update.effective_user.id)
