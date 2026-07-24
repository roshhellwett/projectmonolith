import asyncio
import contextlib
import re
import html

from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from core.config import ADMIN_USER_ID, AI_BOT_TOKEN
from core.animation import continuous_typing_action
from core.database import dispose_engine
from core.engagement_handlers import cmd_changelog, cmd_feedback, cmd_mystats, cmd_referral
from core.error_handler import handle_bot_error
from core.gateway import attach_gateway, setup_bot_webhook
from core.logger import setup_logger
from core.permissions import resolve_tier
from core.webhook_router import register_bot_webhook
from zenith_ai_bot.llm_engine import process_ai_query
from zenith_ai_bot.pro_handlers import cmd_code, cmd_history, cmd_imagine, cmd_persona, cmd_research, cmd_summarize, cmd_audit, cmd_sentiment
from zenith_ai_bot.prompts import PERSONAS
from zenith_ai_bot.repository import ConversationRepo, UsageRepo, SettingsRepo
from zenith_ai_bot.search import close_http_client
from zenith_ai_bot.ui import (
    get_ai_dashboard,
    get_back_button,
    get_confirm_clear_history,
    get_confirm_clear_history_msg,
    get_help_msg,
    get_history_cleared_msg,
    get_history_empty_msg,
    get_history_keyboard,
    get_history_list_msg,
    get_persona_switched_msg,
    get_personas_select_msg,
    get_queue_full_msg,
    get_usage_card,
    get_welcome_msg,
    get_worker_error_msg,
    get_zenith_no_query_msg,
)
from zenith_ai_bot.utils import sanitize_telegram_html

logger = setup_logger("SVC_AI")

bot_app = None
task_queue = asyncio.Queue(maxsize=100)
worker_tasks = []


