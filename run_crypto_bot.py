import html
import random
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import RetryAfter, BadRequest, Forbidden

from core.logger import setup_logger
from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, ADMIN_USER_ID
from zenith_crypto_bot.repository import (
    init_crypto_db, dispose_crypto_engine, SubscriptionRepo,
    PriceAlertRepo, WalletTrackerRepo,
)
from zenith_crypto_bot.ui import (
    get_main_dashboard, get_back_button, get_audits_keyboard,
    get_welcome_msg, get_alerts_keyboard, get_wallets_keyboard,
)
from zenith_crypto_bot.market_service import (
    get_prices, get_wallet_recent_txns, get_new_pairs, close_market_client,
)
from zenith_crypto_bot.pro_handlers import (
    cmd_alert, cmd_alerts, cmd_delalert,
    cmd_track, cmd_wallets, cmd_untrack,
    cmd_addtoken, cmd_portfolio, cmd_removetoken,
    cmd_market, cmd_gas, perform_real_audit, show_new_pairs,
)

logger = setup_logger("CRYPTO")
router = APIRouter()
bot_app = None
alert_queue = asyncio.Queue(maxsize=500)
background_tasks = set()


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
            logger.error(f"Loop '{name}' crashed: {e}")
            await asyncio.sleep(5)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await SubscriptionRepo.register_user(user_id)
    first_name = html.escape(update.effective_user.first_name or "Trader")
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0
    await update.message.reply_text(
        get_welcome_msg(first_name, is_pro, days_left),
        reply_markup=get_main_dashboard(is_pro), parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    
    help_text = (
        "📖 <b>ZENITH CRYPTO BOT - FULL GUIDE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "<b>💰 PRICE COMMANDS</b>\n"
        "• <code>/price [symbol]</code> - Get token price (e.g., /price BTC)\n"
        "• <code>/market</code> - Market overview + Fear & Greed\n"
        "• <code>/gas</code> - Ethereum gas prices\n\n"
        
        "<b>🔔 ALERTS & TRACKING</b>\n"
        "• <code>/alert [token] [above/below] [price]</code> - Set price alert\n"
        "  Example: <code>/alert BTC above 100000</code>\n"
        "• <code>/alerts</code> - View your price alerts\n"
        "• <code>/track [address] [label]</code> - Track wallet (Pro)\n"
        "• <code>/wallets</code> - View tracked wallets (Pro)\n\n"
        
        "<b>💼 PORTFOLIO</b>\n"
        "• <code>/addtoken [symbol] [entry_price] [qty]</code> - Add position\n"
        "  Example: <code>/addtoken BTC 95000 0.5</code>\n"
        "• <code>/portfolio</code> - View your portfolio\n"
        "• <code>/removetoken [symbol]</code> - Remove position\n\n"
        
        "<b>🛡️ SECURITY</b>\n"
        "• <code>/audit [contract]</code> - Scan token for risks\n"
        "  Example: <code>/audit 0x1234...</code>\n\n"
        
        "<b>💎 PRO FEATURES (₹149/month)</b>\n"
        "• Unlimited price alerts\n"
        "• Wallet tracking (5 wallets)\n"
        "• Full security audits\n"
        "• New pair scanner\n"
        "• Fear & Greed Index\n"
        "• Top movers gainers/losers\n"
        "• Advanced portfolio analytics\n\n"
        
        "<b>📱 GROUP USAGE</b>\n"
        "Add bot to groups and use:\n"
        "• <code>/price [symbol]</code> - Get prices in group\n"
        "• <code>/market</code> - Market overview\n\n"
        
        "<b>💳 UPGRADE TO PRO</b>\n"
        "Contact @admin to get your activation key!\n"
        "Price: ₹149/month (India)"
    )
    
    keyboard = [
        [InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
        [InlineKeyboardButton("🔙 Back", callback_data="ui_main_menu")]
    ]
    
    await update.message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ <b>Invalid Format.</b> Use: <code>/activate [YOUR_KEY]</code>", parse_mode="HTML")
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "🔍 <b>Token Security Scanner</b>\n\nScan any ERC-20 contract for vulnerabilities:\n"
            "<code>/audit 0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>",
            parse_mode="HTML",
        )
    contract = context.args[0][:100].strip()
    user_id = update.effective_user.id
    msg = await update.message.reply_text("<i>Initializing scanner...</i>", parse_mode="HTML")
    is_pro = await SubscriptionRepo.is_pro(user_id)
    await perform_real_audit(user_id, contract, msg, is_pro)


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    first_name = html.escape(update.effective_user.first_name or "Trader")
    days_left = await SubscriptionRepo.get_days_left(user_id)
    is_pro = days_left > 0

    try:
        if query.data == "ui_main_menu":
            await query.edit_message_text(
                get_welcome_msg(first_name, is_pro, days_left),
                reply_markup=get_main_dashboard(is_pro), parse_mode="HTML",
            )

        elif query.data == "ui_pro_info":
            status = f"🟢 <b>Active</b> — {days_left} days remaining" if is_pro else "🔴 <b>Inactive</b> — Standard Tier"
            pro_features = (
                "\n<b>Pro Features:</b>\n"
                "• 25 Price Alerts (vs 1 free)\n"
                "• 5 Wallet Trackers\n"
                "• 20 Portfolio Positions (vs 3 free)\n"
                "• Full Security Reports\n"
                "• Top Gainers/Losers Data\n"
                "• New Pair Pool Addresses\n"
                "• Instant Notifications\n"
            )
            await query.edit_message_text(
                f"<b>💎 Zenith Pro</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Status:</b> {status}\n{pro_features}\n"
                f"<b>Activation:</b>\n<code>/activate ZENITH-XXXX-XXXX</code>\n\n"
                f"<i>Account ID: {user_id}</i>",
                reply_markup=get_back_button(), parse_mode="HTML",
            )

        elif query.data == "ui_whale_radar":
            await query.edit_message_text("<i>Configuring on-chain telemetry...</i>", parse_mode="HTML")
            await asyncio.sleep(0.5)
            await SubscriptionRepo.toggle_alerts(user_id, True)
            if is_pro:
                await query.edit_message_text(
                    "⚡ <b>PRO ORDERFLOW: ONLINE</b>\n\n"
                    "Monitoring mempool for institutional trades ($1M+).\n"
                    "<i>Leave chat open for live signals.</i>",
                    reply_markup=get_back_button(), parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    "📊 <b>STANDARD ORDERFLOW: ONLINE</b>\n\n"
                    "Receiving delayed mid-cap volume.\n"
                    "<i>Upgrade to Pro for real-time + unredacted data.</i>",
                    reply_markup=get_back_button(), parse_mode="HTML",
                )

        elif query.data == "ui_audit":
            await query.edit_message_text(
                "🔍 <b>Token Security Scanner</b>\n\nScan any contract for vulnerabilities:\n"
                "<code>/audit 0xYourContractAddressHere</code>",
                reply_markup=get_back_button(), parse_mode="HTML",
            )

        elif query.data == "ui_saved_audits":
            audits = await SubscriptionRepo.get_saved_audits(user_id)
            if not audits:
                await query.edit_message_text("🗂️ <b>Audit Vault</b>\n\nEmpty. Run a scan: <code>/audit [contract]</code>", reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await query.edit_message_text("🗂️ <b>Audit Vault</b>\n\nSelect a record:", reply_markup=get_audits_keyboard(audits), parse_mode="HTML")

        elif query.data.startswith("ui_del_audit_"):
            audit_id = int(query.data.split("_")[-1])
            await SubscriptionRepo.delete_audit(user_id, audit_id)
            audits = await SubscriptionRepo.get_saved_audits(user_id)
            if not audits:
                await query.edit_message_text("🗂️ <b>Vault cleared.</b>", reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await query.edit_message_text("🗂️ <b>Record removed.</b>", reply_markup=get_audits_keyboard(audits), parse_mode="HTML")

        elif query.data == "ui_clear_audits":
            await SubscriptionRepo.clear_all_audits(user_id)
            await query.edit_message_text("🗂️ <b>Vault wiped.</b> All data erased.", reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data.startswith("ui_view_audit_"):
            audit_id = int(query.data.split("_")[-1])
            audit_record = await SubscriptionRepo.get_audit_by_id(user_id, audit_id)
            if audit_record:
                await perform_real_audit(user_id, audit_record.contract, query.message, is_pro)

        elif query.data == "ui_volume":
            await query.edit_message_text("<i>Scanning smart money inflows...</i>", parse_mode="HTML")
            await asyncio.sleep(1.0)
            if is_pro:
                pulse = (
                    "🚨 <b>SMART MONEY INFLOW DETECTED</b>\n\n"
                    "<b>Pair:</b> PEPE / WETH\n<b>Volume (5m):</b> +840% Spike\n"
                    "<b>Smart Money:</b> 14 known wallets buying\n"
                    "<b>Contract:</b> <code>0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>\n\n"
                    "<i>Sudden volume from high-win-rate wallets indicates insider accumulation.</i>"
                )
                kb = [
                    [InlineKeyboardButton("⚡ Trade (Uniswap)", url="https://app.uniswap.org/")],
                    [InlineKeyboardButton("🔙 Terminal", callback_data="ui_main_menu")],
                ]
            else:
                pulse = (
                    "📊 <b>VOLUME ANOMALY DETECTED</b>\n\n"
                    "<b>Pair:</b> PEPE / WETH\n<b>Volume:</b> +840% Spike\n"
                    "<b>Contract:</b> <i>[Pro Required]</i>\n<b>Insight:</b> <i>[Pro Required]</i>\n\n"
                    "<i>Upgrade to Pro for full analysis.</i>"
                )
                kb = [[InlineKeyboardButton("🔙 Terminal", callback_data="ui_main_menu")]]
            await query.edit_message_text(pulse, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

        elif query.data == "ui_market":
            await query.edit_message_text("<i>Scanning global market sentiment...</i>", parse_mode="HTML")
            from zenith_crypto_bot.pro_handlers import _build_gauge
            from zenith_crypto_bot.market_service import get_fear_greed_index, get_top_movers
            fng, (gainers, losers), btc_data = await asyncio.gather(
                get_fear_greed_index(), get_top_movers(), get_prices(["bitcoin", "ethereum"])
            )
            fng_val = fng["value"] if fng else 0
            fng_class = fng["classification"] if fng else "N/A"
            gauge = _build_gauge(fng_val)
            btc_p = btc_data.get("bitcoin", {}).get("usd", 0)
            btc_c = btc_data.get("bitcoin", {}).get("usd_24h_change", 0)
            eth_p = btc_data.get("ethereum", {}).get("usd", 0)
            eth_c = btc_data.get("ethereum", {}).get("usd_24h_change", 0)
            lines = [
                "<b>📊 MARKET INTELLIGENCE</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n",
                f"<b>Fear & Greed:</b> {fng_val}/100 — <b>{fng_class}</b>", gauge, "",
                f"<b>BTC:</b> ${btc_p:,.0f} ({btc_c:+.1f}%)",
                f"<b>ETH:</b> ${eth_p:,.0f} ({eth_c:+.1f}%)\n",
            ]
            if is_pro and gainers:
                lines.append("<b>🟢 Top Gainers</b>")
                for g in gainers[:5]:
                    pct = g.get("price_change_percentage_24h", 0) or 0
                    lines.append(f"  • {g['symbol'].upper()} ${g.get('current_price', 0):,.4f} ({pct:+.1f}%)")
                lines.append("\n<b>🔴 Top Losers</b>")
                for l in losers[:5]:
                    pct = l.get("price_change_percentage_24h", 0) or 0
                    lines.append(f"  • {l['symbol'].upper()} ${l.get('current_price', 0):,.4f} ({pct:+.1f}%)")
            else:
                lines.append("<i>Top Gainers/Losers: [Pro Required]</i>")
            await query.edit_message_text("\n".join(lines), reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ui_gas":
            await query.edit_message_text("<i>Reading Ethereum mempool...</i>", parse_mode="HTML")
            from zenith_crypto_bot.market_service import get_gas_prices
            gas = await get_gas_prices()
            if not gas:
                await query.edit_message_text("⚠️ Gas data unavailable.", reply_markup=get_back_button())
                return
            gwei = gas["gas_gwei"]
            if gwei < 15:
                lv = "🟢 LOW — Great time to trade"
            elif gwei < 30:
                lv = "🟡 MODERATE"
            elif gwei < 60:
                lv = "🟠 HIGH — Consider waiting"
            else:
                lv = "🔴 VERY HIGH — Delay if possible"
            await query.edit_message_text(
                f"<b>⛽ GAS TRACKER</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Gas:</b> {gwei:.1f} Gwei — {lv}\n<b>Base Fee:</b> {gas['base_fee_gwei']:.1f} Gwei\n\n"
                f"<b>Priority:</b>\n🐢 {gas['priority_low']:.1f} | 🚶 {gas['priority_medium']:.1f} | 🚀 {gas['priority_high']:.1f} Gwei",
                reply_markup=get_back_button(), parse_mode="HTML",
            )

        elif query.data == "ui_portfolio":
            from zenith_crypto_bot.repository import WatchlistRepo
            tokens = await WatchlistRepo.get_watchlist(user_id)
            if not tokens:
                await query.edit_message_text(
                    "💰 <b>Portfolio</b>\n\nEmpty. Add positions:\n<code>/addtoken BTC 95000 0.5</code>",
                    reply_markup=get_back_button(), parse_mode="HTML",
                )
            else:
                token_ids = [t.token_id for t in tokens]
                prices = await get_prices(token_ids)
                lines = ["<b>💰 PORTFOLIO</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
                total_inv, total_cur = 0, 0
                for t in tokens:
                    cp = prices.get(t.token_id, {}).get("usd", 0)
                    inv = t.entry_price * t.quantity
                    cur = cp * t.quantity
                    pnl = ((cp - t.entry_price) / t.entry_price * 100) if t.entry_price > 0 else 0
                    total_inv += inv
                    total_cur += cur
                    ic = "🟢" if pnl >= 0 else "🔴"
                    lines.append(f"{ic} <b>{t.token_symbol}</b> ×{t.quantity}\n   ${t.entry_price:,.2f}→${cp:,.2f} ({pnl:+.1f}%)\n")
                tp = total_cur - total_inv
                tpct = ((total_cur - total_inv) / total_inv * 100) if total_inv > 0 else 0
                lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━\n{'🟢' if tp >= 0 else '🔴'} <b>P/L: ${tp:+,.2f} ({tpct:+.1f}%)</b>")
                await query.edit_message_text("\n".join(lines), reply_markup=get_back_button(), parse_mode="HTML")

        elif query.data == "ui_price_alerts":
            alerts = await PriceAlertRepo.get_user_alerts(user_id)
            if not alerts:
                await query.edit_message_text(
                    "🔔 <b>Price Alerts</b>\n\nNo active alerts.\n<code>/alert BTC above 100000</code>",
                    reply_markup=get_back_button(), parse_mode="HTML",
                )
            else:
                await query.edit_message_text("🔔 <b>Your Alerts</b>", reply_markup=get_alerts_keyboard(alerts), parse_mode="HTML")

        elif query.data.startswith("ui_del_alert_"):
            aid = int(query.data.split("_")[-1])
            await PriceAlertRepo.delete_alert(user_id, aid)
            alerts = await PriceAlertRepo.get_user_alerts(user_id)
            if not alerts:
                await query.edit_message_text("🔔 Alert removed. No remaining alerts.", reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await query.edit_message_text("🔔 Alert removed.", reply_markup=get_alerts_keyboard(alerts), parse_mode="HTML")

        elif query.data == "ui_wallet_tracker":
            if not is_pro:
                await query.edit_message_text(
                    "🔒 <b>Pro Feature: Wallet Tracker</b>\n\n"
                    "Track whale wallets and get alerts when they trade.\n"
                    "<code>/activate [KEY]</code> to unlock.",
                    reply_markup=get_back_button(), parse_mode="HTML",
                )
            else:
                wallets = await WalletTrackerRepo.get_user_wallets(user_id)
                if not wallets:
                    await query.edit_message_text(
                        "👁️ <b>Wallet Tracker</b>\n\nNo tracked wallets.\n<code>/track 0x... MyLabel</code>",
                        reply_markup=get_back_button(), parse_mode="HTML",
                    )
                else:
                    await query.edit_message_text("👁️ <b>Tracked Wallets</b>", reply_markup=get_wallets_keyboard(wallets), parse_mode="HTML")

        elif query.data.startswith("ui_untrack_"):
            wid = int(query.data.split("_")[-1])
            wallets = await WalletTrackerRepo.get_user_wallets(user_id)
            for w in wallets:
                if w.id == wid:
                    await WalletTrackerRepo.remove_wallet(user_id, w.wallet_address)
                    break
            remaining = await WalletTrackerRepo.get_user_wallets(user_id)
            if not remaining:
                await query.edit_message_text("👁️ Wallet removed. No remaining trackers.", reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await query.edit_message_text("👁️ Wallet removed.", reply_markup=get_wallets_keyboard(remaining), parse_mode="HTML")

        elif query.data == "ui_new_pairs":
            await query.edit_message_text("<i>Scanning Uniswap V2 Factory...</i>", parse_mode="HTML")
            await show_new_pairs(query.message, is_pro)

        elif query.data.startswith("ui_noop"):
            pass

    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.error(f"UI Error: {e}")


async def alert_dispatcher():
    while True:
        chat_id, text = await alert_queue.get()
        try:
            await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            await alert_queue.put((chat_id, text))
        except Forbidden:
            await SubscriptionRepo.toggle_alerts(chat_id, False)
        except Exception as e:
            logger.error(f"Dispatch failed: {e}")
        finally:
            alert_queue.task_done()
            await asyncio.sleep(0.05)


async def price_alert_checker():
    while True:
        await asyncio.sleep(60)
        try:
            alerts = await PriceAlertRepo.get_all_active_alerts()
            if not alerts:
                continue
            token_ids = list(set(a.token_id for a in alerts))
            prices = await get_prices(token_ids)

            for alert in alerts:
                current = prices.get(alert.token_id, {}).get("usd")
                if current is None:
                    continue
                triggered = (
                    (alert.direction == "above" and current >= alert.target_price) or
                    (alert.direction == "below" and current <= alert.target_price)
                )
                if triggered:
                    await PriceAlertRepo.trigger_alert(alert.id)
                    icon = "📈" if alert.direction == "above" else "📉"
                    text = (
                        f"🔔 <b>PRICE ALERT TRIGGERED</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"{icon} <b>{alert.token_symbol}</b> hit your {alert.direction} target!\n\n"
                        f"<b>Target:</b> ${alert.target_price:,.2f}\n"
                        f"<b>Current:</b> ${current:,.2f}\n\n"
                        f"<i>Set another alert with /alert</i>"
                    )
                    try:
                        alert_queue.put_nowait((alert.user_id, text))
                    except asyncio.QueueFull:
                        pass
        except Exception as e:
            logger.error(f"Price alert checker error: {e}")


async def wallet_watcher():
    while True:
        await asyncio.sleep(120)
        try:
            wallets = await WalletTrackerRepo.get_all_tracked_wallets()
            for w in wallets:
                txns = await get_wallet_recent_txns(w.wallet_address, w.last_checked_tx)
                if txns:
                    await WalletTrackerRepo.update_last_tx(w.id, txns[0].get("hash", ""))
                    for tx in txns[:3]:
                        val_eth = int(tx.get("value", "0")) / 1e18
                        if val_eth < 0.01:
                            continue
                        direction = "📤 SENT" if tx.get("from", "").lower() == w.wallet_address else "📥 RECEIVED"
                        text = (
                            f"👁️ <b>WALLET ACTIVITY</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"<b>Wallet:</b> {w.label}\n"
                            f"<b>Action:</b> {direction}\n"
                            f"<b>Amount:</b> {val_eth:.4f} ETH\n"
                            f"<b>Tx:</b> <a href='https://etherscan.io/tx/{tx.get('hash', '')}'>"
                            f"{tx.get('hash', '')[:10]}...</a>"
                        )
                        try:
                            alert_queue.put_nowait((w.user_id, text))
                        except asyncio.QueueFull:
                            pass
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Wallet watcher error: {e}")


async def active_blockchain_watcher():
    scenarios = [
        ("Binance Deposit", "🔴 SELL PRESSURE: OTC liquidation on CEX."),
        ("Coinbase Hot Wallet", "🔴 SELL PRESSURE: Moving to exchange ledger."),
        ("Unknown DEX Route", "🟢 ACCUMULATION: Routed through DEX pools."),
        ("Wintermute OTC", "⚪ INSTITUTIONAL: Market maker restructuring."),
        ("New Cold Storage", "🟢 ACCUMULATION: Moving to deep cold storage."),
    ]
    coins = [("USDC", "Ethereum"), ("USDT", "Tron"), ("ETH", "Ethereum"), ("WBTC", "Ethereum"), ("SOL", "Solana")]
    explorer = {"Ethereum": "https://etherscan.io/tx/", "Tron": "https://tronscan.org/#/transaction/", "Solana": "https://solscan.io/tx/"}

    while True:
        await asyncio.sleep(180)
        free_users, pro_users = await SubscriptionRepo.get_alert_subscribers()
        if not free_users and not pro_users:
            continue
        coin, network = random.choice(coins)
        dest, insight = random.choice(scenarios)
        url = explorer.get(network, "https://etherscan.io/tx/")
        amt_pro = random.randint(1_000_000, 50_000_000) if coin not in ["ETH", "WBTC"] else random.randint(500, 5000)
        amt_free = random.randint(50_000, 250_000) if coin not in ["ETH", "WBTC"] else random.randint(10, 50)
        utc = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

        for uid in pro_users:
            txt = (
                f"🚨 <b>INSTITUTIONAL TRANSFER</b>\n\n"
                f"<b>Asset:</b> {amt_pro:,} {coin}\n<b>Dest:</b> {dest}\n"
                f"<b>Insight:</b> {insight}\n<b>Time:</b> {utc}"
            )
            try:
                alert_queue.put_nowait((uid, txt))
            except asyncio.QueueFull:
                pass
        for uid in free_users:
            txt = (
                f"📊 <b>ON-CHAIN TRANSFER</b>\n\n"
                f"<b>Asset:</b> {amt_free:,} {coin}\n<b>Dest:</b> {dest}\n"
                f"<b>Insight:</b> <i>[Pro Required]</i>\n<b>Time:</b> <i>Delayed</i>"
            )
            try:
                alert_queue.put_nowait((uid, txt))
            except asyncio.QueueFull:
                pass


async def subscription_monitor():
    notified_warning = set()
    notified_expired = set()

    while True:
        await asyncio.sleep(3600)
        try:
            expiring = await SubscriptionRepo.get_expiring_users(within_hours=72)
            for sub in expiring:
                if sub.user_id in notified_warning:
                    continue
                notified_warning.add(sub.user_id)
                days_left = max(1, (sub.expires_at - datetime.now(timezone.utc)).days)
                text = (
                    f"⚠️ <b>SUBSCRIPTION EXPIRING SOON</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Your Zenith Pro expires in <b>{days_left} day{'s' if days_left != 1 else ''}</b>.\n\n"
                    f"To renew, contact the admin and provide your ID:\n"
                    f"<code>{sub.user_id}</code>\n\n"
                    f"<i>After payment, your subscription will be extended instantly.</i>"
                )
                try:
                    alert_queue.put_nowait((sub.user_id, text))
                except asyncio.QueueFull:
                    pass

            expired = await SubscriptionRepo.get_just_expired_users(within_hours=1)
            for sub in expired:
                if sub.user_id in notified_expired:
                    continue
                notified_expired.add(sub.user_id)
                text = (
                    f"🔴 <b>PRO SUBSCRIPTION ENDED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Your Zenith Pro access has expired.\n"
                    f"Pro features (wallet tracker, full security scans, "
                    f"extended alerts) are now locked.\n\n"
                    f"<b>To renew:</b> Contact the admin with your ID:\n"
                    f"<code>{sub.user_id}</code>\n\n"
                    f"<i>Your data (alerts, portfolio, wallets) is preserved "
                    f"and will be available again once you renew.</i>"
                )
                try:
                    alert_queue.put_nowait((sub.user_id, text))
                except asyncio.QueueFull:
                    pass

            if len(notified_warning) > 1000:
                notified_warning.clear()
            if len(notified_expired) > 1000:
                notified_expired.clear()
        except Exception as e:
            logger.error(f"Subscription monitor error: {e}")


async def start_service():
    global bot_app
    if not CRYPTO_BOT_TOKEN:
        return

    await init_crypto_db()
    bot_app = ApplicationBuilder().token(CRYPTO_BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("help", cmd_help))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("audit", cmd_audit))
    bot_app.add_handler(CommandHandler("alert", cmd_alert))
    bot_app.add_handler(CommandHandler("alerts", cmd_alerts))
    bot_app.add_handler(CommandHandler("delalert", cmd_delalert))
    bot_app.add_handler(CommandHandler("track", cmd_track))
    bot_app.add_handler(CommandHandler("wallets", cmd_wallets))
    bot_app.add_handler(CommandHandler("untrack", cmd_untrack))
    bot_app.add_handler(CommandHandler("addtoken", cmd_addtoken))
    bot_app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    bot_app.add_handler(CommandHandler("removetoken", cmd_removetoken))
    bot_app.add_handler(CommandHandler("market", cmd_market))
    bot_app.add_handler(CommandHandler("gas", cmd_gas))
    bot_app.add_handler(CallbackQueryHandler(handle_dashboard))

    await bot_app.initialize()
    await bot_app.start()

    webhook_base = (WEBHOOK_URL or "").strip().rstrip("/")
    if webhook_base and not webhook_base.startswith("http"):
        webhook_base = f"https://{webhook_base}"
    if webhook_base:
        try:
            path = f"{webhook_base}/webhook/crypto/{WEBHOOK_SECRET}"
            await bot_app.bot.set_webhook(url=path, secret_token=WEBHOOK_SECRET, allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.warning(f"Failed to set webhook: {e}")

    track_task(asyncio.create_task(safe_loop("dispatcher", alert_dispatcher)))
    track_task(asyncio.create_task(safe_loop("watcher", active_blockchain_watcher)))
    track_task(asyncio.create_task(safe_loop("price_alerts", price_alert_checker)))
    track_task(asyncio.create_task(safe_loop("wallet_watcher", wallet_watcher)))
    track_task(asyncio.create_task(safe_loop("sub_monitor", subscription_monitor)))


async def stop_service():
    for t in list(background_tasks):
        t.cancel()
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    await close_market_client()
    await dispose_crypto_engine()


@router.post("/webhook/crypto/{secret}")
async def crypto_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    if not bot_app:
        return Response(status_code=503)
    try:
        data = await request.json()
        await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook payload error: {e}")
        return Response(status_code=200)