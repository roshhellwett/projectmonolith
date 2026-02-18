import html
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, RetryAfter
from telegram.ext import ContextTypes

from core.logger import setup_logger
from core.animation import send_typing_action, edit_with_stages
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_ai_bot.repository import ConversationRepo, UsageRepo
from zenith_ai_bot.llm_engine import process_research, process_summarize, process_code, process_imagine
from zenith_ai_bot.prompts import PERSONAS
from zenith_ai_bot.ui import (
    get_back_button, get_history_keyboard, get_confirm_clear_history,
    get_confirm_clear_history_msg, get_persona_preview_msg, get_confirm_persona_switch,
    get_pro_feature_msg, get_limit_reached_msg, get_generating_response_msg,
)

logger = setup_logger("AI_PRO")


async def cmd_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not context.args:
        current = await UsageRepo.get_persona(user_id)
        current_info = PERSONAS.get(current, PERSONAS["default"])
        
        personas_list = "\n".join(
            f"  {'✅' if k == current else '•'} <code>{k}</code> — {v['icon']} {v['name']}"
            for k, v in PERSONAS.items()
        )
        
        lock = "" if is_pro else "\n\n🔒 <i>Pro required for non-default personas.</i>"
        
        return await update.message.reply_text(
            f"🎭 <b>AI Personas</b>\n\n"
            f"<b>Current:</b> {current_info['icon']} {current_info['name']}\n\n"
            f"{personas_list}{lock}\n\n"
            f"<b>Usage:</b> <code>/persona [name]</code>\n\n"
            f"<i>Example: /persona coder</i>",
            parse_mode="HTML",
        )

    target = context.args[0].lower()
    
    if target not in PERSONAS:
        valid = ", ".join(PERSONAS.keys())
        return await update.message.reply_text(
            f"⚠️ <b>Unknown Persona</b>\n\n"
            f"Available personas: {valid}\n\n"
            f"<b>Usage:</b> <code>/persona coder</code>",
            parse_mode="HTML",
        )

    if target != "default" and not is_pro:
        msg, kb = get_pro_feature_msg("AI Personas")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    current = await UsageRepo.get_persona(user_id)
    if target == current:
        p = PERSONAS[target]
        return await update.message.reply_text(
            f"ℹ️ <b>Already Using</b>\n\n"
            f"You're already using {p['icon']} <b>{p['name']}</b> persona.",
            parse_mode="HTML",
        )

    p = PERSONAS[target]
    preview_msg = get_persona_preview_msg(target)
    
    await update.message.reply_text(
        preview_msg,
        reply_markup=get_confirm_persona_switch(target),
        parse_mode="HTML",
    )


