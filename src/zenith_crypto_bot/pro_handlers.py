import asyncio
import contextlib

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, RetryAfter
from telegram.ext import ContextTypes

from core.animation import send_loading_message, send_typing_action
from core.logger import setup_logger
from core.validators import (
    validate_ethereum_address,
    validate_price,
    validate_wallet_label,
)
from zenith_crypto_bot import ui as crypto_ui
from zenith_crypto_bot.market_service import (
    get_fear_greed_index,
    get_gas_prices,
    get_new_pairs,
    get_prices,
    get_token_security,
    get_top_movers,
    resolve_token_id,
    search_token,
)
from zenith_crypto_bot.repository import PriceAlertRepo, SubscriptionRepo, WalletTrackerRepo, WatchlistRepo

logger = setup_logger("PRO_HANDLERS")


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not context.args or len(context.args) < 3:
        return await update.message.reply_text(crypto_ui.get_alert_help(), parse_mode="HTML")

    symbol = context.args[0].upper()
    direction = context.args[1].lower()

    if direction not in ("above", "below"):
        return await update.message.reply_text(crypto_ui.get_alert_direction_error(), parse_mode="HTML")

    target_price_str = context.args[2].replace(",", "")
    price_validation = validate_price(target_price_str)
    if not price_validation.is_valid:
        return await update.message.reply_text(
            crypto_ui.get_alert_price_error(price_validation.error_message), parse_mode="HTML"
        )

    target_price = float(price_validation.sanitized_value)
    count = await PriceAlertRepo.count_user_alerts(user_id)
    limit = 25 if is_pro else 1
    if count >= limit:
        msg, kb = crypto_ui.get_limit_reached_card("Price Alerts", count, limit, is_pro)
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    token_id = resolve_token_id(symbol)
    prices = await get_prices([token_id])
    if token_id not in prices:
        found = await search_token(symbol)
        if found:
            token_id = found["id"]
            symbol = found["symbol"]
        else:
            return await update.message.reply_text(crypto_ui.get_alert_token_not_found(symbol), parse_mode="HTML")

    await PriceAlertRepo.create_alert(user_id, token_id, symbol, target_price, direction)
    await update.message.reply_text(crypto_ui.get_alert_created(symbol, direction, target_price), parse_mode="HTML")


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    alerts = await PriceAlertRepo.get_user_alerts(user_id)
    if not alerts:
        return await update.message.reply_text(crypto_ui.get_alerts_empty(), parse_mode="HTML")

    msg = await send_loading_message(update, context, crypto_ui.get_alerts_loading())
    await msg.edit_text(
        crypto_ui.get_alerts_loaded(), reply_markup=crypto_ui.get_alerts_keyboard(alerts, is_pro), parse_mode="HTML"
    )


async def cmd_delalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(crypto_ui.get_delalert_usage())
    try:
        alert_id = int(context.args[0])
        deleted = await PriceAlertRepo.delete_alert(update.effective_user.id, alert_id)
        await update.message.reply_text(crypto_ui.get_delalert_result(deleted))
    except ValueError:
        await update.message.reply_text(crypto_ui.get_delalert_invalid())


async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    if not is_pro:
        msg, kb = crypto_ui.get_pro_feature_msg("Wallet Tracker")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    if not context.args:
        return await update.message.reply_text(crypto_ui.get_track_help(), parse_mode="HTML")

    address = context.args[0].strip()
    address_validation = validate_ethereum_address(address)
    if not address_validation.is_valid:
        return await update.message.reply_text(
            crypto_ui.get_track_address_error(address_validation.error_message), parse_mode="HTML"
        )

    address = address_validation.sanitized_value
    label = " ".join(context.args[1:]) if len(context.args) > 1 else "Unnamed Wallet"
    label_validation = validate_wallet_label(label)
    if not label_validation.is_valid:
        return await update.message.reply_text(
            crypto_ui.get_track_label_error(label_validation.error_message), parse_mode="HTML"
        )
    label = label_validation.sanitized_value

    count = await WalletTrackerRepo.count_user_wallets(user_id)
    limit = 5
    if count >= limit:
        msg, kb = crypto_ui.get_limit_reached_card("Tracked Wallets", count, limit, is_pro)
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    added = await WalletTrackerRepo.add_wallet(user_id, address, label)
    if added:
        await update.message.reply_text(crypto_ui.get_track_success(label, address), parse_mode="HTML")
    else:
        await update.message.reply_text(crypto_ui.get_already_tracked_msg(label), parse_mode="HTML")


