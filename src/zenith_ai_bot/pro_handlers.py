import html

from telegram import Update
from telegram.ext import ContextTypes

from core.animation import edit_with_stages, send_typing_action
from core.logger import setup_logger
from zenith_ai_bot.llm_engine import process_code, process_imagine, process_research, process_summarize
from zenith_ai_bot.prompts import PERSONAS
from zenith_ai_bot.repository import ConversationRepo, UsageRepo
from zenith_ai_bot.ui import (
    get_back_button,
    get_code_no_query,
    get_confirm_persona_switch,
    get_history_keyboard,
    get_history_list_msg,
    get_imagine_help,
    get_persona_already_using,
    get_persona_help,
    get_persona_locked,
    get_persona_preview_msg,
    get_persona_unknown,
    get_pro_feature_msg,
    get_research_help,
    get_summarize_help,
    get_summarize_limit_reached,
    get_no_key_msg,
)
from zenith_ai_bot.utils import sanitize_user_input
from zenith_crypto_bot.repository import SubscriptionRepo

logger = setup_logger("AI_PRO")


async def cmd_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not context.args:
        current = await UsageRepo.get_persona(user_id)
        text = get_persona_help()
        current_info = PERSONAS.get(current, PERSONAS["default"])
        return await update.message.reply_text(
            f"<b>Current:</b> {current_info['icon']} {current_info['name']}\n\n{text}"
            + (get_persona_locked() if not is_pro else ""),
            parse_mode="HTML",
        )

    target = context.args[0].lower()

    if target not in PERSONAS:
        valid = ", ".join(PERSONAS.keys())
        return await update.message.reply_text(get_persona_unknown(valid), parse_mode="HTML")

    if target != "default" and not is_pro:
        msg, kb = get_pro_feature_msg("AI Personas")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    current = await UsageRepo.get_persona(user_id)
    if target == current:
        p = PERSONAS[target]
        return await update.message.reply_text(get_persona_already_using(p["name"]), parse_mode="HTML")

    preview_msg = get_persona_preview_msg(target)

    await update.message.reply_text(preview_msg, reply_markup=get_confirm_persona_switch(target), parse_mode="HTML")


async def cmd_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Deep Research")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    api_key = await SubscriptionRepo.get_groq_key(user_id)
    if not api_key:
        return await update.message.reply_text(
            get_no_key_msg(),
            parse_mode="HTML",
        )

    topic = " ".join(context.args) if context.args else ""
    topic = sanitize_user_input(topic)

    if not topic:
        return await update.message.reply_text(get_research_help(), parse_mode="HTML")

    msg = await update.message.reply_text(
        f"Launching deep research on: {html.escape(topic[:50])}...", parse_mode="HTML"
    )

    stages = ["Searching sources", "Analyzing data", "Synthesizing findings"]

    from zenith_ai_bot.utils import sanitize_telegram_html

    final_text = None
    try:
        await edit_with_stages(
            update, context, stages=stages, final_text="Research complete! Compiling report...", delay=0.8
        )

        result = await process_research(topic, api_key=api_key)
        clean = sanitize_telegram_html(result)

        if len(clean) > 4000:
            clean = clean[:4000] + "\n\n[Truncated due to Telegram limits]"

        final_text = clean

    except Exception as e:
        logger.error(f"Research error: {e}")
        final_text = "Research Failed\n\nAn error occurred while researching. Please try again."

    try:
        await msg.edit_text(
            final_text, reply_markup=get_back_button(), parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception:
        import re

        plain = re.sub(r"<[^>]+>", "", final_text or "")
        await msg.edit_text(plain, disable_web_page_preview=True)


async def cmd_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    msg_obj = update.message

    api_key = await SubscriptionRepo.get_groq_key(user_id)
    if not api_key:
        return await msg_obj.reply_text(
            get_no_key_msg(),
            parse_mode="HTML",
        )

    text = " ".join(context.args) if context.args else ""
    text = sanitize_user_input(text)

    if not text and msg_obj.reply_to_message:
        text = msg_obj.reply_to_message.text or msg_obj.reply_to_message.caption or ""
        text = sanitize_user_input(text)
    if not text:
        return await msg_obj.reply_text(get_summarize_help(), parse_mode="HTML")

    word_count = len(text.split())
    if not is_pro:
        usage = await UsageRepo.get_today_usage(user_id)
        if usage["summarizes"] >= 1:
            return await msg_obj.reply_text(get_summarize_limit_reached(), parse_mode="HTML")
        if word_count > 500:
            text = " ".join(text.split()[:500])
    else:
        if word_count > 4000:
            text = " ".join(text.split()[:4000])

    await UsageRepo.increment_summarize(user_id)
    placeholder = await msg_obj.reply_text("Summarizing...", parse_mode="HTML")

    from zenith_ai_bot.utils import sanitize_telegram_html

    result = await process_summarize(text, api_key=api_key)
    clean = sanitize_telegram_html(result)
    if len(clean) > 4000:
        clean = clean[:4000] + "\n\n[Truncated]"

    try:
        await placeholder.edit_text(clean, reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        import re

        plain = re.sub(r"<[^>]+>", "", clean)
        await placeholder.edit_text(plain)


async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Code Generator")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    api_key = await SubscriptionRepo.get_groq_key(user_id)
    if not api_key:
        return await update.message.reply_text(
            get_no_key_msg(),
            parse_mode="HTML",
        )

    description = " ".join(context.args) if context.args else ""
    description = sanitize_user_input(description)

    if not description:
        return await update.message.reply_text(get_code_no_query(), parse_mode="HTML")

    placeholder = await update.message.reply_text("Generating code...", parse_mode="HTML")

    from zenith_ai_bot.utils import sanitize_telegram_html

    result = await process_code(description, api_key=api_key)
    clean = sanitize_telegram_html(result)
    if len(clean) > 4000:
        clean = clean[:4000] + "\n\n[Truncated]"

    try:
        await placeholder.edit_text(clean, reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        import re

        plain = re.sub(r"<[^>]+>", "", clean)
        await placeholder.edit_text(plain)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Chat History")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    history = await ConversationRepo.get_history(user_id, limit=10)
    text = get_history_list_msg(history)
    kb = get_history_keyboard() if history else get_back_button()
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def cmd_imagine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Image Prompt Crafter")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    api_key = await SubscriptionRepo.get_groq_key(user_id)
    if not api_key:
        return await update.message.reply_text(
            get_no_key_msg(),
            parse_mode="HTML",
        )

    description = " ".join(context.args) if context.args else ""
    description = sanitize_user_input(description)

    if not description:
        return await update.message.reply_text(get_imagine_help(), parse_mode="HTML")

    await send_typing_action(update, context)

    placeholder = await update.message.reply_text("Crafting optimized prompts...", parse_mode="HTML")

    from zenith_ai_bot.utils import sanitize_telegram_html

    result = await process_imagine(description, api_key=api_key)
    clean = sanitize_telegram_html(result)
    if len(clean) > 4000:
        clean = clean[:4000] + "\n\n[Truncated]"

    try:
        await placeholder.edit_text(clean, reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        import re

        plain = re.sub(r"<[^>]+>", "", clean)
        await placeholder.edit_text(plain)