async def ai_worker():
    while True:
        task_item = None
        try:
            task_item = await task_queue.get()
            update, context, placeholder_msg, text, history_text, persona, history = task_item
            try:
                user_id = update.effective_user.id
                quota_allowed, quota_msg = await UsageRepo.check_quota(user_id)
                if not quota_allowed:
                    with contextlib.suppress(Exception):
                        await context.bot.edit_message_text(
                            chat_id=placeholder_msg.chat_id,
                            message_id=placeholder_msg.message_id,
                            text=quota_msg,
                            parse_mode="HTML",
                        )
                    task_queue.task_done()
                    continue

                selected_model = await UsageRepo.get_selected_model(user_id)
                api_key = await SettingsRepo.get_api_key(user_id)
                if not api_key:
                    with contextlib.suppress(Exception):
                        await context.bot.edit_message_text(
                            chat_id=placeholder_msg.chat_id,
                            message_id=placeholder_msg.message_id,
                            text="⚠️ <b>API Key Required</b>\n\nPlease set your personal Groq API key using <code>/setkey [your_key]</code>.",
                            parse_mode="HTML",
                        )
                    task_queue.task_done()
                    continue

                msg = update.message
                image_base64 = None
                
                if msg.voice:
                    import tempfile, os
                    from core.llm_fallback import AIExecutionEngine
                    try:
                        voice_file = await msg.voice.get_file()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
                            temp_audio_path = temp_audio.name
                        await voice_file.download_to_drive(temp_audio_path)
                        transcript = await AIExecutionEngine.transcribe_audio(api_key, temp_audio_path)
                        text = (f"[Voice Note Transcription]: {transcript}\n\n" + text).strip()
                        os.remove(temp_audio_path)
                    except Exception as e:
                        logger.error(f"Voice error: {e}")
                
                if msg.photo:
                    import tempfile, os, base64
                    try:
                        photo_file = await msg.photo[-1].get_file()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_photo:
                            temp_photo_path = temp_photo.name
                        await photo_file.download_to_drive(temp_photo_path)
                        with open(temp_photo_path, "rb") as f:
                            image_base64 = base64.b64encode(f.read()).decode("utf-8")
                        os.remove(temp_photo_path)
                    except Exception as e:
                        logger.error(f"Photo error: {e}")

                async with continuous_typing_action(update, context):
                    ai_response = await process_ai_query(
                        user_id,
                        text,
                        history_text,
                        persona=persona,
                        max_tokens=4096,
                        history=history,
                        preferred_model=selected_model,
                        api_key=api_key,
                        image_base64=image_base64,
                    )
                clean_html = sanitize_telegram_html(ai_response)

                if len(clean_html) > 4000:
                    clean_html = clean_html[:4000] + "\n\n[Truncated due to Telegram limits]"

                await ConversationRepo.add_message(update.effective_user.id, "user", text)
                await ConversationRepo.add_message(update.effective_user.id, "assistant", ai_response[:2000])

                try:
                    await context.bot.edit_message_text(
                        chat_id=placeholder_msg.chat_id,
                        message_id=placeholder_msg.message_id,
                        text=clean_html,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception as inner_e:
                    if "not modified" not in str(inner_e).lower():
                        plain_text = re.sub(r"<[^>]+>", "", clean_html)[:4000]
                        try:
                            await context.bot.edit_message_text(
                                chat_id=placeholder_msg.chat_id,
                                message_id=placeholder_msg.message_id,
                                text=plain_text,
                                disable_web_page_preview=True,
                            )
                        except Exception as fallback_e:
                            if "not modified" not in str(fallback_e).lower():
                                raise fallback_e
            except Exception as e:
                if "not modified" not in str(e).lower():
                    logger.error(f"Worker Error: {e}")
                    with contextlib.suppress(Exception):
                        await context.bot.edit_message_text(
                            chat_id=placeholder_msg.chat_id,
                            message_id=placeholder_msg.message_id,
                            text=get_worker_error_msg(),
                        )
            finally:
                if task_item is not None:
                    task_queue.task_done()
        except asyncio.CancelledError:
            break


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    api_key = await SettingsRepo.get_api_key(user_id)
    if not api_key:
        from zenith_ai_bot.ui import get_key_required_msg
        return await update.message.reply_text(get_key_required_msg(), parse_mode="HTML")
        
    first_name = html.escape(update.effective_user.first_name or "User")
    usage = await UsageRepo.get_today_usage(user_id)
    persona = usage.get("persona", "default")
    text = get_welcome_msg(usage, persona)
    selected_model = usage.get("selected_model", "llama-3.3-70b-versatile")
    await update.message.reply_text(
        text, reply_markup=get_ai_dashboard(persona, usage, selected_model), parse_mode="HTML"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tier = await resolve_tier(user_id)

    text = get_help_msg()

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = [[InlineKeyboardButton("Back", callback_data="ai_main_menu")]]

    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cmd_zenith(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id = update.effective_user.id

    quota_allowed, quota_msg = await UsageRepo.check_quota(user_id)
    if not quota_allowed:
        return await msg.reply_text(quota_msg, parse_mode="HTML")

    text = ""
    if context.args:
        text = " ".join(context.args)
    elif msg.text and not msg.text.startswith('/'):
        text = msg.text

    if not text and msg.caption:
        text = msg.caption.replace("/zenith", "").strip()

    history_text = (msg.reply_to_message.text or msg.reply_to_message.caption) if msg.reply_to_message else None

    if not text and not history_text and not msg.photo and not msg.voice:
        return await msg.reply_text(get_zenith_no_query_msg())
    if not text and history_text:
        text = f"Please analyze this: {history_text}"
        history_text = None

    persona = await UsageRepo.get_persona(user_id)
    conversation_history = await ConversationRepo.get_history(user_id, limit=10)

    p = PERSONAS.get(persona, PERSONAS["default"])
    try:
        placeholder = await msg.reply_text(f"{p['icon']} Thinking...", parse_mode="HTML")
        task_queue.put_nowait((update, context, placeholder, text, history_text, persona, conversation_history))
        await UsageRepo.increment_queries(user_id)
    except asyncio.QueueFull:
        await msg.reply_text(get_queue_full_msg())


async def cmd_setkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n<code>/setkey [your_groq_api_key]</code>\n\nGet your free key at <a href='https://console.groq.com'>console.groq.com</a>",
            parse_mode="HTML"
        )
    key = context.args[0].strip()
    
    from core.llm_fallback import AIExecutionEngine
    msg = await update.message.reply_text("🔄 Verifying API key...", parse_mode="HTML")
    resp = await AIExecutionEngine.execute([{"role": "user", "content": "ping"}], api_key=key, max_tokens=10)
    is_valid = not resp.is_error
    
    if not is_valid:
        return await msg.edit_text("❌ <b>Invalid API Key</b>\n\nThe key you provided was rejected by Groq.", parse_mode="HTML")
        
    await SettingsRepo.set_api_key(update.effective_user.id, key)
    await msg.edit_text("✅ <b>API Key Connected</b>\n\nYour personal Groq API key has been securely saved. You can now use <code>/zenith</code>!", parse_mode="HTML")


async def cmd_mykey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quota = await UsageRepo.get_token_quota(update.effective_user.id)
    await update.message.reply_text(
        f"⚡ <b>AI Token Usage</b>\n\n"
        f"Today's usage: <b>{quota['tokens_used']:,}</b> / <b>{quota['daily_limit']:,}</b> tokens\n"
        f"Remaining: <b>{quota['remaining']:,}</b> tokens\n\n"
        f"Your quota resets at midnight UTC.",
        parse_mode="HTML",
    )


async def cmd_delkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await SettingsRepo.set_api_key(update.effective_user.id, None)
    await update.message.reply_text(
        "🗑️ <b>API Key Removed</b>\n\nYour personal Groq API key has been securely deleted from our database.",
        parse_mode="HTML",
    )


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()
    user_id = query.from_user.id

    try:
        if query.data == "ai_main_menu":
            usage = await UsageRepo.get_today_usage(user_id)
            persona = usage.get("persona", "default")
            selected_model = usage.get("selected_model", "llama-3.3-70b-versatile")
            text = get_welcome_msg(usage, persona)
            await query.edit_message_text(
                text, reply_markup=get_ai_dashboard(persona, usage, selected_model), parse_mode="HTML"
            )

        elif query.data == "ai_usage":
            usage = await UsageRepo.get_today_usage(user_id)
            text = get_usage_card(usage)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_show_key_setup":
            from zenith_ai_bot.repository import SettingsRepo
            from zenith_ai_bot.ui import get_api_key_status_msg
            
            api_key, tokens_used = await SettingsRepo.get_key_and_tokens(user_id)
            await query.edit_message_text(
                get_api_key_status_msg(api_key, tokens_used),
                reply_markup=get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "ai_features_menu":
            from zenith_ai_bot.ui import get_ai_features_msg, get_ai_features_keyboard
            await query.edit_message_text(
                get_ai_features_msg(), reply_markup=get_ai_features_keyboard(), parse_mode="HTML"
            )

        elif query.data == "ai_help_menu":
            from zenith_ai_bot.ui import get_help_msg, get_ai_help_keyboard
            await query.edit_message_text(
                get_help_msg(), reply_markup=get_ai_help_keyboard(), parse_mode="HTML"
            )

        elif query.data == "ai_research_help":
            await query.answer("Use /research [topic] to run a multi-pass deep research.", show_alert=True)
        elif query.data == "ai_summarize_help":
            await query.answer("Use /summarize [text/url] to summarize content.", show_alert=True)
        elif query.data == "ai_code_help":
            await query.answer("Use /code [desc] to generate software architecture.", show_alert=True)
        elif query.data == "ai_imagine_help":
            await query.answer("Use /imagine [desc] to craft image prompts.", show_alert=True)

        elif query.data == "ai_personas":
            current = await UsageRepo.get_persona(user_id)
            from zenith_ai_bot.ui import get_persona_keyboard

            await query.edit_message_text(
                get_personas_select_msg(),
                reply_markup=get_persona_keyboard(current),
                parse_mode="HTML",
            )

        elif query.data.startswith("ai_persona_") or query.data.startswith("ai_switch_persona_"):
            persona_key = query.data.replace("ai_persona_", "").replace("ai_switch_persona_", "")
            if persona_key in PERSONAS:
                await UsageRepo.set_persona(user_id, persona_key)
                text = get_persona_switched_msg(persona_key)
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_history":
            history = await ConversationRepo.get_history(user_id, limit=10)
            text = get_history_empty_msg() if not history else get_history_list_msg(history)
            await query.edit_message_text(text, reply_markup=get_history_keyboard(), parse_mode="HTML")

        elif query.data == "ai_clear_history_confirm":
            text = get_confirm_clear_history_msg()
            await query.edit_message_text(text, reply_markup=get_confirm_clear_history(), parse_mode="HTML")

        elif query.data == "ai_clear_history":
            deleted = await ConversationRepo.clear_history(user_id)
            text = get_history_cleared_msg(deleted)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_models":
            current_model = await UsageRepo.get_selected_model(user_id)
            from zenith_ai_bot.ui import get_model_selector_keyboard, get_model_selector_msg

            await query.edit_message_text(
                get_model_selector_msg(current_model),
                reply_markup=get_model_selector_keyboard(current_model),
                parse_mode="HTML",
            )

        elif query.data.startswith("ai_set_model_"):
            model_id = query.data.replace("ai_set_model_", "")
            from core.llm_fallback import AVAILABLE_MODELS
            from zenith_ai_bot.ui import get_model_selector_keyboard, get_model_selector_msg

            if model_id in AVAILABLE_MODELS:
                await UsageRepo.set_selected_model(user_id, model_id)
                text = (
                    f"✅ <b>Active Engine Switched!</b>\nNow using: <b>{AVAILABLE_MODELS[model_id]['icon']} {AVAILABLE_MODELS[model_id]['name']}</b>\n\n"
                    + get_model_selector_msg(model_id)
                )
                await query.edit_message_text(
                    text, reply_markup=get_model_selector_keyboard(model_id), parse_mode="HTML"
                )

        elif query.data.startswith("ai_quick_"):
            quota_allowed, quota_msg = await UsageRepo.check_quota(user_id)
            if not quota_allowed:
                await query.edit_message_text(quota_msg, parse_mode="HTML")
            else:
                selected_model = await UsageRepo.get_selected_model(user_id)
                from zenith_ai_bot.llm_engine import (
                    process_code,
                    process_imagine,
                    process_research,
                    process_summarize,
                )
                from zenith_ai_bot.utils import sanitize_telegram_html

                if query.data.startswith("ai_quick_res_"):
                    topics = {
                        "ai_quick_res_aitrends": "Artificial Intelligence breakthroughs and agentic workflows 2026",
                        "ai_quick_res_quantum": "Quantum computing commercial progress and breakthroughs",
                        "ai_quick_res_defi": "DeFi security moats and smart contract vulnerability mitigation",
                    }
                    topic = topics.get(query.data, "Artificial Intelligence trends")
                    await query.edit_message_text(
                        f"🔬 <i>Executing deep research: {topic}...</i>", parse_mode="HTML"
                    )
                    res = await process_research(user_id, topic, preferred_model=selected_model)
                    clean = sanitize_telegram_html(res)[:4000]
                    await query.edit_message_text(
                        clean, reply_markup=get_back_button(), parse_mode="HTML", disable_web_page_preview=True
                    )

                elif query.data.startswith("ai_quick_sum_"):
                    samples = {
                        "ai_quick_sum_whitepaper": "Autonomous Agentic Systems Whitepaper Summary: Modern AI architectures rely on multi-tier fallback mechanisms, dynamic context pruning, and subagent orchestration. By integrating real-time web verification with specialized tool execution, next-generation LLM agents achieve near-zero hallucination rates in production engineering environments.",
                        "ai_quick_sum_earnings": "Quarterly Earnings High-Density Review: Tech sector revenues surged 24% year-over-year, driven primarily by enterprise adoption of autonomous developer tools and decentralized compute infrastructure. Operating margins expanded by 340 bps due to AI-driven efficiency workflows across customer support and core infrastructure.",
                    }
                    sample = samples.get(query.data, "Summary sample text.")
                    await query.edit_message_text("📝 <i>Summarizing sample document...</i>", parse_mode="HTML")
                    res = await process_summarize(user_id, sample, preferred_model=selected_model)
                    clean = sanitize_telegram_html(res)[:4000]
                    await query.edit_message_text(clean, reply_markup=get_back_button(), parse_mode="HTML")

                elif query.data.startswith("ai_quick_code_"):
                    prompts = {
                        "ai_quick_code_fastapi": "Create a Python FastAPI REST API endpoint with JWT authentication, dependency injection, and Pydantic schema validation for user registration.",
                        "ai_quick_code_react": "Write a clean React TypeScript component featuring a sortable, paginated data table with search filtering and modern styling.",
                        "ai_quick_code_tgbot": "Write a Python Telegram bot handler using python-telegram-bot v20+ with inline keyboard pagination and robust error handling.",
                    }
                    prompt = prompts.get(query.data, "Write a Python function.")
                    await query.edit_message_text(
                        "💻 <i>Generating production code architecture...</i>", parse_mode="HTML"
                    )
                    res = await process_code(user_id, prompt, preferred_model=selected_model)
                    clean = sanitize_telegram_html(res)[:4000]
                    await query.edit_message_text(clean, reply_markup=get_back_button(), parse_mode="HTML")

                elif query.data.startswith("ai_quick_img_"):
                    prompts = {
                        "ai_quick_img_cyberpunk": "A breathtaking cyberpunk Neo-Tokyo street at twilight with neon rain reflections and towering holographic advertisements.",
                        "ai_quick_img_nebula": "A vivid deep space colorful nebula horizon with a lone exploratory starship approaching a hyper-luminous pulsar.",
                        "ai_quick_img_watch": "A minimalist luxury mechanical wristwatch suspended in mid-air with dramatically lit gears and matte black titanium casing.",
                    }
                    prompt = prompts.get(query.data, "Visual prompt sample.")
                    await query.edit_message_text(
                        "🎨 <i>Crafting multi-platform visual prompts...</i>", parse_mode="HTML"
                    )
                    res = await process_imagine(user_id, prompt, preferred_model=selected_model)
                    clean = sanitize_telegram_html(res)[:4000]
                    await query.edit_message_text(clean, reply_markup=get_back_button(), parse_mode="HTML")

    except Exception as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Dashboard callback error: {e}")


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        return
    results = [
        InlineQueryResultArticle(
            id="zenith_search",
            title=f"Ask Zenith: {query}",
            input_message_content=InputTextMessageContent(f"/zenith {query}"),
            description="Tap here to trigger high-speed AI research.",
        )
    ]
    await update.inline_query.answer(results, cache_time=5, is_personal=True)


async def start_service():
    global bot_app, worker_tasks
    if not AI_BOT_TOKEN:
        logger.warning("AI_BOT_TOKEN missing! AI Service disabled.")
        return

    bot_app = ApplicationBuilder().token(AI_BOT_TOKEN).build()
    attach_gateway(bot_app, "AI")

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("help", cmd_help))
    bot_app.add_handler(CommandHandler("zenith", cmd_zenith))
    bot_app.add_handler(MessageHandler((filters.TEXT | filters.VOICE | filters.PHOTO) & ~filters.COMMAND, cmd_zenith))
    bot_app.add_handler(CommandHandler("persona", cmd_persona))
    bot_app.add_handler(CommandHandler("research", cmd_research))
    bot_app.add_handler(CommandHandler("summarize", cmd_summarize))
    bot_app.add_handler(CommandHandler("code", cmd_code))
    bot_app.add_handler(CommandHandler("history", cmd_history))
    bot_app.add_handler(CommandHandler("imagine", cmd_imagine))
    bot_app.add_handler(CommandHandler("audit", cmd_audit))
    bot_app.add_handler(CommandHandler("sentiment", cmd_sentiment))
    bot_app.add_handler(CommandHandler("setkey", cmd_setkey))
    bot_app.add_handler(CommandHandler("rotate", cmd_setkey))
    bot_app.add_handler(CommandHandler("mykey", cmd_mykey))
    bot_app.add_handler(CommandHandler("delkey", cmd_delkey))
    bot_app.add_handler(CommandHandler("referral", cmd_referral))
    bot_app.add_handler(CommandHandler("feedback", cmd_feedback))
    bot_app.add_handler(CommandHandler("changelog", cmd_changelog))
    bot_app.add_handler(CommandHandler("mystats", cmd_mystats))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))
    bot_app.add_handler(InlineQueryHandler(inline_query))
    bot_app.add_error_handler(handle_bot_error)

    register_bot_webhook("ai", bot_app)

    await bot_app.initialize()
    await bot_app.start()

    worker_tasks = [asyncio.create_task(ai_worker()) for _ in range(5)]
    logger.info("AI Worker Pool: Online (5 workers)")


async def register_webhook():
    if bot_app:
        await setup_bot_webhook(bot_app, "ai")


async def stop_service(dispose_db: bool = False):
    while not task_queue.empty():
        try:
            task_item = task_queue.get_nowait()
            if len(task_item) >= 3:
                _, _context, placeholder_msg = task_item[0], task_item[1], task_item[2]
                if _context and placeholder_msg:
                    with contextlib.suppress(Exception):
                        await _context.bot.edit_message_text(
                            chat_id=placeholder_msg.chat_id,
                            message_id=placeholder_msg.message_id,
                            text="System Update: Zenith is restarting. Please try again in a moment.",
                            parse_mode="HTML",
                        )
            task_queue.task_done()
        except asyncio.QueueEmpty:
            break
        except Exception as e:
            logger.warning(f"Error draining task queue: {e}")

    for task in worker_tasks:
        task.cancel()

    await asyncio.gather(*worker_tasks, return_exceptions=True)

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    if dispose_db:
        await dispose_engine()
    await close_http_client()
