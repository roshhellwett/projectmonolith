"""
Centralized Telegram Update Gateway & Middleware.

Provides:
- Concurrency limiting (throttling simultaneous updates per bot) to prevent memory spikes under heavy load.
- Request validation (payload size checks, malformed update rejection).
- Memory management & periodic cache pruning utilities.
"""

import asyncio
import contextlib
import gc
from collections.abc import Callable

from cachetools import TTLCache
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import setup_logger
from core.rate_limiter import SlidingWindowLimiter

logger = setup_logger("GATEWAY")

_seen_update_ids: TTLCache | None = None


def get_update_id_dedup_cache() -> TTLCache:
    global _seen_update_ids
    if _seen_update_ids is None:
        _seen_update_ids = TTLCache(maxsize=100000, ttl=300)
    return _seen_update_ids


class TelegramRequestValidator:
    """Validates incoming Telegram updates before handler execution."""

    MAX_TEXT_LENGTH = 4096 * 4  # Max allowed raw text length (including captions)
    MAX_ARGS_COUNT = 100  # Max arguments per command

    @classmethod
    def validate_update(cls, update: Update) -> tuple[bool, str]:
        """
        Validate an update for sanity and safety.
        Returns (is_valid, error_reason).
        """
        if not update:
            return False, "Empty update"

        user = update.effective_user
        if not user or user.id <= 0:
            return False, "Invalid or missing user ID"

        # Check chat validity only when message/channel_post is directly present
        # CallbackQuery, InlineQuery, and other queries/membership updates may not have a valid effective_chat or may have Chat(id=0)
        is_query_or_member_update = bool(
            update.callback_query
            or update.inline_query
            or update.chosen_inline_result
            or update.pre_checkout_query
            or update.shipping_query
            or update.my_chat_member
            or update.chat_member
        )
        if not is_query_or_member_update:
            chat = update.effective_chat
            if not chat or chat.id == 0:
                return False, "Invalid or missing chat ID"

        msg = update.effective_message
        if msg:
            text = msg.text or msg.caption or ""
            if len(text) > cls.MAX_TEXT_LENGTH:
                return False, f"Message text exceeds maximum length ({len(text)} > {cls.MAX_TEXT_LENGTH})"

        return True, ""


class GatewayController:
    """
    Manages concurrency and memory limits for bot instances.
    Ensures safe resource utilization during traffic spikes.
    """

    def __init__(self, max_concurrent_updates: int = 200):
        self.semaphore = asyncio.Semaphore(max_concurrent_updates)
        self.active_requests = 0
        self.total_processed = 0
        self.rejected_requests = 0

    async def acquire(self) -> bool:
        """Attempt to acquire a concurrency slot."""
        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout=5.0)
            self.active_requests += 1
            self.total_processed += 1
            return True
        except TimeoutError:
            self.rejected_requests += 1
            logger.warning(f"Gateway concurrency limit reached. Rejected update. (Active: {self.active_requests})")
            return False

    def release(self):
        """Release a concurrency slot."""
        self.active_requests = max(0, self.active_requests - 1)
        self.semaphore.release()

    async def check_memory_and_prune(self):
        """
        Memory optimization check. If processed count crosses threshold,
        force garbage collection and prune expired rate limiter windows.
        """
        if self.total_processed % 500 == 0:
            logger.info("Running periodic gateway memory optimization and garbage collection...")
            await SlidingWindowLimiter.prune_all_memory()
            gc.collect()

    def get_stats(self) -> dict:
        return {
            "active_requests": self.active_requests,
            "total_processed": self.total_processed,
            "rejected_requests": self.rejected_requests,
        }


# Global singleton gateway instance
_gateway = GatewayController(max_concurrent_updates=250)


async def gateway_middleware(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    next_handler: Callable,
):
    """
    Middleware function to wrap around bot handlers for validation,
    rate limiting check, and memory optimization.
    """
    is_valid, reason = TelegramRequestValidator.validate_update(update)
    if not is_valid:
        logger.warning(f"Gateway rejected invalid update: {reason}")
        return

    acquired = await _gateway.acquire()
    if not acquired:
        if update.effective_message:
            with contextlib.suppress(Exception):
                await update.effective_message.reply_text(
                    "⚠️ Server under high load. Please try again in a few seconds."
                )
        return

    try:
        await _gateway.check_memory_and_prune()
        return await next_handler(update, context)
    finally:
        _gateway.release()


