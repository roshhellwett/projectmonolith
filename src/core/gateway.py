"""
Centralized Telegram Update Gateway & Middleware.

Provides:
- Concurrency limiting (throttling simultaneous updates per bot) to prevent memory spikes under heavy load.
- Request validation (payload size checks, malformed update rejection).
- Memory management & periodic cache pruning utilities.
"""

import asyncio
import gc
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes

from core.logger import setup_logger
from core.rate_limiter import SlidingWindowLimiter

logger = setup_logger("GATEWAY")


class TelegramRequestValidator:
    """Validates incoming Telegram updates before handler execution."""

    MAX_TEXT_LENGTH = 4096 * 4  # Max allowed raw text length (including captions)
    MAX_ARGS_COUNT = 100        # Max arguments per command

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
        except asyncio.TimeoutError:
            self.rejected_requests += 1
            logger.warning(f"Gateway concurrency limit reached. Rejected update. (Active: {self.active_requests})")
            return False

    def release(self):
        """Release a concurrency slot."""
        self.active_requests = max(0, self.active_requests - 1)
        self.semaphore.release()

    def check_memory_and_prune(self):
        """
        Memory optimization check. If processed count crosses threshold,
        force garbage collection and prune expired rate limiter windows.
        """
        if self.total_processed % 500 == 0:
            logger.info("Running periodic gateway memory optimization and garbage collection...")
            SlidingWindowLimiter.prune_all_memory()
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
            try:
                await update.effective_message.reply_text(
                    "⚠️ Server under high load. Please try again in a few seconds."
                )
            except Exception:
                pass
        return

    try:
        _gateway.check_memory_and_prune()
        return await next_handler(update, context)
    finally:
        _gateway.release()


def get_gateway() -> GatewayController:
    return _gateway
