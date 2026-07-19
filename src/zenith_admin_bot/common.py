import time
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from core.config import ADMIN_USER_ID
from core.logger import setup_logger

logger = setup_logger("ADMIN")

_admin_command_timestamps = {}


def track_task(task, background_tasks: set):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def rate_limit_admin(seconds: int = 10):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            command = func.__name__
            key = f"{user_id}:{command}"
            now = time.time()

            if key in _admin_command_timestamps:
                last_time = _admin_command_timestamps[key]
                if now - last_time < seconds:
                    if update.message:
                        await update.message.reply_text(f"Please wait {seconds} seconds between {command} commands.")
                    return

            _admin_command_timestamps[key] = now
            return await func(update, context)

        return wrapper

    return decorator


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_USER_ID:
            if update.message:
                await update.message.reply_text("Unauthorized.")
            elif update.callback_query:
                await update.callback_query.answer("Unauthorized.", show_alert=True)
            return
        return await func(update, context)

    return wrapper