def get_gateway() -> GatewayController:
    return _gateway


def validate_webhook_auth(path_secret: str, request: "Request") -> bool:
    """Validate webhook path secret and Telegram secret-token header."""
    from core.config import WEBHOOK_SECRET

    if not WEBHOOK_SECRET or path_secret != WEBHOOK_SECRET:
        return False

    header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if header_token and header_token != WEBHOOK_SECRET:
        return False
    return True


def resolve_webhook_url(bot_name: str) -> str:
    """Build the full webhook URL for a bot service."""
    from core.config import WEBHOOK_SECRET, WEBHOOK_URL

    base = (WEBHOOK_URL or "").strip().rstrip("/")
    if not base:
        return ""
    if not base.startswith("http"):
        base = f"https://{base}"
    return f"{base}/webhook/{bot_name.lower()}/{WEBHOOK_SECRET}"


async def setup_bot_webhook(bot_app, bot_name: str) -> None:
    """Register webhook for a bot with shared error handling. Starts polling if WEBHOOK_URL is unconfigured."""
    from core.config import WEBHOOK_SECRET
    from core.logger import setup_logger as _setup_logger

    _log = _setup_logger("WEBHOOK")
    url = resolve_webhook_url(bot_name)
    if not url:
        _log.warning(f"Webhook URL not configured — {bot_name} running in polling mode")
        try:
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            if bot_app.updater and not bot_app.updater.running:
                await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                _log.info(f"✅ {bot_name} started in polling mode")
        except Exception as e:
            _log.error(f"❌ {bot_name} polling setup failed: {e}")
        return
    try:
        with contextlib.suppress(Exception):
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.bot.set_webhook(
            url=url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES,
        )
        _log.info(f"✅ {bot_name} webhook registered at {url}")
        try:
            info = await bot_app.bot.get_webhook_info()
            _log.info(
                f"📋 {bot_name} status -> pending_updates: {info.pending_update_count}, last_error: {info.last_error_message or 'None'}"
            )
            if info.last_error_message:
                _log.error(
                    f"⚠️ Telegram server reported error delivering webhook for {bot_name}: {info.last_error_message}"
                )
        except Exception as ex:
            _log.warning(f"Could not fetch get_webhook_info for {bot_name}: {ex}")
    except Exception as e:
        _log.error(f"❌ {bot_name} webhook setup failed: {e}")


def attach_gateway(bot_app, bot_name: str):
    """
    Attaches the central gateway middleware and registers the bot with monitoring.
    """
    from telegram.ext import TypeHandler

    from zenith_admin_bot.monitoring import register_bot_app

    register_bot_app(bot_name, bot_app)

    async def gateway_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log incoming updates. Concurrency and validation are handled by gateway_middleware."""
        try:
            user_id = update.effective_user.id if update.effective_user else "unknown"
            logger.info(f"⚡ [{bot_name}] Processing Update {update.update_id} from user {user_id}")
            await _gateway.check_memory_and_prune()
        except Exception as e:
            logger.error(f"Error in gateway_type_handler ({bot_name}): {e}", exc_info=True)

    with contextlib.suppress(Exception):
        bot_app.add_handler(TypeHandler(Update, gateway_type_handler), group=-999)

    original_process_update = bot_app.process_update

    async def wrapped_process_update(update: object):
        try:
            if isinstance(update, Update):

                async def next_call(u, c=None):
                    return await original_process_update(u)

                await gateway_middleware(update, None, next_call)
            else:
                await original_process_update(update)
        except Exception as e:
            logger.error(
                f"\n┌── 🚨 SECTOR ERROR DIAGNOSTIC ──┐\n"
                f"│ Sector:   GATEWAY ({bot_name})\n"
                f"│ Error:    {e}\n"
                f"└────────────────────────────────┘",
                exc_info=True,
            )

    with contextlib.suppress(AttributeError):
        bot_app.process_update = wrapped_process_update