async def cmd_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    wallets = await WalletTrackerRepo.get_user_wallets(user_id)
    if not wallets:
        return await update.message.reply_text(crypto_ui.get_wallets_empty(), parse_mode="HTML")

    msg = await send_loading_message(update, context, crypto_ui.get_wallets_loading())
    await msg.edit_text(
        crypto_ui.get_wallets_loaded(), reply_markup=crypto_ui.get_wallets_keyboard(wallets, is_pro), parse_mode="HTML"
    )


async def cmd_untrack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(crypto_ui.get_untrack_help(), parse_mode="HTML")

    address = context.args[0].strip()
    address_validation = validate_ethereum_address(address)
    if not address_validation.is_valid:
        return await update.message.reply_text(address_validation.error_message)

    address = address_validation.sanitized_value
    removed = await WalletTrackerRepo.remove_wallet(update.effective_user.id, address)
    if removed:
        await update.message.reply_text(crypto_ui.get_untrack_success())
    else:
        await update.message.reply_text(crypto_ui.get_untrack_not_found())


async def cmd_addtoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not context.args or len(context.args) < 2:
        return await update.message.reply_text(crypto_ui.get_addtoken_help(), parse_mode="HTML")

    limit = 20 if is_pro else 3
    count = await WatchlistRepo.count_watchlist(user_id)
    if count >= limit:
        return await update.message.reply_text(
            crypto_ui.get_addtoken_portfolio_full(count, limit, is_pro), parse_mode="HTML"
        )

    symbol = context.args[0].upper()
    try:
        entry_price = float(context.args[1].replace(",", ""))
        quantity = float(context.args[2].replace(",", "")) if len(context.args) > 2 else 1.0
    except ValueError:
        return await update.message.reply_text(crypto_ui.get_addtoken_invalid())

    token_id = resolve_token_id(symbol)
    prices = await get_prices([token_id])
    if token_id not in prices:
        found = await search_token(symbol)
        if found:
            token_id, symbol = found["id"], found["symbol"]
        else:
            return await update.message.reply_text(crypto_ui.get_addtoken_not_found(symbol), parse_mode="HTML")

    await WatchlistRepo.add_token(user_id, token_id, symbol, entry_price, quantity)
    current = prices.get(token_id, {}).get("usd", entry_price)
    pnl_pct = ((current - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    await update.message.reply_text(
        crypto_ui.get_addtoken_success(symbol, quantity, entry_price, current, pnl_pct), parse_mode="HTML"
    )


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tokens = await WatchlistRepo.get_watchlist(user_id)
    if not tokens:
        return await update.message.reply_text(crypto_ui.get_portfolio_empty(), parse_mode="HTML")

    msg = await send_loading_message(update, context, crypto_ui.get_portfolio_loading())
    token_ids = [t.token_id for t in tokens]
    prices = await get_prices(token_ids)
    text = crypto_ui.get_portfolio_card(tokens, prices)
    try:
        await msg.edit_text(text, reply_markup=crypto_ui.get_portfolio_keyboard(tokens), parse_mode="HTML")
    except Exception:
        await msg.edit_text(text, parse_mode="HTML")


async def cmd_removetoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(crypto_ui.get_removetoken_usage())
    token_id = resolve_token_id(context.args[0])
    removed = await WatchlistRepo.remove_token(update.effective_user.id, token_id)
    await update.message.reply_text(crypto_ui.get_removetoken_result(removed))


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await send_loading_message(update, context, crypto_ui.get_market_loading())
    fng, (gainers, losers), btc_data = await asyncio.gather(
        get_fear_greed_index(), get_top_movers(), get_prices(["bitcoin", "ethereum"])
    )
    is_pro = await SubscriptionRepo.is_pro(update.effective_user.id)

    fng_val = fng["value"] if fng else 0
    fng_class = fng["classification"] if fng else "N/A"
    gauge_bar = crypto_ui.build_gauge(fng_val)

    btc_price = btc_data.get("bitcoin", {}).get("usd", 0)
    btc_change = btc_data.get("bitcoin", {}).get("usd_24h_change", 0)
    eth_price = btc_data.get("ethereum", {}).get("usd", 0)
    eth_change = btc_data.get("ethereum", {}).get("usd_24h_change", 0)

    text = crypto_ui.get_market_card(
        fng_val, fng_class, gauge_bar, btc_price, btc_change, eth_price, eth_change, gainers, losers, is_pro
    )
    with contextlib.suppress(Exception):
        await msg.edit_text(text, reply_markup=crypto_ui.get_back_button(), parse_mode="HTML")


async def cmd_gainers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await send_loading_message(update, context, "Scanning top 24h market gainers...")
    gainers, _ = await get_top_movers()
    text = crypto_ui.get_gainers_card(gainers)
    with contextlib.suppress(Exception):
        await msg.edit_text(text, reply_markup=crypto_ui.get_back_button(), parse_mode="HTML")


async def cmd_losers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await send_loading_message(update, context, "Scanning top 24h market pullbacks...")
    _, losers = await get_top_movers()
    text = crypto_ui.get_losers_card(losers)
    with contextlib.suppress(Exception):
        await msg.edit_text(text, reply_markup=crypto_ui.get_back_button(), parse_mode="HTML")


cmd_watchlist = cmd_portfolio


async def cmd_gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = await send_loading_message(update, context, crypto_ui.get_gas_loading())
    gas = await get_gas_prices()
    if not gas:
        return await msg_obj.edit_text(crypto_ui.get_gas_unavailable())

    await msg_obj.edit_text(crypto_ui.get_gas_card(gas), reply_markup=crypto_ui.get_back_button(), parse_mode="HTML")


async def perform_real_audit(user_id: int, contract: str, msg, is_pro: bool):
    try:
        stages = crypto_ui.get_audit_scanning_stages(contract)
        for stage in stages:
            await msg.edit_text(f"<i>{stage}...</i>", parse_mode="HTML")
            await asyncio.sleep(0.4)

        security = await get_token_security(contract)
        await SubscriptionRepo.save_audit(user_id, contract)

        if not security:
            await msg.edit_text(
                crypto_ui.get_audit_no_data(contract),
                reply_markup=crypto_ui.get_back_button(),
                parse_mode="HTML",
            )
            return

        token_name = security.get("token_name", "Unknown")
        token_symbol = security.get("token_symbol", "???")
        is_honeypot = security.get("is_honeypot", "0") == "1"
        is_open_source = security.get("is_open_source", "0") == "1"
        is_proxy = security.get("is_proxy", "0") == "1"
        can_take_back = security.get("can_take_back_ownership", "0") == "1"
        owner_change_balance = security.get("owner_change_balance", "0") == "1"
        buy_tax = security.get("buy_tax", "0")
        sell_tax = security.get("sell_tax", "0")
        holder_count = security.get("holder_count", "N/A")
        lp_holder_count = security.get("lp_holder_count", "N/A")

        risk_score = 0
        risks = []
        if is_honeypot:
            risk_score += 40
            risks.append("HONEYPOT DETECTED")
        if not is_open_source:
            risk_score += 15
            risks.append("Contract not verified")
        if is_proxy:
            risk_score += 10
            risks.append("Proxy contract (upgradeable)")
        if can_take_back:
            risk_score += 20
            risks.append("Owner can reclaim ownership")
        if owner_change_balance:
            risk_score += 25
            risks.append("Owner can modify balances")
        try:
            if float(buy_tax) > 0.1:
                risk_score += 10
                risks.append(f"Buy tax: {float(buy_tax)*100:.1f}%")
            if float(sell_tax) > 0.1:
                risk_score += 15
                risks.append(f"Sell tax: {float(sell_tax)*100:.1f}%")
        except Exception:
            pass

        kb = [
            [InlineKeyboardButton("DexScreener", url=f"https://dexscreener.com/ethereum/{contract}")],
            [InlineKeyboardButton("Back", callback_data="ui_main_menu")],
        ]

        if is_pro:
            report = crypto_ui.get_audit_pro_report(
                token_name,
                token_symbol,
                contract,
                safety=crypto_ui.get_risk_label(risk_score),
                risk_score=risk_score,
                risks=risks,
                is_honeypot=is_honeypot,
                is_open_source=is_open_source,
                is_proxy=is_proxy,
                buy_tax=buy_tax,
                sell_tax=sell_tax,
                holder_count=holder_count,
                lp_holder_count=lp_holder_count,
            )
        else:
            report = crypto_ui.get_audit_free_report(
                token_name,
                token_symbol,
                contract,
                safety=crypto_ui.get_risk_label(risk_score),
                is_honeypot=is_honeypot,
            )

        await msg.edit_text(report, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.error(f"Audit error: {e}")


async def show_new_pairs(msg, is_pro: bool):
    pairs, _ = await get_new_pairs()
    if not pairs:
        await msg.edit_text(
            crypto_ui.get_new_pairs_empty(),
            reply_markup=crypto_ui.get_back_button(),
            parse_mode="HTML",
        )
        return

    await msg.edit_text(
        crypto_ui.get_new_pairs_card(pairs, is_pro),
        reply_markup=crypto_ui.get_back_button(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
