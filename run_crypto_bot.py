import asyncio
from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.ui import get_main_dashboard, get_welcome_msg
from zenith_crypto_bot.repository import SubscriptionRepo, init_crypto_db

logger = setup_logger("SVC_WHALE")
router = APIRouter()
bot_app = None

# --- 🚀 PROPER ASYNC START HANDLER ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Safely handles the /start command."""
    first_name = update.effective_user.first_name
    await update.message.reply_text(
        get_welcome_msg(first_name), 
        reply_markup=get_main_dashboard(), 
        parse_mode="HTML"
    )

# --- 👻 GHOST ADMIN PROTOCOL ---
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return # Silent rejection
    
    if not context.args:
        return await update.message.reply_text("Admin Format: `/keygen [DAYS]`", parse_mode="Markdown")
        
    try:
        days = int(context.args[0])
        new_key = await SubscriptionRepo.generate_key(days)
        await update.message.reply_text(f"🔑 <b>PRO KEY GENERATED:</b>\n<code>{new_key}</code>", parse_mode="HTML")
    except ValueError: 
        pass

# --- 💳 ACTIVATION HANDLER ---
async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Format: `/activate [YOUR_KEY]`", parse_mode="Markdown")
        
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    
    await update.message.reply_text(msg, parse_mode="HTML")

# --- 📡 BUTTON HANDLERS ---
async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    
    if query.data == "ui_pro_info":
        status = f"✅ <b>Pro Active:</b> {days_left} days left." if days_left > 0 else "❌ <b>Pro Inactive.</b>"
        # 🚀 SRE FIX: Edit the message instead of sending a new one for cleaner UI
        await query.edit_message_text(f"{status}\n\nTo upgrade, purchase a key and type:\n<code>/activate YOUR_KEY</code>", parse_mode="HTML")

    elif query.data == "ui_whale_radar":
        msg = "🎯 <b>Pro Radar Online:</b> Scanning for $1M+ moves..." if days_left > 0 else "⏳ <b>Free Radar Online:</b> Monitoring smaller moves ($50k+)..."
        await query.edit_message_text(msg, parse_mode="HTML")

# --- 🚀 LIFECYCLE ---
async def start_service():
    global bot_app
    if not CRYPTO_BOT_TOKEN: 
        logger.warning("⚠️ CRYPTO_BOT_TOKEN missing!")
        return
    
    await init_crypto_db()
    bot_app = ApplicationBuilder().token(CRYPTO_BOT_TOKEN).build()
    
    # Register handlers properly
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    await bot_app.initialize()
    await bot_app.start()

    # Webhook Registration
    webhook_base = (WEBHOOK_URL or "").strip().rstrip('/')
    if webhook_base and not webhook_base.startswith("http"): webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            webhook_path = f"{webhook_base}/webhook/crypto/{WEBHOOK_SECRET}"
            await bot_app.bot.set_webhook(url=webhook_path, secret_token=WEBHOOK_SECRET, allowed_updates=Update.ALL_TYPES)
            logger.info(f"✅ Zenith Whale Online: /webhook/crypto/...")
        except Exception as e:
            logger.error(f"❌ Crypto Bot Webhook Failed: {e}")

async def stop_service():
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

@router.post("/webhook/crypto/{secret}")
async def crypto_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not bot_app: return Response(status_code=503)
    
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Crypto Webhook Error: {e}")
        return Response(status_code=500)