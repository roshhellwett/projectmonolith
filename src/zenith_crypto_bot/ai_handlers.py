import contextlib

from telegram import Update
from telegram.ext import ContextTypes

from core.animation import edit_with_stages, send_loading_message, send_typing_action
from core.logger import setup_logger
from zenith_crypto_bot import ui as crypto_ui
from zenith_crypto_bot.ai_engine import call_crypto_ai, validate_groq_key
from zenith_crypto_bot.repository import SubscriptionRepo

logger = setup_logger("CRYPTO_AI_HANDLER")


async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    api_key = await SubscriptionRepo.get_groq_key(user_id)
    if not api_key:
        text, kb = crypto_ui.get_ai_no_key_msg()
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return

    query = " ".join(context.args) if context.args else ""
    if not query:
        text, kb = crypto_ui.get_ai_empty_query_msg()
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return

    is_pro = await SubscriptionRepo.is_pro(user_id)
    stages = ["Reading your data", "Checking markets", "Thinking"]
    await send_typing_action(update, context)
    placeholder = await send_loading_message(update, context, "Processing...")
    try:
        await edit_with_stages(update, context, stages, final_text="Generating your answer...")
        response, error = await call_crypto_ai(api_key, user_id, query)
        if error == "rate_limited":
            text, kb = crypto_ui.get_ai_rate_limited_msg()
        elif error == "invalid_key":
            text, kb = crypto_ui.get_ai_invalid_key_msg()
        elif error == "server_error":
            text, kb = crypto_ui.get_ai_server_error_msg()
        elif response:
            text, kb = crypto_ui.get_ai_response_msg(response, query)
        else:
            text, kb = crypto_ui.get_ai_server_error_msg()

        try:
            await placeholder.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            import re

            plain = re.sub(r"<[^>]+>", "", text)
            await placeholder.edit_text(plain, disable_web_page_preview=True)

        if is_pro:
            try:
                from zenith_ai_bot.repository import ConversationRepo

                await ConversationRepo.add_message(user_id, "user", query[:2000])
                if response:
                    await ConversationRepo.add_message(user_id, "assistant", response[:2000])
            except Exception:
                pass

    except Exception as e:
        logger.error(f"AI handler error: {e}")
        text, kb = crypto_ui.get_ai_server_error_msg()
        with contextlib.suppress(Exception):
            await placeholder.edit_text(text, reply_markup=kb, parse_mode="HTML")


async def cmd_setkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /setkey gsk_your_groq_api_key")
        return
    api_key = context.args[0].strip()
    valid, msg = await validate_groq_key(api_key)
    if not valid:
        await update.message.reply_text(f"Invalid Key\n\n{msg}\n\nGet a free key at console.groq.com")
        return
    await SubscriptionRepo.set_groq_key(update.effective_user.id, api_key)
    text, kb = crypto_ui.get_ai_key_set_success_msg()
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def cmd_mykey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    key = await SubscriptionRepo.get_groq_key(user_id)
    text, kb = crypto_ui.get_ai_key_status_msg(key is not None)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def cmd_delkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await SubscriptionRepo.delete_groq_key(update.effective_user.id)
    text, kb = crypto_ui.get_ai_key_deleted_msg()
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def handle_ai_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("ai_followup_"):
        return
    topic = data.replace("ai_followup_", "", 1)
    context.args = [topic]
    user_id = query.from_user.id
    api_key = await SubscriptionRepo.get_groq_key(user_id)
    if not api_key:
        text, kb = crypto_ui.get_ai_no_key_msg()
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return

    is_pro = await SubscriptionRepo.is_pro(user_id)
    stages = ["Reading your data", "Checking markets", "Thinking"]
    placeholder = await send_loading_message(update, context, "Processing...")
    try:
        await edit_with_stages(update, context, stages, final_text="Generating your answer...")
        response, error = await call_crypto_ai(api_key, user_id, topic)
        if error == "rate_limited":
            text, kb = crypto_ui.get_ai_rate_limited_msg()
        elif error == "invalid_key":
            text, kb = crypto_ui.get_ai_invalid_key_msg()
        elif error == "server_error":
            text, kb = crypto_ui.get_ai_server_error_msg()
        elif response:
            text, kb = crypto_ui.get_ai_response_msg(response, topic)
        else:
            text, kb = crypto_ui.get_ai_server_error_msg()

        try:
            await placeholder.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            import re

            plain = re.sub(r"<[^>]+>", "", text)
            await placeholder.edit_text(plain, disable_web_page_preview=True)

        if is_pro:
            try:
                from zenith_ai_bot.repository import ConversationRepo

                await ConversationRepo.add_message(user_id, "user", topic[:2000])
                if response:
                    await ConversationRepo.add_message(user_id, "assistant", response[:2000])
            except Exception:
                pass
    except Exception as e:
        logger.error(f"AI followup error: {e}")
        text, kb = crypto_ui.get_ai_server_error_msg()
        with contextlib.suppress(Exception):
            await placeholder.edit_text(text, reply_markup=kb, parse_mode="HTML")
