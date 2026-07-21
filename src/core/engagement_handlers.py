"""Shared engagement handlers for referral, feedback, stats, and changelog."""

import re

from telegram import Update
from telegram.ext import ContextTypes

from core.logger import setup_logger
from zenith_crypto_bot.repository import SubscriptionRepo

logger = setup_logger("ENGAGEMENT")

_RE_REFERRAL_CODE = re.compile(r"^[A-Z0-9]{6,20}$")


def _sanitize_text(text: str, max_len: int = 2000) -> str:
    cleaned = text.strip()[:max_len]
    return re.sub(r"<[^>]*>", "", cleaned)


_CHANGELOG = (
    "<b>📋 Zenith Changelog</b>\n\n"
    "<b>July 21, 2026</b>\n"
    "\u2022 Server-managed AI \u2014 no personal API key needed\n"
    "\u2022 Real-time whale alerts via Etherscan\n"
    "\u2022 Daily token quotas (10K free, 500K pro)\n"
    "\u2022 Data retention auto-cleanup for privacy\n"
    "\u2022 Performance optimizations across all bots\n"
    "\u2022 Referral program \u2014 invite friends for bonus Pro days!"
)


async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = await SubscriptionRepo.get_or_create_referral(user_id)
    stats = await SubscriptionRepo.get_referral_stats(user_id)

    raw_code = "".join(context.args).strip().upper() if context.args else ""
    if raw_code:
        if not _RE_REFERRAL_CODE.match(raw_code):
            await update.message.reply_text(
                "❌ Invalid referral code format. Codes are 6-20 alphanumeric characters.",
            )
            return
        success, msg = await SubscriptionRepo.redeem_referral(user_id, raw_code)
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    text = (
        f"<b>🤝 Referral Program</b>\n\n"
        f"Your referral code: <code>{code}</code>\n\n"
        f"Share it with friends! When they use <code>/referral {code}</code>,\n"
        f"<b>both</b> of you get <b>{stats['bonus_days']} days</b> of Zenith Pro!\n\n"
        f"Redemptions so far: <b>{stats['used']}</b>\n"
        f"To use someone else's code:\n"
        f"<code>/referral THEIR_CODE</code>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(context.args) if context.args else ""
    if not msg:
        await update.message.reply_text(
            "<b>📮 Feedback</b>\n\n"
            "Send your feedback:\n"
            "<code>/feedback your message here</code>\n\n"
            "We read every submission!",
            parse_mode="HTML",
        )
        return
    clean = _sanitize_text(msg)
    if not clean:
        await update.message.reply_text("Your feedback was empty. Please write something!")
        return
    await SubscriptionRepo.submit_feedback(update.effective_user.id, clean)
    await update.message.reply_text(
        "✅ <b>Thanks for your feedback!</b> We review every submission.",
        parse_mode="HTML",
    )


async def cmd_changelog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_CHANGELOG, parse_mode="HTML")


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        from zenith_ai_bot.repository import UsageRepo

        quota = await UsageRepo.get_token_quota(user_id)
        days = await SubscriptionRepo.get_days_left(user_id)
        stats = await SubscriptionRepo.get_referral_stats(user_id)
        tier = "Pro" if days > 0 else "Free"

        text = (
            f"<b>📊 Your Stats</b>\n\n"
            f"Tier: <b>{tier}</b>\n"
            f"Pro days remaining: <b>{days}</b>\n"
            f"AI tokens today: <b>{quota['tokens_used']:,}</b> / <b>{quota['daily_limit']:,}</b>\n"
            f"Referrals: <b>{stats['used']}</b>\n"
            f"Code: <code>{stats['code'] or 'N/A'}</code>\n\n"
            f"Use <code>/referral</code> to earn more Pro days!"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await update.message.reply_text(
            "<b>📊 Your Stats</b>\n\n" "Could not load stats right now. Try again later.",
            parse_mode="HTML",
        )
