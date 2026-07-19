import asyncio
import contextlib
from typing import Any

from telegram import InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes


async def send_typing_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with contextlib.suppress(Exception):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")


async def edit_or_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
    existing_msg: Any | None = None,
) -> Any | None:
    """Bulletproof helper to edit an existing message or reply with a new message, handling Telegram errors cleanly."""
    if existing_msg is not None:
        try:
            return await existing_msg.edit_text(text=text, reply_markup=keyboard, parse_mode=parse_mode)
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return existing_msg
        except Exception:
            pass

    if update.callback_query and update.callback_query.message:
        try:
            return await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard, parse_mode=parse_mode
            )
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return update.callback_query.message
        except Exception:
            pass

    chat_id = update.effective_chat.id if update.effective_chat else None
    if update.message:
        try:
            return await update.message.reply_text(text=text, reply_markup=keyboard, parse_mode=parse_mode)
        except Exception:
            pass
    elif chat_id and context.bot:
        try:
            return await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode=parse_mode)
        except Exception:
            pass
    return None


async def send_loading_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str = "Processing...",
    keyboard: InlineKeyboardMarkup | None = None,
) -> Any | None:
    return await edit_or_reply(update, context, text=text, keyboard=keyboard)


async def _edit_with_animation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
    existing_msg: Any | None = None,
) -> Any | None:
    return await edit_or_reply(update, context, text=text, keyboard=keyboard, parse_mode=parse_mode, existing_msg=existing_msg)


async def edit_with_stages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    stages: list[str],
    final_text: str,
    final_keyboard: InlineKeyboardMarkup | None = None,
    delay: float = 0.7,
) -> Any | None:
    msg = None
    for stage in stages:
        try:
            if msg is None:
                msg = await edit_or_reply(update, context, text=stage)
            else:
                try:
                    msg = await msg.edit_text(text=stage, parse_mode="HTML")
                except BadRequest as e:
                    if "not modified" not in str(e).lower():
                        raise
        except Exception:
            pass
        await asyncio.sleep(delay)
    return await edit_or_reply(update, context, text=final_text, keyboard=final_keyboard, existing_msg=msg)


def get_ai_stages(query: str = "neural pathways") -> list[str]:
    """Precision-crafted multi-stage loading sequence for AI synthesis."""
    return [
        f"⚡ <b>ZENITH CODEX</b> » <i>Initializing neural context for {query}...</i>\n<code>[▰▰▱▱▱▱▱▱▱▱] 20%</code>",
        "⚡ <b>ZENITH CODEX</b> » <i>Querying multi-tier Groq LLM clusters...</i>\n<code>[▰▰▰▰▰▱▱▱▱▱] 50%</code>",
        "⚡ <b>ZENITH CODEX</b> » <i>Synthesizing final intelligence response...</i>\n<code>[▰▰▰▰▰▰▰▰▰▱] 90%</code>",
    ]


def get_crypto_stages(subject: str = "On-Chain Audit") -> list[str]:
    """Precision-crafted multi-stage loading sequence for Crypto scans."""
    return [
        "🛡️ <b>ZENITH SECURITY</b> » <i>Connecting to GoPlus honeypot nodes...</i>\n<code>[▰▰▱▱▱▱▱▱▱▱] 25%</code>",
        "🛡️ <b>ZENITH SECURITY</b> » <i>Scanning tax rates, LP lock & ownership proxy...</i>\n<code>[▰▰▰▰▰▰▱▱▱▱] 60%</code>",
        f"🛡️ <b>ZENITH SECURITY</b> » <i>Aggregating smart money radar for {subject}...</i>\n<code>[▰▰▰▰▰▰▰▰▰▱] 95%</code>",
    ]


def get_group_stages(action: str = "Moderation Scan") -> list[str]:
    """Precision-crafted multi-stage sequence for Group & Admin operations."""
    return [
        "⚡ <b>ZENITH SHIELD</b> » <i>Verifying group security policies...</i>\n<code>[▰▰▰▱▱▱▱▱▱▱] 30%</code>",
        f"⚡ <b>ZENITH SHIELD</b> » <i>Executing {action}...</i>\n<code>[▰▰▰▰▰▰▰▱▱▱] 70%</code>",
    ]

