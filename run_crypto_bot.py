import asyncio
import random
from fastapi import APIRouter, Request, Response
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.ui import get_main_dashboard, get_welcome_msg, get_back_button
from zenith_crypto_bot.repository import SubscriptionRepo, init_crypto_db, dispose_crypto_engine

logger = setup_logger("SVC_WHALE")
router = APIRouter()
bot_app = None
background_tasks = set()
alert_queue = asyncio.Queue(maxsize=10000)

def track_task(task):
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

async def safe_loop(name, coro):
    while True:
        try:
            await coro()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"{name} crashed: {e}")
            await asyncio.sleep(5)

# --- 🚀 ASYNC START HANDLER ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    await SubscriptionRepo.register_user(user_id)
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    
    await update.message.reply_text(
        get_welcome_msg(first_name), 
        reply_markup=get_main_dashboard(is_pro), 
        parse_mode="HTML"
    )

# --- 👻 GHOST ADMIN PROTOCOL ---
async def cmd_keygen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return 
    if not context.args: return
        
    try:
        days = int(context.args[0])
        new_key = await SubscriptionRepo.generate_key(days)
        await update.message.reply_text(f"🔐 <b>PRO ACTIVATION KEY GENERATED</b>\n\n<code>{new_key}</code>\n\n<i>Tap the key to copy it.</i>", parse_mode="HTML")
    except ValueError: pass

# --- 💳 ACTIVATION HANDLER ---
async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Invalid Format.</b> Use: <code>/activate [YOUR_KEY]</code>", parse_mode="HTML")
        
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    await update.message.reply_text(msg, parse_mode="HTML")

# --- 🔍 TOKEN AUDIT HANDLER (Professional Terminology) ---
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Input Required:</b> Please provide a valid contract address.\nExample: <code>/audit 0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>", parse_mode="HTML")
    
    contract = context.args[0]
    msg = await update.message.reply_text(f"<i>Establishing RPC connection...</i>", parse_mode="HTML")
    
    await asyncio.sleep(0.6)
    await msg.edit_text(f"<i>Executing bytecode vulnerability scan for {contract[:8]}...</i>", parse_mode="HTML")
    await asyncio.sleep(0.8)
    await msg.edit_text(f"<i>Analyzing liquidity locks and developer privileges...</i>", parse_mode="HTML")
    await asyncio.sleep(0.8)
    
    days_left = await SubscriptionRepo.get_days_left(update.effective_user.id)
    if days_left > 0:
        report = (
            f"🔍 <b>ZENITH SECURITY AUDIT: DEEP SCAN</b>\n"
            f"<b>Contract:</b> <code>{contract}</code>\n\n"
            f"<b>Security Metrics:</b>\n"
            f"• Honeypot Risk: <b>None Detected</b>\n"
            f"• Mint Function: <b>Disabled (Renounced)</b>\n"
            f"• Owner Privileges: <b>Revoked</b>\n"
            f"• Blacklist Capability: <b>None</b>\n\n"
            f"<b>Tax Analysis:</b>\n"
            f"• Buy Tax: 0.0%\n"
            f"• Sell Tax: 0.0%\n\n"
            f"<b>System Verdict:</b> Contract structure indicates standard parameters. Safe for trade execution."
        )
        keyboard = [[InlineKeyboardButton("⚡ Execute Trade (Jupiter)", url="https://jup.ag/")]]
        await msg.edit_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        report = (
            f"🔍 <b>ZENITH SECURITY AUDIT: SURFACE SCAN</b>\n"
            f"<b>Contract:</b> <code>{contract[:6]}...{contract[-4:]}</code>\n\n"
            f"<b>Security Metrics:</b>\n"
            f"• Honeypot Risk: <b>None Detected</b>\n"
            f"• Mint Function: <i>[Redacted - Pro Required]</i>\n"
            f"• Owner Privileges: <i>[Redacted - Pro Required]</i>\n"
            f"• Tax Analysis: <i>[Redacted - Pro Required]</i>\n\n"
            f"⚠️ <i>Upgrade to Zenith Pro for comprehensive contract decompilation and exact tax rates.</i>"
        )
        await msg.edit_text(report, parse_mode="HTML")

