import re
import html
import asyncio
from fastapi import APIRouter, Request, Response
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, InlineQueryHandler,
    CallbackQueryHandler, ContextTypes,
)

from core.logger import setup_logger
from core.config import AI_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.repository import SubscriptionRepo
from zenith_ai_bot.repository import (
    init_ai_db, dispose_ai_engine, ConversationRepo, UsageRepo,
)
from zenith_ai_bot.llm_engine import process_ai_query
from zenith_ai_bot.utils import check_ai_rate_limit, sanitize_telegram_html
from zenith_ai_bot.search import close_http_client
from zenith_ai_bot.prompts import PERSONAS
from zenith_ai_bot.ui import (
    get_ai_dashboard, get_persona_keyboard, get_back_button, get_history_keyboard,
)
from zenith_ai_bot.pro_handlers import (
    cmd_persona, cmd_research, cmd_summarize, cmd_code, cmd_history, cmd_imagine,
)

logger = setup_logger("SVC_AI")
router = APIRouter()

bot_app = None
task_queue = asyncio.Queue(maxsize=100)
worker_tasks = []


async def ai_worker():
    while True:
        try:
            update, context, placeholder_msg, text, history_text, is_pro, persona, history = await task_queue.get()
            try:
                max_tokens = 4096 if is_pro else 1024
                ai_response = await process_ai_query(
                    text, history_text,
                    persona=persona, max_tokens=max_tokens,
                    history=history,
                )
                clean_html = sanitize_telegram_html(ai_response)

                if len(clean_html) > 4000:
                    clean_html = clean_html[:4000] + "\n\n<i>[Truncated due to Telegram limits]</i>"

                if is_pro:
                    await ConversationRepo.add_message(update.effective_user.id, "user", text)
                    await ConversationRepo.add_message(update.effective_user.id, "assistant", ai_response[:2000])

                try:
                    await context.bot.edit_message_text(
                        chat_id=placeholder_msg.chat_id,
                        message_id=placeholder_msg.message_id,
                        text=clean_html, parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception:
                    plain_text = re.sub(r'<[^>]+>', '', clean_html)
                    await context.bot.edit_message_text(
                        chat_id=placeholder_msg.chat_id,
                        message_id=placeholder_msg.message_id,
                        text=plain_text, disable_web_page_preview=True,
                    )
            except Exception as e:
                logger.error(f"Worker Error: {e}")
                try:
                    await context.bot.edit_message_text(
                        chat_id=placeholder_msg.chat_id,
                        message_id=placeholder_msg.message_id,
                        text="❌ Connection to AI lost.",
                    )
                except Exception:
                    pass
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            break


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    usage = await UsageRepo.get_today_usage(user_id)
    persona = usage.get("persona", "default")
    days_left = await SubscriptionRepo.get_days_left(user_id)

    p = PERSONAS.get(persona, PERSONAS["default"])
    if is_pro:
        status = f"💎 <b>PRO ACTIVE</b> — {days_left} day{'s' if days_left != 1 else ''} remaining"
    else:
        status = "🆓 <b>FREE TIER</b> — Upgrade for unlimited power"

    welcome = (
        f"<b>{p['icon']} ZENITH AI TERMINAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{status}\n"
        f"<b>Persona:</b> {p['name']}\n"
        f"<b>Queries Today:</b> {usage['queries']}/{'60' if is_pro else '5'}\n\n"
        f"<b>Commands:</b>\n"
        f"• <code>/zenith [question]</code> — Ask anything\n"
        f"• <code>/persona [name]</code> — Switch AI personality\n"
        f"• <code>/research [topic]</code> — Deep research 🔒\n"
        f"• <code>/summarize [text]</code> — Summarize text\n"
        f"• <code>/code [desc]</code> — Code generator 🔒\n"
        f"• <code>/imagine [desc]</code> — Image prompts 🔒\n"
        f"• <code>/history</code> — Chat memory 🔒\n\n"
        f"<i>🔒 = Pro Required | Use /help for full guide</i>"
    )
    await update.message.reply_text(
        welcome,
        reply_markup=get_ai_dashboard(is_pro, persona, usage),
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    
    help_text = (
        "📖 <b>ZENITH AI BOT - FULL GUIDE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "<b>🤖 MAIN COMMANDS</b>\n"
        "• <code>/start</code> - Start the bot & see dashboard\n"
        "• <code>/zenith [question]</code> - Ask AI anything\n"
        "• <code>/help</code> - Show this help message\n\n"
        
        "<b>🎭 PERSONAS</b>\n"
        "• <code>/persona</code> - View/switch AI personality\n"
        "  Available: Default, Coder, Writer, Analyst, Tutor, Debate, Roast\n\n"
        
        "<b>📝 TEXT TOOLS</b>\n"
        "• <code>/summarize [text]</code> - Summarize long text\n"
        "  (Reply to a message with /summarize)\n\n"
        
        "<b>💻 PRO FEATURES (₹149/month)</b>\n"
        "• <code>/research [topic]</code> - Deep research on any topic\n"
        "• <code>/code [description]</code> - Generate code in any language\n"
        "• <code>/imagine [description]</code> - Create image prompts\n"
        "• <code>/history</code> - View chat memory\n\n"
        
        "<b>💎 PRO BENEFITS</b>\n"
        "• Unlimited messages\n"
        "• 7 AI personas\n"
        "• Longer responses\n"
        "• Priority support\n\n"
        
        "<b>📱 GROUP USAGE</b>\n"
        "Add bot to groups and use:\n"
        "• <code>/ask [question]</code> - Ask AI in group\n"
        "• <code>/grouphelp</code> - Group-specific help\n\n"
        
        "<b>💳 UPGRADE TO PRO</b>\n"
        "Contact @admin to get your activation key!\n"
        "Price: ₹149/month (India)"
    )
    
    keyboard = [
        [InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
        [InlineKeyboardButton("🔙 Back", callback_data="ai_main_menu")]
    ]
    
    await update.message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def cmd_zenith(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return

    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    allowed, reason = await check_ai_rate_limit(user_id, is_pro)
    if not allowed:
        return await msg.reply_text(reason, parse_mode="HTML")

    text = " ".join(context.args) if context.args else ""
    if not text and msg.caption:
        text = msg.caption.replace("/zenith", "").strip()

    history_text = (msg.reply_to_message.text or msg.reply_to_message.caption) if msg.reply_to_message else None

    if not text and not history_text:
        return await msg.reply_text("Please provide a question or reply to a message with /zenith !")
    if not text and history_text:
        text = f"Please analyze this: {history_text}"
        history_text = None

    await UsageRepo.increment_queries(user_id)

    persona = await UsageRepo.get_persona(user_id) if is_pro else "default"
    conversation_history = await ConversationRepo.get_history(user_id, limit=10) if is_pro else None

    p = PERSONAS.get(persona, PERSONAS["default"])
    try:
        placeholder = await msg.reply_text(f"{p['icon']} <i>Thinking...</i>", parse_mode="HTML")
        task_queue.put_nowait((update, context, placeholder, text, history_text, is_pro, persona, conversation_history))
    except asyncio.QueueFull:
        await msg.reply_text("🚨 Zenith AI is currently at maximum capacity.")


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "🔑 <b>Activate Pro</b>\n\n"
            "<b>Usage:</b> <code>/activate [YOUR_KEY]</code>\n\n"
            "<i>Contact admin to purchase a Pro key.</i>",
            parse_mode="HTML",
        )
    key = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key)
    await update.message.reply_text(msg, parse_mode="HTML")


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    try:
        if query.data == "ai_main_menu":
            usage = await UsageRepo.get_today_usage(user_id)
            persona = usage.get("persona", "default")
            days_left = await SubscriptionRepo.get_days_left(user_id)
            p = PERSONAS.get(persona, PERSONAS["default"])

            if is_pro:
                status = f"💎 <b>PRO ACTIVE</b> — {days_left} day{'s' if days_left != 1 else ''} remaining"
            else:
                status = "🆓 <b>FREE TIER</b> — Upgrade for unlimited power"

            text = (
                f"<b>{p['icon']} ZENITH AI TERMINAL</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{status}\n"
                f"<b>Persona:</b> {p['name']}\n"
                f"<b>Queries Today:</b> {usage['queries']}/{'60' if is_pro else '5'}\n"
            )
            await query.edit_message_text(
                text, reply_markup=get_ai_dashboard(is_pro, persona, usage), parse_mode="HTML",
            )

        elif query.data == "ai_status":
            days = await SubscriptionRepo.get_days_left(user_id)
            if is_pro:
                text = (
                    f"💎 <b>PRO SUBSCRIPTION</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"<b>Status:</b> ✅ Active\n"
                    f"<b>Remaining:</b> {days} day{'s' if days != 1 else ''}\n\n"
                    f"<b>Pro Benefits:</b>\n"
                    f"• 60 queries/hour (12× Free)\n"
                    f"• 4096 token responses (4× Free)\n"
                    f"• 6 AI Personas\n"
                    f"• Deep Research Mode\n"
                    f"• Code Generator\n"
                    f"• Image Prompt Crafter\n"
                    f"• Chat Memory (10 messages)\n"
                    f"• Unlimited Summarization"
                )
            else:
                text = (
                    f"🆓 <b>FREE TIER</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"<b>Limits:</b>\n"
                    f"• 5 queries/hour\n"
                    f"• 1024 token responses\n"
                    f"• Default persona only\n"
                    f"• 1 summary/day\n\n"
                    f"<b>Unlock everything:</b>\n"
                    f"<code>/activate [YOUR_KEY]</code>"
                )
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_usage":
            usage = await UsageRepo.get_today_usage(user_id)
            q_limit = 60 if is_pro else 5
            s_limit = "∞" if is_pro else "1"
            text = (
                f"📊 <b>TODAY'S USAGE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Queries:</b> {usage['queries']}/{q_limit}\n"
                f"<b>Summaries:</b> {usage['summarizes']}/{s_limit}\n"
                f"<b>Active Persona:</b> {usage['persona'].capitalize()}\n\n"
                f"<i>Usage resets daily at midnight UTC.</i>"
            )
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_personas":
            if not is_pro:
                text = (
                    "🔒 <b>Pro Feature: AI Personas</b>\n\n"
                    "Switch between specialized AI personalities:\n"
                    "💻 <b>Coder</b> — Production-grade code\n"
                    "✍️ <b>Writer</b> — Creative content\n"
                    "📊 <b>Analyst</b> — Strategic analysis\n"
                    "🎓 <b>Tutor</b> — Patient teaching\n"
                    "⚔️ <b>Debate</b> — Devil's advocate\n"
                    "🔥 <b>Roast</b> — Comedy roasts\n\n"
                    "<code>/activate [YOUR_KEY]</code>"
                )
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                current = await UsageRepo.get_persona(user_id)
                await query.edit_message_text(
                    "🎭 <b>SELECT PERSONA</b>\n\n<i>Choose your AI personality:</i>",
                    reply_markup=get_persona_keyboard(current),
                    parse_mode="HTML",
                )

        elif query.data.startswith("ai_persona_"):
            persona_key = query.data.replace("ai_persona_", "")
            if persona_key in PERSONAS:
                await UsageRepo.set_persona(user_id, persona_key)
                p = PERSONAS[persona_key]
                await query.edit_message_text(
                    f"✅ <b>Persona Switched</b>\n\n"
                    f"{p['icon']} Now talking to <b>{p['name']}</b>",
                    reply_markup=get_back_button(), parse_mode="HTML",
                )

        elif query.data == "ai_history":
            if not is_pro:
                text = (
                    "🔒 <b>Pro Feature: Chat Memory</b>\n\n"
                    "Zenith remembers your last 10 messages for contextual follow-ups.\n\n"
                    "<code>/activate [YOUR_KEY]</code>"
                )
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                history = await ConversationRepo.get_history(user_id, limit=10)
                if not history:
                    text = "💬 <b>Chat Memory</b>\n\nNo history yet. Start chatting with /zenith!"
                else:
                    lines = ["<b>💬 CHAT MEMORY</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
                    for msg in history[-6:]:
                        role_icon = "👤" if msg.role == "user" else "🤖"
                        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                        lines.append(f"{role_icon} <i>{html.escape(preview)}</i>")
                    count = await ConversationRepo.count_messages(user_id)
                    lines.append(f"\n<i>{count} messages stored</i>")
                    text = "\n".join(lines)
                await query.edit_message_text(text, reply_markup=get_history_keyboard(), parse_mode="HTML")

        elif query.data == "ai_clear_history":
            deleted = await ConversationRepo.clear_history(user_id)
            await query.edit_message_text(
                f"🗑️ <b>History Cleared</b>\n\n{deleted} messages removed.",
                reply_markup=get_back_button(), parse_mode="HTML",
            )

        elif query.data in ("ai_research_help", "ai_summarize_help", "ai_code_help", "ai_imagine_help"):
            help_texts = {
                "ai_research_help": (
                    "🔬 <b>Deep Research</b>\n\n"
                    "Multi-source research with news and web analysis.\n\n"
                    "<b>Usage:</b> <code>/research [TOPIC]</code>\n"
                    f"{'✅ <i>Available with your Pro subscription.</i>' if is_pro else '🔒 <i>Pro Required</i>'}"
                ),
                "ai_summarize_help": (
                    "📝 <b>Text Summarizer</b>\n\n"
                    "Condense long texts into key takeaways.\n\n"
                    "<b>Usage:</b> <code>/summarize [TEXT]</code>\n"
                    "<i>Or reply to any message with /summarize</i>\n\n"
                    f"<b>Limit:</b> {'Unlimited' if is_pro else '1/day (500 words max)'}"
                ),
                "ai_code_help": (
                    "💻 <b>Code Generator</b>\n\n"
                    "Production-ready code from natural language.\n\n"
                    "<b>Usage:</b> <code>/code [DESCRIPTION]</code>\n"
                    f"{'✅ <i>Available with your Pro subscription.</i>' if is_pro else '🔒 <i>Pro Required</i>'}"
                ),
                "ai_imagine_help": (
                    "🎨 <b>Image Prompt Crafter</b>\n\n"
                    "Optimized prompts for Midjourney, DALL-E, Stable Diffusion.\n\n"
                    "<b>Usage:</b> <code>/imagine [DESCRIPTION]</code>\n"
                    f"{'✅ <i>Available with your Pro subscription.</i>' if is_pro else '🔒 <i>Pro Required</i>'}"
                ),
            }
            await query.edit_message_text(
                help_texts[query.data], reply_markup=get_back_button(), parse_mode="HTML",
            )

    except Exception as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Dashboard callback error: {e}")


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        return
    results = [InlineQueryResultArticle(
        id="zenith_search", title=f"🔍 Ask Zenith: {query}",
        input_message_content=InputTextMessageContent(f"/zenith {query}"),
        description="Tap here to trigger high-speed AI research.",
    )]
    await update.inline_query.answer(results, cache_time=5, is_personal=True)


async def start_service():
    global bot_app, worker_tasks
    if not AI_BOT_TOKEN:
        logger.warning("⚠️ AI_BOT_TOKEN missing! AI Service disabled.")
        return

    await init_ai_db()

    bot_app = ApplicationBuilder().token(AI_BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("help", cmd_help))
    bot_app.add_handler(CommandHandler("zenith", cmd_zenith))
    bot_app.add_handler(CommandHandler("persona", cmd_persona))
    bot_app.add_handler(CommandHandler("research", cmd_research))
    bot_app.add_handler(CommandHandler("summarize", cmd_summarize))
    bot_app.add_handler(CommandHandler("code", cmd_code))
    bot_app.add_handler(CommandHandler("history", cmd_history))
    bot_app.add_handler(CommandHandler("imagine", cmd_imagine))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))
    bot_app.add_handler(InlineQueryHandler(inline_query))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            await bot_app.bot.set_webhook(
                url=f"{webhook_base}/webhook/ai/{WEBHOOK_SECRET}",
                secret_token=WEBHOOK_SECRET,
                allowed_updates=Update.ALL_TYPES,
            )
            logger.info("✅ AI Bot Online & Webhook Registered.")
        except Exception as e:
            logger.error(f"❌ AI Bot Webhook Failed: {e}")

    worker_tasks = [asyncio.create_task(ai_worker()) for _ in range(5)]
    logger.info("👷 AI Worker Pool: Online (5 workers)")


async def stop_service():
    for task in worker_tasks:
        task.cancel()

    while not task_queue.empty():
        try:
            _, context, placeholder_msg, *_ = task_queue.get_nowait()
            await context.bot.edit_message_text(
                chat_id=placeholder_msg.chat_id,
                message_id=placeholder_msg.message_id,
                text="🔄 <b>System Update:</b> Zenith is restarting. Please try again in a moment.",
                parse_mode="HTML",
            )
            task_queue.task_done()
        except Exception as e:
            logger.warning(f"Error in worker: {e}")

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_ai_engine()
    await close_http_client()


@router.post("/webhook/ai/{secret}")
async def ai_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)

    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"AI Webhook Malformed Payload Dropped: {e}")
        return Response(status_code=200)