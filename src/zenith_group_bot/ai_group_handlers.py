import contextlib
import re
import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.llm_helpers import process_ai_query, sanitize_telegram_html
from core.logger import setup_logger
from core.subscription import SubscriptionRepo
from zenith_group_bot.flood_control import (
    add_warning,
    check_bot_command_limit,
    get_flood_action,
)
from zenith_group_bot.repository import SettingsRepo

logger = setup_logger("GROUP_AI")

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
                await update.message.reply_text(
                    f"⏳ {update.effective_user.first_name}, please wait {remaining}s between commands.",
                    parse_mode="HTML",
                )
        else:
            warning_count = add_warning(user_id)
            action, duration = get_flood_action(warning_count, is_pro)

            if action == "warn":
                with contextlib.suppress(Exception):
                    await update.message.reply_text(
                        f"⚠️ {update.effective_user.first_name}, you're sending too many commands!", parse_mode="HTML"
                    )
            elif action == "mute":
                try:
                    await context.bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + duration)
                    await update.message.reply_text(
                        f"🔇 {update.effective_user.first_name} has been muted for {duration//3600}h due to spam.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to mute user: {e}")
            elif action == "kick":
                try:
                    await context.bot.ban_chat_member(chat_id, user_id)
                    await context.bot.unban_chat_member(chat_id, user_id)
                    await update.message.reply_text(
                        f"🚫 {update.effective_user.first_name} has been removed for repeated spam.", parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to kick user: {e}")
        return

    text = " ".join(context.args) if context.args else ""

    if not text:
        await update.message.reply_text(
            "💬 <b>Ask Zenith AI</b>\n\n"
            "Usage: <code>/ask [your question]</code>\n\n"
            "Example: <code>/ask What's the weather like today?</code>",
            parse_mode="HTML",
        )
        return

    msg = await update.message.reply_text("<i>Thinking...</i>", parse_mode="HTML")

    try:
        max_tokens = 1024 if is_pro else 512
        response = await process_ai_query(text, "", persona="default", max_tokens=max_tokens)
        clean = sanitize_telegram_html(response)

        if len(clean) > 1500 and not is_pro:
            clean = clean[:1500] + "\n\n<i>[Upgrade to Pro for longer responses]</i>"

        try:
            await msg.edit_text(clean, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            plain = re.sub(r"<[^>]+>", "", clean)
            await msg.edit_text(plain, disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"AI Error in group: {e}")
        await msg.edit_text("❌ AI service temporarily unavailable.")


async def cmd_group_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    is_pro = await SubscriptionRepo.is_pro(update.effective_user.id)

    free_features = (
        "📖 <b>GROUP BOT HELP</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>🤖 AI Commands:</b>\n"
        "• /ask [question] - Ask AI anything\n"
        "• /persona - View available personas (Pro)\n\n"
        "<b>💰 Crypto Commands:</b>\n"
        "• /price [coin] - Get price info\n"
        "• /alert [coin] [above/below] [price] - Set alert (Pro)\n\n"
        "<b>🛡️ Flood Protection:</b>\n"
        "• Free: 5 commands/min, 15s cooldown\n"
        "• Pro: 20 commands/min, 5s cooldown"
    )

    pro_features = (
        "\n\n<b>💎 PRO Features:</b>\n"
        "• Unlimited AI queries\n"
        "• All 7 AI personas\n"
        "• Deep research\n"
        "• Code generator\n"
        "• Price alerts\n"
        "• Wallet tracking"
    )

    await update.message.reply_text(free_features + (pro_features if is_pro else ""), parse_mode="HTML")


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
