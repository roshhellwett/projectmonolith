import asyncio
import contextlib
import html
import random
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import Response
from telegram import Update
from telegram.error import BadRequest, Forbidden, RetryAfter
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

from core.config import CRYPTO_BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL
from core.database import dispose_engine
from core.logger import setup_logger
from zenith_crypto_bot import ui as crypto_ui
from zenith_crypto_bot.ai_handlers import cmd_ai, cmd_delkey, cmd_mykey, cmd_setkey, handle_ai_followup
from zenith_crypto_bot.market_service import (
    close_market_client,
    get_prices,
    get_wallet_recent_txns,
)
from zenith_crypto_bot.pro_handlers import (
    cmd_addtoken,
    cmd_alert,
    cmd_alerts,
    cmd_delalert,
    cmd_gas,
    cmd_market,
    cmd_portfolio,
    cmd_removetoken,
    cmd_track,
    cmd_untrack,
    cmd_wallets,
    perform_real_audit,
    show_new_pairs,
)
from zenith_crypto_bot.repository import (
    PriceAlertRepo,
    SubscriptionRepo,
    WalletTrackerRepo,
    WatchlistRepo,
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
        crypto_ui.get_welcome_msg(first_name, is_pro, days_left),
        reply_markup=crypto_ui.get_main_dashboard(is_pro),
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await SubscriptionRepo.is_pro(update.effective_user.id)
    keyboard = crypto_ui.get_back_button()
    await update.message.reply_text(crypto_ui.get_help_msg(), reply_markup=keyboard, parse_mode="HTML")


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(crypto_ui.get_activate_help(), parse_mode="HTML")
    key_string = context.args[0].strip()
    success, msg = await SubscriptionRepo.redeem_key(update.effective_user.id, key_string)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(crypto_ui.get_audit_help(), parse_mode="HTML")
    contract = context.args[0][:100].strip()
    user_id = update.effective_user.id
    msg = await update.message.reply_text("Initializing scanner...")
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
                crypto_ui.get_welcome_msg(first_name, is_pro, days_left),
                reply_markup=crypto_ui.get_main_dashboard(is_pro),
                parse_mode="HTML",
            )

        elif query.data == "ui_pro_info":
            await query.edit_message_text(
                crypto_ui.get_pro_info_msg(is_pro, days_left, user_id),
                reply_markup=crypto_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "ui_whale_radar":
            await query.edit_message_text("Configuring on-chain telemetry...")
            await asyncio.sleep(0.5)
            await SubscriptionRepo.toggle_alerts(user_id, True)
            await query.edit_message_text(
                crypto_ui.get_whale_radar_on(is_pro),
                reply_markup=crypto_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "ui_audit":
            await query.edit_message_text(
                crypto_ui.get_audit_help(),
                reply_markup=crypto_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "ui_saved_audits":
            audits = await SubscriptionRepo.get_saved_audits(user_id)
            if not audits:
                await query.edit_message_text(
                    crypto_ui.get_audit_vault_empty(),
                    reply_markup=crypto_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    crypto_ui.get_audit_vault_select(),
                    reply_markup=crypto_ui.get_audits_keyboard(audits),
                    parse_mode="HTML",
                )

        elif query.data.startswith("ui_del_audit_"):
            audit_id = int(query.data.split("_")[-1])
            await SubscriptionRepo.delete_audit(user_id, audit_id)
            audits = await SubscriptionRepo.get_saved_audits(user_id)
            if not audits:
                await query.edit_message_text(
                    crypto_ui.get_audit_vault_cleared(),
                    reply_markup=crypto_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    crypto_ui.get_audit_deleted(),
                    reply_markup=crypto_ui.get_audits_keyboard(audits),
                    parse_mode="HTML",
                )

        elif query.data == "ui_clear_audits":
            await SubscriptionRepo.clear_all_audits(user_id)
            await query.edit_message_text(
                crypto_ui.get_audit_vault_cleared(),
                reply_markup=crypto_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data.startswith("ui_view_audit_"):
            audit_id = int(query.data.split("_")[-1])
            audit_record = await SubscriptionRepo.get_audit_by_id(user_id, audit_id)
            if audit_record:
                await perform_real_audit(user_id, audit_record.contract, query.message, is_pro)

        elif query.data == "ui_volume":
            await query.edit_message_text("Scanning smart money inflows...")
            await asyncio.sleep(1.0)
            kb = crypto_ui.get_back_button()
            await query.edit_message_text(
                crypto_ui.get_volume_pulse(is_pro),
                reply_markup=kb if not is_pro else None,
                parse_mode="HTML",
            )

        elif query.data == "ui_market":
            await query.edit_message_text(crypto_ui.get_market_loading())
            from zenith_crypto_bot.market_service import get_fear_greed_index, get_top_movers

            fng, (gainers, losers), btc_data = await asyncio.gather(
                get_fear_greed_index(), get_top_movers(), get_prices(["bitcoin", "ethereum"])
            )
            fng_val = fng["value"] if fng else 0
            fng_class = fng["classification"] if fng else "N/A"
            gauge_bar = crypto_ui.build_gauge(fng_val)
            btc_p = btc_data.get("bitcoin", {}).get("usd", 0)
            btc_c = btc_data.get("bitcoin", {}).get("usd_24h_change", 0)
            eth_p = btc_data.get("ethereum", {}).get("usd", 0)
            eth_c = btc_data.get("ethereum", {}).get("usd_24h_change", 0)
            await query.edit_message_text(
                crypto_ui.get_market_card(fng_val, fng_class, gauge_bar, btc_p, btc_c, eth_p, eth_c, gainers, losers, is_pro),
                reply_markup=crypto_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "ui_gas":
            await query.edit_message_text(crypto_ui.get_gas_loading())
            from zenith_crypto_bot.market_service import get_gas_prices

            gas = await get_gas_prices()
            if not gas:
                await query.edit_message_text(crypto_ui.get_gas_unavailable(), reply_markup=crypto_ui.get_back_button())
                return
            await query.edit_message_text(
                crypto_ui.get_gas_card(gas),
                reply_markup=crypto_ui.get_back_button(),
                parse_mode="HTML",
            )

        elif query.data == "ui_portfolio":
            tokens = await WatchlistRepo.get_watchlist(user_id)
            if not tokens:
                await query.edit_message_text(
                    crypto_ui.get_portfolio_empty(),
                    reply_markup=crypto_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                token_ids = [t.token_id for t in tokens]
                prices = await get_prices(token_ids)
                await query.edit_message_text(
                    crypto_ui.get_portfolio_card(tokens, prices),
                    reply_markup=crypto_ui.get_portfolio_keyboard(),
                    parse_mode="HTML",
                )

        elif query.data == "ui_price_alerts":
            alerts = await PriceAlertRepo.get_user_alerts(user_id)
            if not alerts:
                await query.edit_message_text(
                    crypto_ui.get_alerts_empty(),
                    reply_markup=crypto_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    crypto_ui.get_alerts_loaded(),
                    reply_markup=crypto_ui.get_alerts_keyboard(alerts),
                    parse_mode="HTML",
                )

        elif query.data.startswith("ui_del_alert_confirm_"):
            aid = int(query.data.split("_")[-1])
            alerts = await PriceAlertRepo.get_user_alerts(user_id)
            alert = next((a for a in alerts if a.id == aid), None)
            if alert:
                await query.edit_message_text(
                    crypto_ui.get_confirm_delete_alert_msg(alert),
                    reply_markup=crypto_ui.get_confirm_delete_alert(alert),
                    parse_mode="HTML",
                )

        elif query.data.startswith("ui_del_alert_"):
            aid = int(query.data.split("_")[-1])
            await PriceAlertRepo.delete_alert(user_id, aid)
            alerts = await PriceAlertRepo.get_user_alerts(user_id)
            if not alerts:
                await query.edit_message_text(
                    crypto_ui.get_alerts_empty(),
                    reply_markup=crypto_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    crypto_ui.get_alerts_loaded(),
                    reply_markup=crypto_ui.get_alerts_keyboard(alerts),
                    parse_mode="HTML",
                )

        elif query.data == "ui_wallet_tracker":
            if not is_pro:
                msg, kb = crypto_ui.get_pro_feature_msg("Wallet Tracker")
                await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")
            else:
                wallets = await WalletTrackerRepo.get_user_wallets(user_id)
                if not wallets:
                    await query.edit_message_text(
                        crypto_ui.get_wallets_empty(),
                        reply_markup=crypto_ui.get_back_button(),
                        parse_mode="HTML",
                    )
                else:
                    await query.edit_message_text(
                        crypto_ui.get_wallets_loaded(),
                        reply_markup=crypto_ui.get_wallets_keyboard(wallets),
                        parse_mode="HTML",
                    )

        elif query.data.startswith("ui_untrack_confirm_"):
            wid = int(query.data.split("_")[-1])
            wallets = await WalletTrackerRepo.get_user_wallets(user_id)
            wallet = next((w for w in wallets if w.id == wid), None)
            if wallet:
                await query.edit_message_text(
                    crypto_ui.get_confirm_untrack_msg(wallet),
                    reply_markup=crypto_ui.get_confirm_untrack_wallet(wallet),
                    parse_mode="HTML",
                )

        elif query.data.startswith("ui_untrack_"):
            wid = int(query.data.split("_")[-1])
            wallets = await WalletTrackerRepo.get_user_wallets(user_id)
            for w in wallets:
                if w.id == wid:
                    await WalletTrackerRepo.remove_wallet(user_id, w.wallet_address)
                    break
            remaining = await WalletTrackerRepo.get_user_wallets(user_id)
            if not remaining:
                await query.edit_message_text(
                    crypto_ui.get_wallets_empty(),
                    reply_markup=crypto_ui.get_back_button(),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    crypto_ui.get_wallets_loaded(),
                    reply_markup=crypto_ui.get_wallets_keyboard(remaining),
                    parse_mode="HTML",
                )

        elif query.data == "ui_new_pairs":
            await query.edit_message_text(crypto_ui.get_new_pairs_loading())
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
                triggered = (alert.direction == "above" and current >= alert.target_price) or (
                    alert.direction == "below" and current <= alert.target_price
                )
                if triggered:
                    await PriceAlertRepo.trigger_alert(alert.id)
                    text = crypto_ui.get_price_alert_triggered(alert.token_symbol, alert.direction, alert.target_price, current)
                    with contextlib.suppress(asyncio.QueueFull):
                        alert_queue.put_nowait((alert.user_id, text))
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
                        direction = "SENT" if tx.get("from", "").lower() == w.wallet_address else "RECEIVED"
                        tx_hash = tx.get("hash", "")
                        text = crypto_ui.get_wallet_activity(w.label, direction, val_eth, tx_hash)
                        with contextlib.suppress(asyncio.QueueFull):
                            alert_queue.put_nowait((w.user_id, text))
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Wallet watcher error: {e}")


async def active_blockchain_watcher():
    scenarios = [
        ("Binance Deposit", "OTC liquidation on CEX."),
        ("Coinbase Hot Wallet", "Moving to exchange ledger."),
        ("Unknown DEX Route", "Accumulation: Routed through DEX pools."),
        ("Wintermute OTC", "Institutional: Market maker restructuring."),
        ("New Cold Storage", "Accumulation: Moving to deep cold storage."),
    ]
    coins = [("USDC", "Ethereum"), ("USDT", "Tron"), ("ETH", "Ethereum"), ("WBTC", "Ethereum"), ("SOL", "Solana")]

    while True:
        await asyncio.sleep(180)
        free_users, pro_users = await SubscriptionRepo.get_alert_subscribers()
        if not free_users and not pro_users:
            continue
        coin, network = random.choice(coins)
        dest, insight = random.choice(scenarios)
        amt_pro = random.randint(1_000_000, 50_000_000) if coin not in ["ETH", "WBTC"] else random.randint(500, 5000)
        amt_free = random.randint(50_000, 250_000) if coin not in ["ETH", "WBTC"] else random.randint(10, 50)
        utc = datetime.now(UTC).strftime("%H:%M:%S UTC")

        for uid in pro_users:
            txt = crypto_ui.get_institutional_transfer(coin, amt_pro, dest, insight, utc)
            with contextlib.suppress(asyncio.QueueFull):
                alert_queue.put_nowait((uid, txt))
        for uid in free_users:
            txt = crypto_ui.get_onchain_transfer(coin, amt_free, dest, utc)
            with contextlib.suppress(asyncio.QueueFull):
                alert_queue.put_nowait((uid, txt))


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
                days_left = max(1, (sub.expires_at - datetime.now(UTC)).days)
                text = crypto_ui.get_subscription_expiring(sub.user_id, days_left)
                with contextlib.suppress(asyncio.QueueFull):
                    alert_queue.put_nowait((sub.user_id, text))

            expired = await SubscriptionRepo.get_just_expired_users(within_hours=1)
            for sub in expired:
                if sub.user_id in notified_expired:
                    continue
                notified_expired.add(sub.user_id)
                text = crypto_ui.get_subscription_expired(sub.user_id)
                with contextlib.suppress(asyncio.QueueFull):
                    alert_queue.put_nowait((sub.user_id, text))

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
    bot_app.add_handler(CommandHandler("ai", cmd_ai))
    bot_app.add_handler(CommandHandler("setkey", cmd_setkey))
    bot_app.add_handler(CommandHandler("mykey", cmd_mykey))
    bot_app.add_handler(CommandHandler("delkey", cmd_delkey))
    bot_app.add_handler(CallbackQueryHandler(handle_ai_followup, pattern="^ai_followup_"))
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
    await dispose_engine()


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