async def cmd_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Deep Research")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    topic = " ".join(context.args) if context.args else ""
    if not topic:
        return await update.message.reply_text(
            "🔬 <b>Deep Research</b>\n\n"
            "<b>Format:</b> <code>/research [TOPIC]</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/research AI regulation in Europe 2025</code>\n"
            "• <code>/research best programming languages for fintech</code>\n"
            "• <code>/research electric vehicle market trends</code>\n\n"
            "<i>💡 Tip: Be specific for better results</i>",
            parse_mode="HTML",
        )

    msg = await update.message.reply_text(
        f"🔬 <i>Launching deep research on: {html.escape(topic[:50])}...</i>",
        parse_mode="HTML",
    )

    stages = [
        "Searching sources",
        "Analyzing data",
        "Synthesizing findings",
    ]
    
    from zenith_ai_bot.utils import sanitize_telegram_html
    
    final_text = None
    try:
        await edit_with_stages(
            update, context,
            stages=stages,
            final_text="🔬 <i>Research complete! Compiling report...</i>",
            delay=0.8
        )
        
        result = await process_research(topic)
        clean = sanitize_telegram_html(result)
        
        if len(clean) > 4000:
            clean = clean[:4000] + "\n\n<i>[Truncated due to Telegram limits]</i>"
        
        final_text = clean
        
    except Exception as e:
        logger.error(f"Research error: {e}")
        final_text = "⚠️ <b>Research Failed</b>\n\nAn error occurred while researching. Please try again."
    
    try:
        await msg.edit_text(final_text, reply_markup=get_back_button(), parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        import re
        plain = re.sub(r'<[^>]+>', '', final_text or "")
        await msg.edit_text(plain, disable_web_page_preview=True)


async def cmd_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    msg = update.message

    text = " ".join(context.args) if context.args else ""
    if not text and msg.reply_to_message:
        text = msg.reply_to_message.text or msg.reply_to_message.caption or ""
    if not text:
        return await msg.reply_text(
            "📝 <b>Text Summarizer</b>\n\n"
            "<b>Usage:</b>\n"
            "• <code>/summarize [text]</code>\n"
            "• Reply to any message with <code>/summarize</code>",
            parse_mode="HTML",
        )

    word_count = len(text.split())
    if not is_pro:
        usage = await UsageRepo.get_today_usage(user_id)
        if usage["summarizes"] >= 1:
            return await msg.reply_text(
                "⚠️ <b>Daily limit reached</b> (1/day Free tier).\n\n"
                "💎 Upgrade to <b>Zenith Pro</b> for unlimited summaries.\n"
                "<code>/activate [YOUR_KEY]</code>",
                parse_mode="HTML",
            )
        if word_count > 500:
            text = " ".join(text.split()[:500])
    else:
        if word_count > 4000:
            text = " ".join(text.split()[:4000])

    await UsageRepo.increment_summarize(user_id)
    placeholder = await msg.reply_text("<i>Summarizing...</i>", parse_mode="HTML")

    from zenith_ai_bot.utils import sanitize_telegram_html
    result = await process_summarize(text)
    clean = sanitize_telegram_html(result)
    if len(clean) > 4000:
        clean = clean[:4000] + "\n\n<i>[Truncated]</i>"

    try:
        await placeholder.edit_text(clean, reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        import re
        plain = re.sub(r'<[^>]+>', '', clean)
        await placeholder.edit_text(plain)


async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        return await update.message.reply_text(
            "🔒 <b>Pro Feature: Code Generator</b>\n\n"
            "Get production-ready code from natural language descriptions.\n"
            "Upgrade to <b>Zenith Pro</b> to unlock.\n\n"
            "<code>/activate [YOUR_KEY]</code>",
            parse_mode="HTML",
        )

    description = " ".join(context.args) if context.args else ""
    if not description:
        return await update.message.reply_text(
            "💻 <b>Code Generator</b>\n\n"
            "<b>Format:</b> <code>/code [DESCRIPTION]</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/code Python FastAPI REST endpoint for user auth with JWT</code>\n"
            "• <code>/code React component for a sortable data table</code>\n"
            "• <code>/code Bash script to backup PostgreSQL database</code>",
            parse_mode="HTML",
        )

    placeholder = await update.message.reply_text(
        "💻 <i>Generating code...</i>",
        parse_mode="HTML",
    )

    from zenith_ai_bot.utils import sanitize_telegram_html
    result = await process_code(description)
    clean = sanitize_telegram_html(result)
    if len(clean) > 4000:
        clean = clean[:4000] + "\n\n<i>[Truncated]</i>"

    try:
        await placeholder.edit_text(clean, reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        import re
        plain = re.sub(r'<[^>]+>', '', clean)
        await placeholder.edit_text(plain)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Chat History")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    history = await ConversationRepo.get_history(user_id, limit=10)
    if not history:
        return await update.message.reply_text(
            "💬 <b>Chat Memory</b>\n\n"
            "No conversation history yet.\n\n"
            "<i>Start chatting with /zenith and I'll remember the context.</i>",
            parse_mode="HTML",
        )

    lines = ["<b>💬 CHAT MEMORY</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for msg in history[-6:]:
        role_icon = "👤" if msg.role == "user" else "🤖"
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        lines.append(f"{role_icon} <i>{html.escape(preview)}</i>")

    count = await ConversationRepo.count_messages(user_id)
    lines.append(f"\n<i>{count} messages stored · Last 10 used for context</i>")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=get_history_keyboard(),
        parse_mode="HTML",
    )

    history = await ConversationRepo.get_history(user_id, limit=10)
    if not history:
        return await update.message.reply_text(
            "💬 <b>Chat Memory</b>\n\nNo conversation history yet.\n"
            "<i>Start chatting with /zenith and I'll remember the context.</i>",
            parse_mode="HTML",
        )

    lines = ["<b>💬 CHAT MEMORY</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for msg in history[-6:]:
        role_icon = "👤" if msg.role == "user" else "🤖"
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        lines.append(f"{role_icon} <i>{html.escape(preview)}</i>")

    count = await ConversationRepo.count_messages(user_id)
    lines.append(f"\n<i>{count} messages stored · Last 10 used for context</i>")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=get_history_keyboard(),
        parse_mode="HTML",
    )


async def cmd_imagine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Image Prompt Crafter")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    description = " ".join(context.args) if context.args else ""
    if not description:
        return await update.message.reply_text(
            "🎨 <b>Image Prompt Crafter</b>\n\n"
            "<b>Format:</b> <code>/imagine [DESCRIPTION]</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/imagine a cyberpunk city at sunset with neon lights</code>\n"
            "• <code>/imagine portrait of an astronaut in a flower field</code>\n"
            "• <code>/imagine minimalist logo for a tech startup</code>\n\n"
            "<i>💡 Tip: Be descriptive for better prompts</i>",
            parse_mode="HTML",
        )

    await send_typing_action(update, context)
    
    placeholder = await update.message.reply_text(
        "🎨 <i>Crafting optimized prompts...</i>",
        parse_mode="HTML",
    )

    from zenith_ai_bot.utils import sanitize_telegram_html
    result = await process_imagine(description)
    clean = sanitize_telegram_html(result)
    if len(clean) > 4000:
        clean = clean[:4000] + "\n\n<i>[Truncated]</i>"

    try:
        await placeholder.edit_text(clean, reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        import re
        plain = re.sub(r'<[^>]+>', '', clean)
        await placeholder.edit_text(plain)
