"""
Single source of truth for ALL tier-based feature limits across every bot.

Every rate limit, quota, and feature gate in the system references this file.
No magic numbers scattered across handlers.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TierLimit:
    """A feature limit with free and pro values."""

    free: int
    pro: int
    owner: int | None = None  # None means unlimited

    def get(self, tier: str) -> int:
        if tier == "owner":
            return self.owner if self.owner is not None else 999_999
        elif tier == "pro":
            return self.pro
        return self.free


# ==========================================================
# Crypto Bot Limits
# ==========================================================
CRYPTO_PRICE_ALERTS = TierLimit(free=1, pro=25)
CRYPTO_PORTFOLIO_TOKENS = TierLimit(free=3, pro=20)
CRYPTO_TRACKED_WALLETS = TierLimit(free=0, pro=5)  # free = locked
CRYPTO_SAVED_AUDITS = TierLimit(free=10, pro=10)

# ==========================================================
# AI Bot Limits
# ==========================================================
AI_QUERIES_PER_DAY = TierLimit(free=10, pro=100)
AI_RATE_PER_HOUR = TierLimit(free=10, pro=60)
AI_MAX_TOKENS = TierLimit(free=1024, pro=4096)
AI_HISTORY_MESSAGES = TierLimit(free=0, pro=10)  # free = locked

# ==========================================================
# Group Bot Limits
# ==========================================================
GROUP_PROTECTED_GROUPS = TierLimit(free=1, pro=5)
GROUP_CUSTOM_WORDS = TierLimit(free=0, pro=200)  # free = locked
GROUP_SCHEDULED_MESSAGES = TierLimit(free=0, pro=10)  # free = locked

# ==========================================================
# Support Bot Limits
# ==========================================================
SUPPORT_OPEN_TICKETS = TierLimit(free=3, pro=15, owner=999)
SUPPORT_FAQ_VISIBLE = TierLimit(free=10, pro=50)

# ==========================================================
# Rate Limiting (per-user, applies across all bots)
# ==========================================================
COMMAND_COOLDOWN_SECONDS = TierLimit(free=15, pro=5)
COMMANDS_PER_MINUTE = TierLimit(free=5, pro=20)
COMMANDS_PER_HOUR = TierLimit(free=50, pro=200)

# ==========================================================
# Feature Flags (which features are available per tier)
# ==========================================================
PRO_ONLY_FEATURES = {
    "crypto": [
        "wallet_tracker",
        "top_gainers_losers",
        "gas_optimizer",
        "full_audit_report",
        "real_time_whale_alerts",
        "new_pair_full_address",
    ],
    "ai": [
        "personas",
        "deep_research",
        "document_summarizer",
        "code_interpreter",
        "image_prompt_crafter",
        "chat_history",
    ],
    "group": [
        "custom_word_filter",
        "anti_raid_shield",
        "moderation_analytics",
        "scheduled_messages",
        "custom_welcome",
        "audit_log",
    ],
    "support": [
        "priority_support",
        "canned_responses",
        "ticket_stats",
        "ai_auto_response",
    ],
}


def is_feature_locked(feature: str, bot: str, tier: str) -> bool:
    """Check if a feature is locked for the given tier."""
    if tier in ("pro", "owner"):
        return False
    return feature in PRO_ONLY_FEATURES.get(bot, [])


def get_upgrade_text(feature_name: str) -> str:
    """Get a consistent upgrade prompt for locked features."""
    return (
        f"🔒 <b>{feature_name}</b> is a Pro feature.\n\n"
        f"Upgrade to <b>Zenith Pro</b> to unlock this and all premium features.\n\n"
        f"<code>/activate YOUR-KEY</code>"
    )


def get_limit_text(feature_name: str, current: int, limit: int, is_pro: bool) -> str:
    """Get a consistent limit-reached message."""
    base = f"📊 <b>{feature_name} Limit Reached</b>\n\n" f"You have <b>{current}/{limit}</b> active.\n"
    if not is_pro:
        base += "\n💎 Upgrade to <b>Zenith Pro</b> for higher limits.\n" "<code>/activate YOUR-KEY</code>"
    else:
        base += "\nPlease remove existing items to add new ones."
    return base