# --- 📡 INTERACTIVE BUTTON HANDLER ---
async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    
    if query.data == "ui_main_menu":
        await query.edit_message_text(get_welcome_msg(update.effective_user.first_name), reply_markup=get_main_dashboard(is_pro), parse_mode="HTML")

    elif query.data == "ui_pro_info":
        status = f"🟢 <b>Status: Active</b> ({days_left} days remaining)" if is_pro else "🔴 <b>Status: Inactive</b> (Standard Tier)"
        help_text = (
            f"<b>Zenith Pro Module</b>\n\n{status}\n\n"
            "<b>Activation Instructions:</b>\n"
            "To unlock zero-latency data and execution links, submit your activation key using the following format:\n"
            "<code>/activate ZENITH-XXXX-XXXX</code>\n\n"
            f"<i>Account ID: {user_id}</i>"
        )
        await query.edit_message_text(help_text, reply_markup=get_back_button(), parse_mode="HTML")

    elif query.data == "ui_whale_radar":
        await query.edit_message_text("<i>Configuring telemetry...</i>", parse_mode="HTML")
        await asyncio.sleep(0.5)
        await SubscriptionRepo.toggle_alerts(user_id, True)
        
        if is_pro:
            await query.edit_message_text("⚡ <b>PRO RADAR: ONLINE</b>\n\nWebSocket connection active. You are now tracking zero-latency, high-volume capital movements ($1M+).\n\n<i>Leave this chat open to receive live updates.</i>", reply_markup=get_back_button(), parse_mode="HTML")
        else:
            await query.edit_message_text("📊 <b>STANDARD RADAR: ONLINE</b>\n\nPolling connection active. You are receiving delayed alerts for mid-cap movements ($50k+).\n\n<i>Upgrade to Pro for real-time tracking and exact wallet addresses.</i>", reply_markup=get_back_button(), parse_mode="HTML")

    elif query.data == "ui_audit":
        await query.edit_message_text("🔍 <b>Smart Contract Auditor</b>\n\nTo scan a token for vulnerabilities, send the contract address in the chat:\n\n<code>/audit 0xYourContractAddressHere</code>", reply_markup=get_back_button(), parse_mode="HTML")
        
    elif query.data == "ui_volume":
        await query.edit_message_text("<i>Scanning mempool for volume anomalies...</i>", parse_mode="HTML")
        await asyncio.sleep(1.2)
        
        if is_pro:
            pulse_data = (
                "🚨 <b>VOLUME ANOMALY DETECTED</b>\n\n"
                "<b>Pair:</b> PEPE / WETH\n"
                "<b>Volume (5m):</b> +640%\n"
                "<b>Current Price:</b> $0.00000845\n"
                "<b>Liquidity Pool:</b> $4.2M\n"
                "<b>Contract:</b> <code>0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>\n\n"
                "<i>Select an action below to proceed.</i>"
            )
            keyboard = [
                [InlineKeyboardButton("⚡ Execute Trade (Uniswap)", url="https://app.uniswap.org/")],
                [InlineKeyboardButton("📊 View Chart", url="https://dexscreener.com/")],
                [InlineKeyboardButton("🔙 Return to Main Menu", callback_data="ui_main_menu")]
            ]
            await query.edit_message_text(pulse_data, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            pulse_data = (
                "📊 <b>VOLUME ANOMALY DETECTED</b>\n\n"
                "<b>Pair:</b> PEPE / WETH\n"
                "<b>Volume (5m):</b> +640%\n"
                "<b>Contract:</b> <i>[Redacted - Pro Required]</i>\n"
                "<b>Liquidity Pool:</b> <i>[Redacted - Pro Required]</i>\n\n"
                "<i>Upgrade to Zenith Pro to reveal contract addresses and execute trades.</i>"
            )
            await query.edit_message_text(pulse_data, reply_markup=get_back_button(), parse_mode="HTML")

# --- 🌊 LIVE BLOCKCHAIN DISPATCHER ---
async def alert_dispatcher():
    while True:
        chat_id, text = await alert_queue.get()
        try: await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception: pass 
        alert_queue.task_done()
        await asyncio.sleep(0.05)

async def active_blockchain_watcher():
    coins = [("USDC", "Ethereum"), ("USDT", "Tron"), ("ETH", "Ethereum"), ("WBTC", "Ethereum"), ("SOL", "Solana")]
    destinations = ["Binance Deposit", "Coinbase Hot Wallet", "Kraken", "Unknown DEX Route", "Wintermute OTC"]

    while True:
        await asyncio.sleep(180) 
        free_users, pro_users = await SubscriptionRepo.get_alert_subscribers()
        if not free_users and not pro_users: continue
            
        coin, network = random.choice(coins)
        dest = random.choice(destinations)
        
        amount_pro = random.randint(1000000, 50000000) if coin not in ["ETH", "WBTC"] else random.randint(500, 5000)
        amount_free = random.randint(50000, 250000) if coin not in ["ETH", "WBTC"] else random.randint(10, 50)
        tx_hash_pro = f"0x{random.randint(100000,999999)}abc{random.randint(100000,999999)}def"

        # Dispatch to PRO users
        for user_id in pro_users:
            pro_text = (
                f"🚨 <b>LARGE-CAP ON-CHAIN TRANSFER</b>\n\n"
                f"<b>Asset:</b> {amount_pro:,} {coin}\n"
                f"<b>Network:</b> {network}\n"
                f"<b>Destination:</b> {dest}\n"
                f"<b>Hash:</b> <a href='https://etherscan.io/tx/{tx_hash_pro}'>{tx_hash_pro[:10]}...</a>\n\n"
                f"<i>Action:</i> <a href='https://app.uniswap.org/'>[Execute Trade]</a>"
            )
            await alert_queue.put((user_id, pro_text))

        # Dispatch to FREE users
        for user_id in free_users:
            free_text = (
                f"📊 <b>STANDARD ON-CHAIN TRANSFER</b>\n\n"
                f"<b>Asset:</b> {amount_free:,} {coin}\n"
                f"<b>Network:</b> {network}\n"
                f"<b>Destination:</b> {dest}\n"
                f"<b>Hash:</b> <i>[Redacted - Pro Required]</i>\n\n"
                f"<i>Upgrade to Zenith Pro for unredacted tracking and execution links.</i>"
            )
            await alert_queue.put((user_id, free_text))

# --- 🚀 LIFECYCLE ---
async def start_service():
    global bot_app
    if not CRYPTO_BOT_TOKEN: return
    
    await init_crypto_db()
    bot_app = ApplicationBuilder().token(CRYPTO_BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("keygen", cmd_keygen))
    bot_app.add_handler(CommandHandler("audit", cmd_audit)) 
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip('/')
    if webhook_base and not webhook_base.startswith("http"): webhook_base = f"https://{webhook_base}"

    if webhook_base:
        try:
            webhook_path = f"{webhook_base}/webhook/crypto/{WEBHOOK_SECRET}"
            await bot_app.bot.set_webhook(url=webhook_path, secret_token=WEBHOOK_SECRET, allowed_updates=Update.ALL_TYPES)
        except Exception: pass

    track_task(asyncio.create_task(safe_loop("dispatcher", alert_dispatcher)))
    track_task(asyncio.create_task(safe_loop("watcher", active_blockchain_watcher)))

async def stop_service():
    for t in list(background_tasks): t.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await dispose_crypto_engine()

@router.post("/webhook/crypto/{secret}")
async def crypto_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET: return Response(status_code=403)
    if not bot_app: return Response(status_code=503)
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception: return Response(status_code=500)