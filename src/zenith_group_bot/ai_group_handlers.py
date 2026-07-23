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
MAX_TOKENS = 4096
from core.llm_fallback import AIExecutionEngine
import json

MAX_RESPONSE_LENGTH = 4000

bot_app = None


def set_group_ai_bot(app):
    global bot_app
    bot_app = app


async def scan_ai_spam_shield(text: str, api_key: str, group_name: str = "") -> tuple[bool, str, int]:
    """Analyze group chat message for zero-day phishing drops, drainer contracts, and scam raids."""
    if not api_key or len(text) < 10:
        return False, "", 0

    prompt = f"""Group Chat Message in '{group_name}':
"{text}"

Analyze if this message is a scam raid, crypto phishing link, wallet drainer drop, disguised airdrop scam, or malicious spam targeting community members.
Output strictly raw valid JSON with two keys:
1. "is_scam": boolean (true if malicious/scam/phishing, false if normal conversation or legitimate inquiry).
2. "reason": string concise explanation if true (or empty if false).
3. "risk_score": integer 0 to 100."""

    try:
        resp = await AIExecutionEngine.execute(
            messages=[
                {"role": "system", "content": "You are Zenith Security Shield, an AI zero-day crypto scam detector. You protect Telegram communities from phishing, wallet drainers, fake airdrop drops, and malicious raid spam."},
                {"role": "user", "content": prompt},
            ],
            api_key=api_key,
            preferred_model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=256,
        )

        # Removed bad track tokens here, handled via return value

        if not resp.is_error and resp.content:
            raw = resp.content.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            data = json.loads(raw.strip())
            is_scam = bool(data.get("is_scam", False))
            reason = str(data.get("reason", "Zero-day scam drop"))
            risk = int(data.get("risk_score", 0))
            
            # Simple token estimation
            token_est = len(prompt) // 4 + len(raw) // 4
            return is_scam, reason, risk, token_est
    except Exception as e:
        logger.debug(f"AI Spam Shield scan error: {e}")
    return False, "", 0, 0


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

    if not getattr(settings, "groq_api_key", None):
        await update.message.reply_text("⚠️ The group admin has not configured the AI API key yet. They must DM me with /setkey to activate AI features.", parse_mode="HTML")
        return

    loading = await send_loading_message(update, context, "Thinking...")

    try:
        from zenith_ai_bot.repository import UsageRepo

        preferred_model = await UsageRepo.get_selected_model(user_id)
        
        resp = await AIExecutionEngine.execute(
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant in a Telegram group chat. Be concise and helpful."},
                {"role": "user", "content": text}
            ],
            api_key=settings.groq_api_key,
            preferred_model=preferred_model,
            temperature=0.7,
            max_tokens=MAX_TOKENS,
        )
        clean = sanitize_telegram_html(resp.get_formatted_content())
        
        if not resp.is_error and resp.content:
            tokens = len(text) // 4 + len(resp.content) // 4
            await SettingsRepo.record_tokens(chat_id, tokens)

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
