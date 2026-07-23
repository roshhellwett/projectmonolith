import asyncio
import contextlib
import re

from telegram import Update
from telegram.error import RetryAfter
from telegram.ext import ContextTypes

from core.animation import send_typing_action
from core.logger import setup_logger
from zenith_ai_bot.repository import UsageRepo
from zenith_crypto_bot import ui as crypto_ui
from zenith_crypto_bot.ai_engine import call_crypto_ai
from zenith_crypto_bot.repository import SubscriptionRepo

logger = setup_logger("CRYPTO_AI_HANDLER")

_AI_STAGES = ["Reading your data...", "Checking markets...", "Thinking..."]


async def _edit_with_final(
    msg: object,
    text: str,
    kb: object = None,
) -> None:
    try:
        await msg.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        plain = re.sub(r"<[^>]+>", "", text)
        with contextlib.suppress(Exception):
            await msg.edit_text(plain, disable_web_page_preview=True)


async def _stage_through(msg: object, stages: list[str]) -> None:
    for i, stage in enumerate(stages):
        if i > 0:
            await asyncio.sleep(0.8)
        with contextlib.suppress(Exception):
            await msg.edit_text(stage, parse_mode="HTML")
    await asyncio.sleep(0.8)
    with contextlib.suppress(Exception):
        await msg.edit_text("Generating your answer...", parse_mode="HTML")


async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    quota_allowed, quota_msg = await UsageRepo.check_quota(user_id)
    if not quota_allowed:
        await update.message.reply_text(quota_msg, parse_mode="HTML")
        return

    query = " ".join(context.args) if context.args else ""
    if not query:
        text, kb = crypto_ui.get_ai_empty_query_msg()
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return

    is_pro = await SubscriptionRepo.is_pro(user_id)
    await send_typing_action(update, context)

    msg = await update.message.reply_text(_AI_STAGES[0], parse_mode="HTML")
    try:
        await _stage_through(msg, _AI_STAGES)
        response, error = await call_crypto_ai(user_id, query)

        if error == "rate_limited":
            text, kb = crypto_ui.get_ai_rate_limited_msg()
        elif error == "server_error":
            text, kb = crypto_ui.get_ai_server_error_msg()
        elif response:
            text, kb = crypto_ui.get_ai_response_msg(response, query)
        else:
            text, kb = crypto_ui.get_ai_server_error_msg()

        await _edit_with_final(msg, text, kb)

        if is_pro:
            try:
                from zenith_ai_bot.repository import ConversationRepo

                await ConversationRepo.add_message(user_id, "user", query[:2000])
                if response:
                    await ConversationRepo.add_message(user_id, "assistant", response[:2000])
            except Exception:
                pass

    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
        text, kb = crypto_ui.get_ai_server_error_msg()
        await _edit_with_final(msg, text, kb)
    except Exception as e:
        logger.error(f"AI handler error: {e}")
        text, kb = crypto_ui.get_ai_server_error_msg()
        await _edit_with_final(msg, text, kb)


async def cmd_setkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ <b>Server-Managed AI</b>\n\n"
        "Zenith now uses its own AI engine — no personal API key needed!\n\n"
        "Just use <code>/ai your question</code> to analyze markets and get crypto insights.",
        parse_mode="HTML",
    )


async def cmd_mykey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quota = await UsageRepo.get_token_quota(update.effective_user.id)
    await update.message.reply_text(
        f"⚡ <b>AI Token Usage</b>\n\n"
        f"Tokens Used: <b>{quota['tokens_used']:,}</b>\n\n"
        f"You are using your own API key, so there are no usage limits.",
        parse_mode="HTML",
    )


async def cmd_delkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ <b>No Key to Delete</b>\n\n" "Zenith uses server-managed AI — your account is automatically configured.",
        parse_mode="HTML",
    )


async def handle_ai_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()
    data = query.data
    if not data.startswith("ai_followup_"):
        return
    topic = data.replace("ai_followup_", "", 1)

    user_id = query.from_user.id

    if "set" in topic.lower() and ("key" in topic.lower() or "groq" in topic.lower()):
        quota = await UsageRepo.get_token_quota(user_id)
        text = (
            "<b>Crypto AI</b>\n\n"
            "This bot connects to your personal Groq API key for completely unlimited access.\n\n"
            f"Tokens Used: <b>{quota['tokens_used']:,}</b>"
        )
        await query.edit_message_text(text, parse_mode="HTML")
        return

    quota_allowed, quota_msg = await UsageRepo.check_quota(user_id)
    if not quota_allowed:
        await query.edit_message_text(quota_msg, parse_mode="HTML")
        return

    context.args = [topic]
    is_pro = await SubscriptionRepo.is_pro(user_id)

    msg = query.message
    try:
        await _stage_through(msg, _AI_STAGES)
        response, error = await call_crypto_ai(user_id, topic)

        if error == "rate_limited":
            text, kb = crypto_ui.get_ai_rate_limited_msg()
        elif error == "server_error":
            text, kb = crypto_ui.get_ai_server_error_msg()
        elif response:
            text, kb = crypto_ui.get_ai_response_msg(response, topic)
        else:
            text, kb = crypto_ui.get_ai_server_error_msg()

        await _edit_with_final(msg, text, kb)

        if is_pro:
            try:
                from zenith_ai_bot.repository import ConversationRepo

                await ConversationRepo.add_message(user_id, "user", topic[:2000])
                if response:
                    await ConversationRepo.add_message(user_id, "assistant", response[:2000])
            except Exception:
                pass

    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
        text, kb = crypto_ui.get_ai_server_error_msg()
        await _edit_with_final(msg, text, kb)
    except Exception as e:
        logger.error(f"AI followup error: {e}")
        text, kb = crypto_ui.get_ai_server_error_msg()
        await _edit_with_final(msg, text, kb)
