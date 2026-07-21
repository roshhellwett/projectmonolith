import asyncio
import contextlib
import re

from fastapi import APIRouter, Request, Response
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

from core.config import ADMIN_USER_ID, AI_BOT_TOKEN, WEBHOOK_SECRET
from core.database import dispose_engine, init_db
from core.error_handler import handle_bot_error
from core.gateway import attach_gateway, get_update_id_dedup_cache, setup_bot_webhook, validate_webhook_auth
from core.logger import setup_logger
from core.permissions import resolve_tier
from zenith_ai_bot.llm_engine import process_ai_query
from zenith_ai_bot.pro_handlers import cmd_code, cmd_history, cmd_imagine, cmd_persona, cmd_research, cmd_summarize
from zenith_ai_bot.prompts import PERSONAS
from zenith_ai_bot.repository import ConversationRepo, UsageRepo
from zenith_ai_bot.search import close_http_client
from zenith_ai_bot.ui import (
    get_activate_help,
    get_ai_dashboard,
    get_ai_key_deleted_msg,
    get_ai_key_set_success_msg,
    get_ai_key_status_msg,
    get_back_button,
    get_confirm_clear_history,
    get_confirm_clear_history_msg,
    get_feature_help_msg,
    get_help_msg,
    get_history_cleared_msg,
    get_history_empty_msg,
    get_history_keyboard,
    get_history_list_msg,
    get_history_locked_msg,
    get_no_key_msg,
    get_persona_switched_msg,
    get_personas_locked_msg,
    get_personas_select_msg,
    get_queue_full_msg,
    get_status_msg,
    get_usage_card,
    get_welcome_msg,
    get_worker_error_msg,
    get_zenith_no_query_msg,
)
from zenith_ai_bot.utils import check_ai_rate_limit, sanitize_telegram_html
from zenith_crypto_bot.ai_engine import validate_groq_key
from zenith_crypto_bot.repository import SubscriptionRepo

logger = setup_logger("SVC_AI")
router = APIRouter()

bot_app = None
task_queue = asyncio.Queue(maxsize=100)
worker_tasks = []


