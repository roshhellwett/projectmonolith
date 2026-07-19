import asyncio
import contextlib
from typing import Any

from telegram import InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes


async def send_typing_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with contextlib.suppress(Exception):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")


async def send_loading_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str = "Processing...",
    keyboard: InlineKeyboardMarkup | None = None,
) -> Any | None:
    try:
        if update.callback_query:
            msg = await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            msg = await update.message.reply_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        return msg
    except BadRequest:
        pass
    return None


async def _edit_with_animation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> Any | None:
    try:
        if update.callback_query:
            return await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard, parse_mode=parse_mode
            )
    except BadRequest:
        pass
    try:
        if update.message:
            return await update.message.reply_text(text=text, reply_markup=keyboard, parse_mode=parse_mode)
    except Exception:
        pass
    return None


async def edit_with_stages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    stages: list[str],
    final_text: str,
    final_keyboard: InlineKeyboardMarkup | None = None,
    delay: float = 0.8,
) -> Any | None:
    msg = None
    for stage in stages:
        try:
            if msg is None:
                if update.callback_query:
                    msg = await update.callback_query.edit_message_text(text=stage, parse_mode="HTML")
                elif update.message:
                    msg = await update.message.reply_text(text=stage, parse_mode="HTML")
            else:
                msg = await msg.edit_text(text=stage, parse_mode="HTML")
        except BadRequest:
            pass
        await asyncio.sleep(delay)
    return await _edit_with_animation(update, context, final_text, final_keyboard)
