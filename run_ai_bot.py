import re
import asyncio
from fastapi import APIRouter, Request, Response
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, InlineQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import AI_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET
from zenith_ai_bot.llm_engine import process_ai_query
from zenith_ai_bot.utils import check_ai_rate_limit, sanitize_telegram_html, dispose_db_engine
from zenith_ai_bot.search import close_http_client


logger = setup_logger("SVC_AI")
router = APIRouter()

bot_app = None
task_queue = asyncio.Queue(maxsize=100) 
worker_tasks = []

async def ai_worker():
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
                    plain_text = re.sub(r'<[^>]+>', '', clean_html)
                    await context.bot.edit_message_text(
                        chat_id=placeholder_msg.chat_id, message_id=placeholder_msg.message_id, 
                        text=plain_text, disable_web_page_preview=True
                    )
            except Exception as e:
                logger.error(f"Worker Error: {e}")
                try: await context.bot.edit_message_text(chat_id=placeholder_msg.chat_id, message_id=placeholder_msg.message_id, text="❌ Connection to AI lost.")
                except Exception: pass
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
    welcome = "<b>👋 Welcome to Zenith AI!</b>\n\nUse <code>/zenith [query]</code> to start."
    await update.message.reply_text(welcome, parse_mode="HTML")
    
async def cmd_zenith(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return

    allowed, reason = await check_ai_rate_limit(update.effective_user.id)
    if not allowed: return await msg.reply_text(reason)

    text = " ".join(context.args) if context.args else ""
    if not text and msg.caption: text = msg.caption.replace("/zenith", "").strip()

    history_text = msg.reply_to_message.text or msg.reply_to_message.caption if msg.reply_to_message else None

    if not text and not history_text: 
        return await msg.reply_text("Please provide a question or reply to a message with /zenith !")
    if not text and history_text:
        text = f"Please analyze this: {history_text}"
        history_text = None

    try:
        placeholder = await msg.reply_text("⏳ Thinking...")
        task_queue.put_nowait((update, context, placeholder, text, history_text))
    except asyncio.QueueFull:
        await msg.reply_text("🚨 Zenith AI is currently at maximum capacity.")

# 🚀 Lifecycle Management
async def start_service():
    global bot_app, worker_tasks
    if not AI_BOT_TOKEN:
        logger.warning("⚠️ AI_BOT_TOKEN missing! AI Service disabled.")
        return

    bot_app = ApplicationBuilder().token(AI_BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("zenith", cmd_zenith))
    bot_app.add_handler(InlineQueryHandler(inline_query))
    
    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip('/')
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/ai/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=Update.ALL_TYPES
            )
            logger.info("✅ AI Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ AI Bot Webhook Failed: {e}")

    worker_tasks = [asyncio.create_task(ai_worker()) for _ in range(5)]
    logger.info("👷 AI Worker Pool: Online")

async def stop_service():
    # 1. Cancel active workers so they stop pulling new tasks
    for task in worker_tasks: task.cancel()
    
    # 2. 🚀 CRITICAL REFINEMENT: Flush queue and notify waiting users
    while not task_queue.empty():
        try:
            _, context, placeholder_msg, _, _ = task_queue.get_nowait()
            await context.bot.edit_message_text(
                chat_id=placeholder_msg.chat_id, 
                message_id=placeholder_msg.message_id, 
                text="🔄 <b>System Update:</b> Zenith is restarting for a cloud update. Please try your prompt again in a moment.",
                parse_mode="HTML"
            )
            task_queue.task_done()
        except Exception:
            pass
            
    # 3. Safely shutdown framework and database
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_db_engine()
    await close_http_client()

# 🚀 The Bot's Personal Webhook Router
@router.post("/webhook/ai/{secret}")
async def ai_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not bot_app: return Response(status_code=503)
    
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"AI Webhook Error: {e}")
        return Response(status_code=500)