async def ai_worker():
    while True:
        task_item = None
        try:
            task_item = await task_queue.get()
            update, context, placeholder_msg, text, history_text, is_pro, persona, history = task_item
            try:
                user_id = update.effective_user.id
                api_key = await SubscriptionRepo.get_groq_key(user_id)
                if not api_key:
                    with contextlib.suppress(Exception):
                        await context.bot.edit_message_text(
                            chat_id=placeholder_msg.chat_id,
                            message_id=placeholder_msg.message_id,
                            text=get_no_key_msg(),
                            parse_mode="HTML",
                        )
                    task_queue.task_done()
                    continue

                max_tokens = 4096 if is_pro else 1024
                selected_model = await UsageRepo.get_selected_model(user_id)
                ai_response = await process_ai_query(
                    text,
                    history_text,
                    persona=persona,
                    max_tokens=max_tokens,
                    history=history,
                    api_key=api_key,
                    preferred_model=selected_model,
                )
                clean_html = sanitize_telegram_html(ai_response)

                if len(clean_html) > 4000:
                    clean_html = clean_html[:4000] + "\n\n[Truncated due to Telegram limits]"

                if is_pro:
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
    is_pro = await SubscriptionRepo.is_pro(user_id)
    usage = await UsageRepo.get_today_usage(user_id)
    persona = usage.get("persona", "default")
    days_left = await SubscriptionRepo.get_days_left(user_id)

    api_key = await SubscriptionRepo.get_groq_key(user_id)
    if not api_key:
        text = (
            "<b>Zenith AI Terminal</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Welcome! To use AI features, you need to connect your Groq API key.\n\n"
            "1. Go to <b>console.groq.com</b> \u2192 API Keys\n"
            "2. Create a free key\n"
            "3. Send it right here:\n"
            "<code>/setkey gsk_your_api_key</code>\n\n"
            "Once connected, use /zenith to ask anything or click around the dashboard!"
        )
    else:
        text = get_welcome_msg(is_pro, days_left, usage, persona)

    selected_model = usage.get("selected_model", "llama-3.3-70b-versatile")
    await update.message.reply_text(
        text, reply_markup=get_ai_dashboard(is_pro, persona, usage, selected_model), parse_mode="HTML"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tier = await resolve_tier(user_id)

    text = get_help_msg(is_pro=tier.is_pro)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    if not tier.is_pro:
        buttons.append([InlineKeyboardButton("Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")])
    buttons.append([InlineKeyboardButton("Back", callback_data="ai_main_menu")])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cmd_zenith(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
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
        return await msg.reply_text(get_zenith_no_query_msg())
    if not text and history_text:
        text = f"Please analyze this: {history_text}"
        history_text = None

    persona = await UsageRepo.get_persona(user_id) if is_pro else "default"
    conversation_history = await ConversationRepo.get_history(user_id, limit=10) if is_pro else None

    p = PERSONAS.get(persona, PERSONAS["default"])
    try:
        placeholder = await msg.reply_text(f"{p['icon']} Thinking...", parse_mode="HTML")
        task_queue.put_nowait((update, context, placeholder, text, history_text, is_pro, persona, conversation_history))
        await UsageRepo.increment_queries(user_id)
    except asyncio.QueueFull:
        await msg.reply_text(get_queue_full_msg())


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        user_id = update.effective_user.id
        is_pro = await SubscriptionRepo.is_pro(user_id)
        if is_pro:
            return await update.message.reply_text(
                "💎 <b>Active Pro Membership</b>\n\nYou already have an active Pro membership! No activation needed right now.",
                parse_mode="HTML",
            )
        return await update.message.reply_text(get_activate_help(), parse_mode="HTML")
    key = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_setkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: <code>/setkey gsk_your_groq_api_key</code>", parse_mode="HTML")
    api_key = context.args[0].strip()
    placeholder = await update.message.reply_text("Verifying API key...", parse_mode="HTML")
    valid, msg = await validate_groq_key(api_key)
    if not valid:
        return await placeholder.edit_text(
            f"<b>Invalid Key</b>\n\n{msg}\n\nGet a free key at console.groq.com", parse_mode="HTML"
        )
    await SubscriptionRepo.set_groq_key(update.effective_user.id, api_key)
    text, kb = get_ai_key_set_success_msg()
    await placeholder.edit_text(text, reply_markup=kb, parse_mode="HTML")


async def cmd_mykey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    key = await SubscriptionRepo.get_groq_key(user_id)
    text, kb = get_ai_key_status_msg(key is not None)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def cmd_delkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await SubscriptionRepo.delete_groq_key(update.effective_user.id)
    text, kb = get_ai_key_deleted_msg()
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()
    user_id = query.from_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    try:
        if query.data == "ai_main_menu":
            usage = await UsageRepo.get_today_usage(user_id)
            persona = usage.get("persona", "default")
            selected_model = usage.get("selected_model", "llama-3.3-70b-versatile")
            days_left = await SubscriptionRepo.get_days_left(user_id)
            text = get_welcome_msg(is_pro, days_left, usage, persona)
            await query.edit_message_text(
                text, reply_markup=get_ai_dashboard(is_pro, persona, usage, selected_model), parse_mode="HTML"
            )

        elif query.data == "ai_status":
            days = await SubscriptionRepo.get_days_left(user_id)
            text = get_status_msg(is_pro, days)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_usage":
            usage = await UsageRepo.get_today_usage(user_id)
            text = get_usage_card(usage, is_pro)
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_show_key_setup":
            has_key = await SubscriptionRepo.get_groq_key(user_id)
            text, kb = get_ai_key_status_msg(has_key is not None)
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

        elif query.data == "ai_personas":
            if not is_pro:
                text = get_personas_locked_msg()
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                current = await UsageRepo.get_persona(user_id)
                from zenith_ai_bot.ui import get_persona_keyboard

                await query.edit_message_text(
                    get_personas_select_msg(),
                    reply_markup=get_persona_keyboard(current, is_pro=True),
                    parse_mode="HTML",
                )

        elif query.data.startswith("ai_persona_") or query.data.startswith("ai_switch_persona_"):
            persona_key = query.data.replace("ai_persona_", "").replace("ai_switch_persona_", "")
            if not is_pro:
                text = get_personas_locked_msg()
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")
            elif persona_key in PERSONAS:
                await UsageRepo.set_persona(user_id, persona_key)
                text = get_persona_switched_msg(persona_key)
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ai_history":
            if not is_pro:
                text = get_history_locked_msg()
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
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

        elif query.data == "ai_activate_help":
            if is_pro:
                text = "💎 <b>Active Pro Membership</b>\n\nYou already have an active Pro membership! No activation needed right now."
                await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                from zenith_ai_bot.ui import get_activate_help_keyboard

                text = get_activate_help()
                await query.edit_message_text(text, reply_markup=get_activate_help_keyboard(), parse_mode="HTML")

        elif query.data in ("ai_research_help", "ai_summarize_help", "ai_code_help", "ai_imagine_help"):
            feature_map = {
                "ai_research_help": "research",
                "ai_summarize_help": "summarize",
                "ai_code_help": "code",
                "ai_imagine_help": "imagine",
            }
            feature = feature_map[query.data]
            msg_text, kb = get_feature_help_msg(feature, is_pro)
            await query.edit_message_text(msg_text, reply_markup=kb, parse_mode="HTML")

        elif query.data == "ai_models":
            current_model = await UsageRepo.get_selected_model(user_id)
            from zenith_ai_bot.ui import get_model_selector_keyboard, get_model_selector_msg

            await query.edit_message_text(
                get_model_selector_msg(current_model),
                reply_markup=get_model_selector_keyboard(current_model, is_pro=is_pro),
                parse_mode="HTML",
            )

        elif query.data.startswith("ai_set_model_"):
            model_id = query.data.replace("ai_set_model_", "")
            from core.llm_fallback import AVAILABLE_MODELS
            from zenith_ai_bot.ui import get_model_selector_keyboard, get_model_selector_msg, get_pro_feature_msg

            if model_id in AVAILABLE_MODELS:
                if AVAILABLE_MODELS[model_id]["tier"] == "pro" and not is_pro:
                    msg, kb = get_pro_feature_msg(f"Model: {AVAILABLE_MODELS[model_id]['name']}")
                    await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")
                else:
                    await UsageRepo.set_selected_model(user_id, model_id)
                    text = (
                        f"✅ <b>Active Engine Switched!</b>\nNow using: <b>{AVAILABLE_MODELS[model_id]['icon']} {AVAILABLE_MODELS[model_id]['name']}</b>\n\n"
                        + get_model_selector_msg(model_id)
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_model_selector_keyboard(model_id, is_pro=is_pro), parse_mode="HTML"
                    )

        elif query.data.startswith("ai_quick_"):
            if (
                query.data.startswith("ai_quick_res_")
                or query.data.startswith("ai_quick_code_")
                or query.data.startswith("ai_quick_img_")
            ) and not is_pro:
                from zenith_ai_bot.ui import get_pro_feature_msg

                msg, kb = get_pro_feature_msg("Pro Interactive Quick-Action")
                await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")
            else:
                api_key = await SubscriptionRepo.get_groq_key(user_id)
                if not api_key:
                    await query.edit_message_text(get_no_key_msg(), parse_mode="HTML")
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
                        res = await process_research(topic, api_key=api_key, preferred_model=selected_model)
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
                        res = await process_summarize(sample, api_key=api_key, preferred_model=selected_model)
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
                        res = await process_code(prompt, api_key=api_key, preferred_model=selected_model)
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
                        res = await process_imagine(prompt, api_key=api_key, preferred_model=selected_model)
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
    bot_app.add_handler(CommandHandler("persona", cmd_persona))
    bot_app.add_handler(CommandHandler("research", cmd_research))
    bot_app.add_handler(CommandHandler("summarize", cmd_summarize))
    bot_app.add_handler(CommandHandler("code", cmd_code))
    bot_app.add_handler(CommandHandler("history", cmd_history))
    bot_app.add_handler(CommandHandler("imagine", cmd_imagine))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("setkey", cmd_setkey))
    bot_app.add_handler(CommandHandler("mykey", cmd_mykey))
    bot_app.add_handler(CommandHandler("delkey", cmd_delkey))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))
    bot_app.add_handler(InlineQueryHandler(inline_query))
    bot_app.add_error_handler(handle_bot_error)

    await init_db()
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
                    try:
                        await _context.bot.edit_message_text(
                            chat_id=placeholder_msg.chat_id,
                            message_id=placeholder_msg.message_id,
                            text="System Update: Zenith is restarting. Please try again in a moment.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
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


@router.post("/webhook/ai/{secret}")
async def ai_webhook(secret: str, request: Request):
    if not validate_webhook_auth(secret, request):
        logger.warning(f"❌ [AI] Webhook auth failed! Expected len={len(WEBHOOK_SECRET)}, got len={len(secret)}")
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)

    try:
        data = await request.json()
        dedup = get_update_id_dedup_cache()
        update_id = data.get("update_id", 0)
        if update_id and update_id in dedup:
            return Response(status_code=200)
        if update_id:
            dedup[update_id] = True
        logger.info(
            f"📥 [AI] Enqueuing update {update_id} into update_queue (qsize before={bot_app.update_queue.qsize()})"
        )
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"AI Webhook Malformed Payload Dropped: {e}", exc_info=True)
        return Response(status_code=200)
