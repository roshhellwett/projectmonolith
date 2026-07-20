"""
Unified error handling for all Zenith bots.

Provides:
- Categorized error types with user-friendly messages
- Global error handler for telegram-bot update errors
- Admin alerting for critical errors
- Safe message sending with automatic fallbacks
"""

import asyncio
import contextlib
import traceback
from enum import Enum

from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import ContextTypes

from core.logger import setup_logger

logger = setup_logger("ERROR_HANDLER")


class ErrorCategory(Enum):
    """Categories of errors with user-facing messages."""

    RATE_LIMITED = "rate_limited"
    API_TIMEOUT = "api_timeout"
    EXTERNAL_API_DOWN = "external_api_down"
    DB_ERROR = "db_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    TELEGRAM_ERROR = "telegram_error"
    INTERNAL_ERROR = "internal_error"


# User-friendly messages for each error category
ERROR_MESSAGES = {
    ErrorCategory.RATE_LIMITED: (
        "⏳ <b>Slow down!</b>\n\n" "You're sending requests too quickly. Please wait a moment and try again."
    ),
    ErrorCategory.API_TIMEOUT: (
        "⏱️ <b>Request Timed Out</b>\n\n"
        "The server took too long to respond. This usually resolves itself — please try again in a few seconds."
    ),
    ErrorCategory.EXTERNAL_API_DOWN: (
        "🔧 <b>Service Temporarily Unavailable</b>\n\n"
        "An external service we depend on is currently down. We're monitoring the situation. "
        "Please try again in a few minutes."
    ),
    ErrorCategory.DB_ERROR: (
        "💾 <b>Temporary Issue</b>\n\n"
        "We encountered a brief database issue. Please try again — it usually resolves in seconds."
    ),
    ErrorCategory.PERMISSION_ERROR: (
        "🔒 <b>Permission Denied</b>\n\n" "You don't have permission to perform this action."
    ),
    ErrorCategory.VALIDATION_ERROR: (
        "⚠️ <b>Invalid Input</b>\n\n" "Please check your input and try again. Use /help for command usage."
    ),
    ErrorCategory.TELEGRAM_ERROR: (
        "📱 <b>Telegram Error</b>\n\n" "There was an issue communicating with Telegram. Please try again."
    ),
    ErrorCategory.INTERNAL_ERROR: (
        "❌ <b>Something Went Wrong</b>\n\n"
        "An unexpected error occurred. Our team has been notified. "
        "Please try again or contact support if the issue persists."
    ),
}


def categorize_error(error: Exception) -> ErrorCategory:
    """Categorize an exception into a user-friendly error type."""
    if isinstance(error, RetryAfter):
        return ErrorCategory.RATE_LIMITED
    if isinstance(error, TimedOut | asyncio.TimeoutError):
        return ErrorCategory.API_TIMEOUT
    if isinstance(error, Forbidden):
        return ErrorCategory.PERMISSION_ERROR
    if isinstance(error, BadRequest):
        return ErrorCategory.TELEGRAM_ERROR
    if isinstance(error, NetworkError):
        return ErrorCategory.EXTERNAL_API_DOWN
    if isinstance(error, ValueError):
        return ErrorCategory.VALIDATION_ERROR

    # Check for database errors
    error_name = type(error).__name__
    if error_name in ("OperationalError", "InterfaceError", "DisconnectionError", "ConnectionRefusedError"):
        return ErrorCategory.DB_ERROR

    # Check for httpx/network errors
    if error_name in ("ConnectError", "ReadTimeout", "ConnectTimeout", "PoolTimeout"):
        return ErrorCategory.EXTERNAL_API_DOWN

    return ErrorCategory.INTERNAL_ERROR


async def safe_send_message(
    update: Update,
    text: str,
    parse_mode: str = "HTML",
    reply_markup=None,
) -> bool:
    """
    Send a message with automatic fallbacks.

    Tries: callback query edit → message reply → plain text fallback.
    Returns True if message was sent successfully.
    """
    if not update:
        return False

    # Try editing callback query message first
    if update.callback_query:
        with contextlib.suppress(Exception):
            await update.callback_query.edit_message_text(text=text, parse_mode=parse_mode, reply_markup=reply_markup)
            return True

    # Try replying to message
    if update.message or update.edited_message:
        msg = update.message or update.edited_message
        try:
            await msg.reply_text(text=text, parse_mode=parse_mode, reply_markup=reply_markup)
            return True
        except BadRequest:
            # HTML parsing failed — try without formatting
            with contextlib.suppress(Exception):
                import re

                plain = re.sub(r"<[^>]+>", "", text)
                await msg.reply_text(text=plain)
                return True

    return False


async def handle_bot_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler for python-telegram-bot.

    Register with: application.add_error_handler(handle_bot_error)
    """
    error = context.error
    if error is None:
        return

    # Ignore "message not modified" errors — not a real problem
    if isinstance(error, BadRequest) and "not modified" in str(error).lower():
        return

    # Ignore user-blocked-bot errors
    if isinstance(error, Forbidden):
        logger.debug(f"User blocked the bot: {error}")
        return

    # Handle rate limiting from Telegram
    if isinstance(error, RetryAfter):
        logger.warning(f"Telegram rate limit: retry after {error.retry_after}s")
        await asyncio.sleep(error.retry_after)
        return

    # Categorize and log
    category = categorize_error(error)

    if category == ErrorCategory.INTERNAL_ERROR:
        # Log full traceback for unexpected errors with exact sector breakdown
        logger.error(
            f"\n┌── 🚨 SECTOR ERROR DIAGNOSTIC ──┐\n"
            f"│ Sector:   {logger.name}\n"
            f"│ Category: {category.value}\n"
            f"│ Error:    {error}\n"
            f"└────────────────────────────────┘\n"
            f"{''.join(traceback.format_exception(type(error), error, error.__traceback__))}"
        )
    else:
        logger.warning(f"Handled sector error [{category.value}] in {logger.name}: {error}")

    # Send user-friendly message
    if update:
        user_message = ERROR_MESSAGES.get(category, ERROR_MESSAGES[ErrorCategory.INTERNAL_ERROR])
        await safe_send_message(update, user_message)

    # Alert admin for critical errors
    if category in (ErrorCategory.INTERNAL_ERROR, ErrorCategory.DB_ERROR):
        await _alert_admin(context, error, category, update)


async def _alert_admin(
    context: ContextTypes.DEFAULT_TYPE,
    error: Exception,
    category: ErrorCategory,
    update: Update | None,
) -> None:
    """Send critical error alert to admin via Telegram."""
    from core.config import ADMIN_USER_ID

    if not ADMIN_USER_ID:
        return

    user_info = ""
    if update and update.effective_user:
        user_info = f"\n<b>User:</b> <code>{update.effective_user.id}</code>"

    command_info = ""
    if update and update.message and update.message.text:
        command_info = f"\n<b>Command:</b> <code>{update.message.text[:100]}</code>"

    alert_text = (
        f"🚨 <b>CRITICAL SECTOR ERROR</b>\n\n"
        f"<b>Sector:</b> <code>{logger.name}</code>\n"
        f"<b>Category:</b> {category.value}\n"
        f"<b>Error:</b> <code>{str(error)[:200]}</code>"
        f"{user_info}"
        f"{command_info}"
    )

    with contextlib.suppress(Exception):
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=alert_text,
            parse_mode="HTML",
        )
