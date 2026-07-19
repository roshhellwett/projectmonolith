import contextlib
import re
import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.animation import send_loading_message
from core.llm_helpers import process_ai_query, sanitize_telegram_html
from core.logger import setup_logger
from core.subscription import SubscriptionRepo
from zenith_group_bot.flood_control import add_warning, check_bot_command_limit, get_flood_action
from zenith_group_bot.repository import SettingsRepo
from zenith_group_bot.ui import (
    get_ai_ask_help,
    get_ai_error,
    get_ai_help_msg,
    get_ai_truncation_notice,
    get_flood_cooldown,
    get_flood_kick,
    get_flood_mute,
    get_flood_warning,
)

logger = setup_logger("GROUP_AI")

# Limits
FREE_MAX_TOKENS = 512
PRO_MAX_TOKENS = 1024
FREE_MAX_RESPONSE_LENGTH = 1500

bot_app = None


def set_group_ai_bot(app):
    global bot_app
    bot_app = app


async def cmd_group_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = update.message.chat.id
    user_id = update.effective_user.id

    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active:
        return

    is_pro = await SubscriptionRepo.is_pro(user_id)
    is_flooding, msg, remaining = check_bot_command_limit(user_id, is_pro)

    if is_flooding:
        if remaining > 0:
            with contextlib.suppress(Exception):
                await update.message.reply_text(get_flood_cooldown(update.effective_user.first_name, remaining))
        else:
            warning_count = add_warning(user_id)
            action, duration = get_flood_action(warning_count, is_pro)

            if action == "warn":
                with contextlib.suppress(Exception):
                    await update.message.reply_text(get_flood_warning(update.effective_user.first_name))
            elif action == "mute":
                try:
                    await context.bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + duration)
                    await update.message.reply_text(get_flood_mute(update.effective_user.first_name, duration))
                except Exception as e:
                    logger.error(f"Failed to mute user: {e}")
            elif action == "kick":
                try:
                    await context.bot.ban_chat_member(chat_id, user_id)
                    await context.bot.unban_chat_member(chat_id, user_id)
                    await update.message.reply_text(get_flood_kick(update.effective_user.first_name))
                except Exception as e:
                    logger.error(f"Failed to kick user: {e}")
        return

    text = " ".join(context.args) if context.args else ""

    if not text:
        await update.message.reply_text(get_ai_ask_help(), parse_mode="HTML")
        return

    loading = await send_loading_message(update, context, "Thinking...")

    try:
        max_tokens = PRO_MAX_TOKENS if is_pro else FREE_MAX_TOKENS
        response = await process_ai_query(text, "", persona="default", max_tokens=max_tokens)
        clean = sanitize_telegram_html(response)

        if len(clean) > FREE_MAX_RESPONSE_LENGTH and not is_pro:
            clean = clean[:FREE_MAX_RESPONSE_LENGTH] + get_ai_truncation_notice()

        try:
            if loading:
                await loading.edit_text(clean, parse_mode="HTML", disable_web_page_preview=True)
            else:
                await update.message.reply_text(clean, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            plain = re.sub(r"<[^>]+>", "", clean)
            if loading:
                await loading.edit_text(plain, disable_web_page_preview=True)
            else:
                await update.message.reply_text(plain, disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"AI Error in group: {e}")
        if loading:
            await loading.edit_text(get_ai_error())
        else:
            await update.message.reply_text(get_ai_error())


async def cmd_group_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    is_pro = await SubscriptionRepo.is_pro(update.effective_user.id)
    msg = get_ai_help_msg(is_pro)
    await update.message.reply_text(msg, parse_mode="HTML")


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return
    if update.message.text and update.message.text.startswith("/"):
        return
    return


def register_group_ai_handlers(app):
    app.add_handler(CommandHandler("ask", cmd_group_ask))
    app.add_handler(CommandHandler("grouphelp", cmd_group_help))
    app.add_handler(CommandHandler("help", cmd_group_help))
    logger.info("Registered group AI handlers")
