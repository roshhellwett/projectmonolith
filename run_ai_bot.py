import os
import re
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, InlineQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import AI_BOT_TOKEN
from zenith_ai_bot.llm_engine import process_ai_query
from zenith_ai_bot.utils import check_ai_rate_limit, sanitize_telegram_html, dispose_db_engine

load_dotenv()
logger = setup_logger("AI_BOT")

# 🚀 SECURITY: Bounded Queue to prevent OOM DDOS
task_queue = asyncio.Queue(maxsize=100) 

async def ai_worker():
    """Independent worker loop for AI processing."""
    logger.info("👷 AI Worker Pool: Online")
    while True:
        try:
            update, context, placeholder_msg, text, history_text = await task_queue.get()
            
            try:
                ai_response = await process_ai_query(text, history_text)
                clean_html = sanitize_telegram_html(ai_response)
                
                if len(clean_html) > 4000: 
                    clean_html = clean_html[:4000] + "\n\n<i>[Truncated due to Telegram limits]</i>"
                    
                try:
                    await context.bot.edit_message_text(
                        chat_id=placeholder_msg.chat_id, message_id=placeholder_msg.message_id, 
                        text=clean_html, parse_mode="HTML", disable_web_page_preview=True
                    )
                except Exception as html_err:
                    logger.warning(f"HTML Parse Error, engaging fallback: {html_err}")
                    plain_text = re.sub(r'<[^>]+>', '', clean_html)
                    await context.bot.edit_message_text(
                        chat_id=placeholder_msg.chat_id, message_id=placeholder_msg.message_id, 
                        text=plain_text, disable_web_page_preview=True
                    )
            except Exception as e:
                logger.error(f"Worker Error: {e}")
                try: await context.bot.edit_message_text(chat_id=placeholder_msg.chat_id, message_id=placeholder_msg.message_id, text="❌ An error occurred connecting to the AI.")
                except: pass
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            break

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query: return
    results = [InlineQueryResultArticle(
        id="zenith_search", title=f"🔍 Ask Zenith: {query}",
        input_message_content=InputTextMessageContent(f"/zenith {query}"),
        description="Tap here to trigger high-speed AI research."
    )]
    await update.inline_query.answer(results, cache_time=5, is_personal=True)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "<b>👋 Welcome to Zenith AI!</b>\n\nI am a high-speed research and chat assistant. I can search the web, summarize YouTube videos, and answer complex questions.\n\nUse <code>/zenith [query]</code> to start."
    await update.message.reply_text(welcome_text, parse_mode="HTML")
    
async def cmd_zenith(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return

    allowed, reason = await check_ai_rate_limit(update.effective_user.id)
    if not allowed: return await msg.reply_text(reason)

    text = " ".join(context.args) if context.args else ""
    if not text and msg.caption:
        text = msg.caption.replace("/zenith", "").strip()

    history_text = None
    if msg.reply_to_message:
        history_text = msg.reply_to_message.text or msg.reply_to_message.caption

    if not text and not history_text: 
        return await msg.reply_text("Please provide a question or reply to a message with /zenith !")

    if not text and history_text:
        text = f"Please analyze this: {history_text}"
        history_text = None

    try:
        placeholder = await msg.reply_text("⏳ Thinking...")
        task_queue.put_nowait((update, context, placeholder, text, history_text))
    except asyncio.QueueFull:
        await msg.reply_text("🚨 Zenith AI is currently at maximum capacity. Please try again in a few seconds.")

# 🚀 NEW: Expose app setup for Monolith Router
async def setup_ai_app():
    if not AI_BOT_TOKEN:
        logger.error("AI_BOT_TOKEN is missing!")
        return None
    app = ApplicationBuilder().token(AI_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("zenith", cmd_zenith))
    app.add_handler(InlineQueryHandler(inline_query))
    return app