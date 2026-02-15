import os
import asyncio
from uuid import uuid4
from dotenv import load_dotenv
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, InlineQueryHandler, filters, ContextTypes

from core.logger import setup_logger
from core.config import AI_BOT_TOKEN
from zenith_ai_bot.llm_engine import process_ai_query, transcribe_voice
from zenith_ai_bot.utils import check_ai_rate_limit, sanitize_telegram_html, is_file_allowed, extract_text_from_pdf, convert_ogg_to_wav, dispose_db_engine

load_dotenv()
logger = setup_logger("AI_BOT")

task_queue = asyncio.Queue()

async def worker(app_context):
    while True:
        try:
            update, context, placeholder_msg, text, image_bytes, history_text = await task_queue.get()
            try:
                ai_response = await process_ai_query(text, image_bytes, history_text)
                clean_html = sanitize_telegram_html(ai_response)
                if len(clean_html) > 4000: clean_html = clean_html[:4000] + "\n\n<i>[Truncated]</i>"
                    
                await context.bot.edit_message_text(chat_id=placeholder_msg.chat_id, message_id=placeholder_msg.message_id, text=clean_html, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Worker Error: {e}")
                try: await context.bot.edit_message_text(chat_id=placeholder_msg.chat_id, message_id=placeholder_msg.message_id, text="❌ An error occurred formatting the AI report.")
                except: pass
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            break

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption or ""
    if "/zenithai" not in caption.lower(): return

    allowed, reason = await check_ai_rate_limit(update.effective_user.id)
    if not allowed: return await update.message.reply_text(reason)

    doc = update.message.document
    if doc.mime_type != "application/pdf":
        return await update.message.reply_text("⚠️ I can only read PDF documents, images, and text.")
    if not is_file_allowed(doc.file_size):
        return await update.message.reply_text("📁 This PDF is too large! My limit is 20MB.")

    placeholder = await update.message.reply_text("📥 Reading PDF... (Scanning first 5 pages)")
    file = await context.bot.get_file(doc.file_id)
    
    # Bug Fix: Safe Unique Identifier Generation to prevent collision
    path = f"temp_{uuid4().hex}.pdf"
    
    try:
        await file.download_to_drive(path)
        text = await asyncio.to_thread(extract_text_from_pdf, path)

        if text == "ERROR:ENCRYPTED": return await placeholder.edit_text("🔒 This PDF is encrypted. I cannot read it.")
        if text == "ERROR:EMPTY": return await placeholder.edit_text("⚠️ This PDF contains no readable text (scanned image).")
        if text == "ERROR:BROKEN": return await placeholder.edit_text("❌ An error occurred parsing this PDF file.")

        user_query = caption.replace("/zenithai", "").strip() or "Please summarize this document."
        await task_queue.put((update, context, placeholder, user_query, None, text))
    finally:
        if os.path.exists(path): os.remove(path)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_private = update.effective_chat.type == "private"
    is_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    if not is_private and not is_reply: return
        
    allowed, reason = await check_ai_rate_limit(update.effective_user.id)
    if not allowed: return await update.message.reply_text(reason)

    voice = update.message.voice
    if voice.duration > 60: return await update.message.reply_text("⏳ This voice note is too long! Keep it under 60s.")

    placeholder = await update.message.reply_text("🎙️ Transcribing voice note...")
    file = await context.bot.get_file(voice.file_id)
    
    ogg_path = f"temp_{uuid4().hex}.ogg"
    wav_path = ""
    
    try:
        await file.download_to_drive(ogg_path)
        wav_path = await asyncio.to_thread(convert_ogg_to_wav, ogg_path)
        
        if not wav_path:
            return await placeholder.edit_text("❌ Error converting audio file. (Missing FFmpeg)")
            
        text = await transcribe_voice(wav_path)
        
        if text == "ERROR:GIBBERISH": return await placeholder.edit_text("⚠️ Audio quality too low to understand.")
        elif text.startswith("ERROR:"): return await placeholder.edit_text("📡 Audio transcription servers are offline.")
        
        history_text = None
        if update.message.reply_to_message:
            history_text = update.message.reply_to_message.text or update.message.reply_to_message.caption

        await placeholder.edit_text(f"📝 <b>Transcribed:</b> <i>\"{text}\"</i>\n\n🔍 <b>Researching...</b>", parse_mode="HTML")
        await task_queue.put((update, context, placeholder, text, None, history_text))
    finally:
        if os.path.exists(ogg_path): os.remove(ogg_path)
        if wav_path and os.path.exists(wav_path): os.remove(wav_path)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query: return
    results = [InlineQueryResultArticle(
        id=str(uuid4()), title=f"🔍 Ask Zenith: {query}",
        input_message_content=InputTextMessageContent(f"/zenithai {query}"),
        description="Tap here to trigger high-speed AI research. (Safe Mode)"
    )]
    await update.inline_query.answer(results, cache_time=5, is_personal=True)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "<b>👋 Welcome to Zenith Multimodal AI!</b>\n\nI can process Text, Web Links, PDFs, Images, and Voice Notes.\n\nUse /zenithai [query] to start researching."
    await update.message.reply_text(welcome_text, parse_mode="HTML")
    
async def cmd_zenithai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    allowed, reason = await check_ai_rate_limit(update.effective_user.id)
    if not allowed: return await update.message.reply_text(reason)

    text = " ".join(context.args) if context.args else (update.message.caption.replace("/zenithai", "").strip() if update.message.caption else "")
    if not text and not update.message.photo: return await update.message.reply_text("Please provide a question, link, or image!")

    image_bytes = None
    if update.message.photo:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_bytes = await file.download_as_bytearray()

    history_text = None
    if update.message.reply_to_message:
        history_text = update.message.reply_to_message.text or update.message.reply_to_message.caption

    placeholder = await update.message.reply_text("⏳ Processing your research query...")
    await task_queue.put((update, context, placeholder, text, image_bytes, history_text))

async def main():
    if not AI_BOT_TOKEN:
        logger.error("AI_BOT_TOKEN is missing!")
        return

    app = ApplicationBuilder().token(AI_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("zenithai", cmd_zenithai))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    
    workers = [asyncio.create_task(worker(app)) for _ in range(3)]

    logger.info("🧠 ZENITH MULTIMODAL AGENT: ONLINE")
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("🛑 Shutting down AI Bot Engine...")
        for w in workers: w.cancel()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await dispose_db_engine()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process Interrupted.")