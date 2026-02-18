import html
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, RetryAfter
from telegram.ext import ContextTypes

from core.logger import setup_logger
from core.validators import (
    validate_ethereum_address,
    validate_price,
    validate_token_symbol,
    validate_wallet_label,
)
from core.animation import (
    send_typing_action,
    edit_with_stages,
    create_confirm_keyboard,
)
from zenith_crypto_bot.repository import SubscriptionRepo, PriceAlertRepo, WalletTrackerRepo, WatchlistRepo
from zenith_crypto_bot.market_service import (
    get_prices, resolve_token_id, search_token, get_token_security,
    get_wallet_recent_txns, get_wallet_token_txns,
    get_fear_greed_index, get_top_movers, get_gas_prices, get_new_pairs,
)
from zenith_crypto_bot.ui import (
    get_back_button, get_alerts_keyboard, get_wallets_keyboard,
    get_confirm_delete_alert, get_confirm_delete_alert_msg,
    get_confirm_untrack_msg, get_confirm_untrack_wallet,
    get_limit_reached_card, get_already_tracked_msg, get_pro_feature_msg,
)

logger = setup_logger("PRO_HANDLERS")


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not context.args or len(context.args) < 3:
        return await update.message.reply_text(
            "🔔 <b>Price Alert Setup</b>\n\n"
            "<b>Format:</b> <code>/alert [TOKEN] [above/below] [PRICE]</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/alert BTC above 100000</code>\n"
            "• <code>/alert ETH below 2000</code>\n"
            "• <code>/alert SOL above 250</code>\n\n"
            "<i>💡 Tip: Use comma separators for large numbers, e.g., 100,000</i>",
            parse_mode="HTML",
        )

    symbol = context.args[0].upper()
    direction = context.args[1].lower()
    
    if direction not in ("above", "below"):
        return await update.message.reply_text(
            "⚠️ <b>Invalid Direction</b>\n\n"
            "Direction must be <code>above</code> or <code>below</code>.\n\n"
            "<b>Example:</b> <code>/alert BTC above 100000</code>",
            parse_mode="HTML"
        )

    target_price_str = context.args[2].replace(",", "")
    
    price_validation = validate_price(target_price_str)
    if not price_validation.is_valid:
        return await update.message.reply_text(
            f"⚠️ <b>Invalid Price</b>\n\n"
            f"{price_validation.error_message}\n\n"
            "<b>Example:</b> <code>/alert BTC above 100000</code>",
            parse_mode="HTML"
        )
    
    target_price = float(price_validation.sanitized_value)

    count = await PriceAlertRepo.count_user_alerts(user_id)
    limit = 25 if is_pro else 1
    if count >= limit:
        msg, kb = get_limit_reached_card("Price Alerts", count, limit, is_pro)
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    token_id = resolve_token_id(symbol)
    prices = await get_prices([token_id])
    if token_id not in prices:
        found = await search_token(symbol)
        if found:
            token_id = found["id"]
            symbol = found["symbol"]
        else:
            return await update.message.reply_text(
                f"⚠️ <b>Token Not Found</b>\n\n"
                f"Token <code>{html.escape(symbol)}</code> was not found.\n\n"
                "Try a different symbol or check for typos.",
                parse_mode="HTML"
            )

    await PriceAlertRepo.create_alert(user_id, token_id, symbol, target_price, direction)
    icon = "📈" if direction == "above" else "📉"
    await update.message.reply_text(
        f"✅ <b>Alert Created</b>\n\n"
        f"{icon} <b>{symbol}</b> → {direction} <b>${target_price:,.2f}</b>\n\n"
        f"<i>You'll receive an instant notification when the price crosses your target.</i>",
        parse_mode="HTML",
    )


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    alerts = await PriceAlertRepo.get_user_alerts(user_id)
    
    if not alerts:
        return await update.message.reply_text(
            "🔔 <b>Price Alerts</b>\n\n"
            "No active alerts.\n\n"
            "<b>Create one:</b>\n"
            "<code>/alert BTC above 100000</code>",
            parse_mode="HTML",
        )
    
    msg = await update.message.reply_text(
        "⏳ <i>Loading your alerts...</i>",
        parse_mode="HTML"
    )
    
    await msg.edit_text(
        "🔔 <b>Your Active Alerts</b>",
        reply_markup=get_alerts_keyboard(alerts, is_pro),
        parse_mode="HTML"
    )


async def cmd_delalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: <code>/delalert [ID]</code>", parse_mode="HTML")
    try:
        alert_id = int(context.args[0])
        deleted = await PriceAlertRepo.delete_alert(update.effective_user.id, alert_id)
        msg = "✅ Alert removed." if deleted else "⚠️ Alert not found."
        await update.message.reply_text(msg)
    except ValueError:
        await update.message.reply_text("⚠️ Invalid alert ID.")


async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        msg, kb = get_pro_feature_msg("Wallet Tracker")
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    if not context.args:
        return await update.message.reply_text(
            "👁️ <b>Wallet Tracker</b>\n\n"
            "<b>Format:</b> <code>/track [ADDRESS] [LABEL]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/track 0x28C6c06298d514Db089934071355E5743bf21d60 Binance14</code>\n\n"
            "<i>💡 Tip: Label helps you identify the wallet (e.g., Whale, Exchange, DeFi)</i>",
            parse_mode="HTML",
        )

    address = context.args[0].strip()
    
    address_validation = validate_ethereum_address(address)
    if not address_validation.is_valid:
        return await update.message.reply_text(
            f"⚠️ <b>Invalid Address</b>\n\n"
            f"{address_validation.error_message}\n\n"
            "<b>Example:</b>\n"
            "<code>0x28C6c06298d514Db089934071355E5743bf21d60</code>",
            parse_mode="HTML"
        )
    
    address = address_validation.sanitized_value

    label = " ".join(context.args[1:]) if len(context.args) > 1 else "Unnamed Wallet"
    label_validation = validate_wallet_label(label)
    if not label_validation.is_valid:
        return await update.message.reply_text(
            f"⚠️ <b>Invalid Label</b>\n\n"
            f"{label_validation.error_message}",
            parse_mode="HTML"
        )
    label = label_validation.sanitized_value

    count = await WalletTrackerRepo.count_user_wallets(user_id)
    limit = 5
    if count >= limit:
        msg, kb = get_limit_reached_card("Tracked Wallets", count, limit, is_pro)
        return await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

    added = await WalletTrackerRepo.add_wallet(user_id, address, label)
    if added:
        await update.message.reply_text(
            f"✅ <b>Wallet Tracked</b>\n\n"
            f"👁️ <b>{html.escape(label)}</b>\n"
            f"<code>{address}</code>\n\n"
            f"<i>You'll receive alerts when this wallet makes transactions.</i>",
            parse_mode="HTML",
        )
    else:
        existing_label = "Unnamed Wallet"
        await update.message.reply_text(
            get_already_tracked_msg(existing_label),
            parse_mode="HTML"
        )


async def cmd_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)
    wallets = await WalletTrackerRepo.get_user_wallets(user_id)
    
    if not wallets:
        return await update.message.reply_text(
            "👁️ <b>Wallet Tracker</b>\n\n"
            "No tracked wallets.\n\n"
            "<b>Track a wallet:</b>\n"
            "<code>/track 0x... MyLabel</code>",
            parse_mode="HTML",
        )
    
    msg = await update.message.reply_text(
        "⏳ <i>Loading wallets...</i>",
        parse_mode="HTML"
    )
    
    await msg.edit_text(
        "👁️ <b>Your Tracked Wallets</b>",
        reply_markup=get_wallets_keyboard(wallets, is_pro),
        parse_mode="HTML"
    )


async def cmd_untrack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "👁️ <b>Untrack Wallet</b>\n\n"
            "<b>Usage:</b> <code>/untrack [ADDRESS]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/untrack 0x28C6c06298d514Db089934071355E5743bf21d60</code>",
            parse_mode="HTML"
        )
    
    address = context.args[0].strip()
    
    address_validation = validate_ethereum_address(address)
    if not address_validation.is_valid:
        return await update.message.reply_text(
            f"⚠️ <b>Invalid Address</b>\n\n"
            f"{address_validation.error_message}",
            parse_mode="HTML"
        )
    
    address = address_validation.sanitized_value
    removed = await WalletTrackerRepo.remove_wallet(update.effective_user.id, address)
    
    if removed:
        await update.message.reply_text(
            "✅ <b>Wallet Untracked</b>\n\n"
            "You will no longer receive alerts for this wallet.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "⚠️ <b>Wallet Not Found</b>\n\n"
            "This wallet is not in your tracking list.\n\n"
            "Use <code>/wallets</code> to see your tracked wallets.",
            parse_mode="HTML"
        )


async def cmd_addtoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not context.args or len(context.args) < 2:
        return await update.message.reply_text(
            "💰 <b>Portfolio Tracker</b>\n\n"
            "<b>Format:</b> <code>/addtoken [TOKEN] [ENTRY_PRICE] [QTY]</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/addtoken BTC 95000 0.5</code>\n"
            "• <code>/addtoken ETH 2500</code>  (qty defaults to 1)",
            parse_mode="HTML",
        )

    limit = 20 if is_pro else 3
    count = await WatchlistRepo.count_watchlist(user_id)
    if count >= limit:
        tier_msg = "Upgrade to <b>Pro</b> for 20 slots." if not is_pro else "Maximum 20 positions."
        return await update.message.reply_text(f"⚠️ Portfolio full ({count}/{limit}). {tier_msg}", parse_mode="HTML")

    symbol = context.args[0].upper()
    try:
        entry_price = float(context.args[1].replace(",", ""))
        quantity = float(context.args[2].replace(",", "")) if len(context.args) > 2 else 1.0
    except ValueError:
        return await update.message.reply_text("⚠️ Invalid price or quantity.")

    token_id = resolve_token_id(symbol)
    prices = await get_prices([token_id])
    if token_id not in prices:
        found = await search_token(symbol)
        if found:
            token_id, symbol = found["id"], found["symbol"]
        else:
            return await update.message.reply_text(f"⚠️ Token <code>{html.escape(symbol)}</code> not found.", parse_mode="HTML")

    await WatchlistRepo.add_token(user_id, token_id, symbol, entry_price, quantity)
    current = prices.get(token_id, {}).get("usd", entry_price)
    pnl_pct = ((current - entry_price) / entry_price) * 100 if entry_price > 0 else 0
    icon = "🟢" if pnl_pct >= 0 else "🔴"

    await update.message.reply_text(
        f"✅ <b>Position Added</b>\n\n"
        f"<b>{symbol}</b> × {quantity}\n"
        f"Entry: ${entry_price:,.2f} → Now: ${current:,.2f}\n"
        f"{icon} P/L: {pnl_pct:+.2f}%",
        parse_mode="HTML",
    )


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tokens = await WatchlistRepo.get_watchlist(user_id)
    if not tokens:
        return await update.message.reply_text(
            "💰 <b>Portfolio</b>\n\nEmpty. Add positions with:\n<code>/addtoken BTC 95000 0.5</code>",
            parse_mode="HTML",
        )

    msg = await update.message.reply_text("<i>Loading live portfolio data...</i>", parse_mode="HTML")
    token_ids = [t.token_id for t in tokens]
    prices = await get_prices(token_ids)

    lines = ["<b>💰 PORTFOLIO OVERVIEW</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    total_invested = 0
    total_current = 0

    for t in tokens:
        current_price = prices.get(t.token_id, {}).get("usd", 0)
        change_24h = prices.get(t.token_id, {}).get("usd_24h_change", 0)
        invested = t.entry_price * t.quantity
        current_val = current_price * t.quantity
        pnl_pct = ((current_price - t.entry_price) / t.entry_price * 100) if t.entry_price > 0 else 0
        pnl_usd = current_val - invested
        total_invested += invested
        total_current += current_val
        icon = "🟢" if pnl_pct >= 0 else "🔴"
        lines.append(
            f"{icon} <b>{t.token_symbol}</b> × {t.quantity}\n"
            f"   ${t.entry_price:,.2f} → ${current_price:,.2f} "
            f"({pnl_pct:+.1f}%) <i>${pnl_usd:+,.2f}</i>\n"
            f"   24h: {change_24h:+.1f}%\n"
        )

    total_pnl = total_current - total_invested
    total_pnl_pct = ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0
    total_icon = "🟢" if total_pnl >= 0 else "🔴"
    lines.append(
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{total_icon} <b>TOTAL P/L: ${total_pnl:+,.2f} ({total_pnl_pct:+.1f}%)</b>\n"
        f"Invested: ${total_invested:,.2f} → Value: ${total_current:,.2f}"
    )

    try:
        await msg.edit_text("\n".join(lines), reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        await msg.edit_text("\n".join(lines), parse_mode="HTML")


async def cmd_removetoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: <code>/removetoken BTC</code>", parse_mode="HTML")
    token_id = resolve_token_id(context.args[0])
    removed = await WatchlistRepo.remove_token(update.effective_user.id, token_id)
    msg = "✅ Position removed." if removed else "⚠️ Token not in portfolio."
    await update.message.reply_text(msg)


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("<i>Scanning global market sentiment...</i>", parse_mode="HTML")
    fng, (gainers, losers), btc_data = await asyncio.gather(
        get_fear_greed_index(), get_top_movers(), get_prices(["bitcoin", "ethereum"])
    )
    is_pro = await SubscriptionRepo.is_pro(update.effective_user.id)

    fng_val = fng["value"] if fng else 0
    fng_class = fng["classification"] if fng else "N/A"
    gauge_bar = _build_gauge(fng_val)

    btc_price = btc_data.get("bitcoin", {}).get("usd", 0)
    btc_change = btc_data.get("bitcoin", {}).get("usd_24h_change", 0)
    eth_price = btc_data.get("ethereum", {}).get("usd", 0)
    eth_change = btc_data.get("ethereum", {}).get("usd_24h_change", 0)

    lines = [
        "<b>📊 MARKET INTELLIGENCE REPORT</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
        f"<b>Fear & Greed Index:</b> {fng_val}/100 — <b>{fng_class}</b>",
        f"{gauge_bar}\n",
        f"<b>BTC:</b> ${btc_price:,.0f} ({btc_change:+.1f}%)",
        f"<b>ETH:</b> ${eth_price:,.0f} ({eth_change:+.1f}%)\n",
    ]

    if is_pro and gainers:
        lines.append("<b>🟢 Top Gainers (24h)</b>")
        for g in gainers[:5]:
            pct = g.get("price_change_percentage_24h", 0) or 0
            lines.append(f"  • {g['symbol'].upper()} ${g.get('current_price', 0):,.4f} ({pct:+.1f}%)")
        lines.append("")
        lines.append("<b>🔴 Top Losers (24h)</b>")
        for l in losers[:5]:
            pct = l.get("price_change_percentage_24h", 0) or 0
            lines.append(f"  • {l['symbol'].upper()} ${l.get('current_price', 0):,.4f} ({pct:+.1f}%)")
    else:
        lines.append("<i>Top Gainers/Losers: [Pro Required]</i>")

    try:
        await msg.edit_text("\n".join(lines), reply_markup=get_back_button(), parse_mode="HTML")
    except Exception:
        pass


def _build_gauge(value: int) -> str:
    filled = value // 5
    empty = 20 - filled
    if value <= 25:
        emoji = "🔴"
    elif value <= 45:
        emoji = "🟠"
    elif value <= 55:
        emoji = "🟡"
    elif value <= 75:
        emoji = "🟢"
    else:
        emoji = "💚"
    return f"{emoji} {'█' * filled}{'░' * empty} {value}%"


async def cmd_gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = await update.message.reply_text("<i>Reading Ethereum mempool...</i>", parse_mode="HTML")
    gas = await get_gas_prices()

    if not gas:
        return await msg_obj.edit_text("⚠️ Gas data unavailable. ETH RPC may be offline.")

    gwei = gas["gas_gwei"]
    if gwei < 15:
        level, color = "🟢 LOW", "Excellent time to trade."
    elif gwei < 30:
        level, color = "🟡 MODERATE", "Acceptable for most transactions."
    elif gwei < 60:
        level, color = "🟠 HIGH", "Consider waiting for lower fees."
    else:
        level, color = "🔴 VERY HIGH", "Delay non-urgent transactions."

    text = (
        f"<b>⛽ ETHEREUM GAS TRACKER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Current Gas:</b> {gwei:.1f} Gwei — {level}\n"
        f"<b>Base Fee:</b> {gas['base_fee_gwei']:.1f} Gwei\n\n"
        f"<b>Priority Tiers:</b>\n"
        f"  🐢 Low: {gas['priority_low']:.1f} Gwei\n"
        f"  🚶 Medium: {gas['priority_medium']:.1f} Gwei\n"
        f"  🚀 High: {gas['priority_high']:.1f} Gwei\n\n"
        f"<b>Recommendation:</b> <i>{color}</i>"
    )
    await msg_obj.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")


async def perform_real_audit(user_id: int, contract: str, msg, is_pro: bool):
    try:
        from zenith_crypto_bot.repository import SubscriptionRepo as SR

        await msg.edit_text(f"<i>Connecting to GoPlus Security Oracle...</i>", parse_mode="HTML")
        await asyncio.sleep(0.4)
        await msg.edit_text(f"<i>Scanning bytecode for {contract[:8]}...</i>", parse_mode="HTML")

        security = await get_token_security(contract)
        await SR.save_audit(user_id, contract)

        if not security:
            await msg.edit_text(
                f"🔍 <b>SCAN COMPLETE</b>\n\n"
                f"<b>Contract:</b> <code>{contract}</code>\n\n"
                f"⚠️ No on-chain data found. The contract may be too new, on a different chain, or invalid.\n\n"
                f"<i>Tip: Ensure this is an Ethereum (ERC-20) contract address.</i>",
                reply_markup=get_back_button(), parse_mode="HTML",
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
            risks.append("🔴 HONEYPOT DETECTED")
        if not is_open_source:
            risk_score += 15
            risks.append("🟠 Contract not verified")
        if is_proxy:
            risk_score += 10
            risks.append("🟡 Proxy contract (upgradeable)")
        if can_take_back:
            risk_score += 20
            risks.append("🔴 Owner can reclaim ownership")
        if owner_change_balance:
            risk_score += 25
            risks.append("🔴 Owner can modify balances")
        try:
            if float(buy_tax) > 0.1:
                risk_score += 10
                risks.append(f"🟠 Buy tax: {float(buy_tax)*100:.1f}%")
            if float(sell_tax) > 0.1:
                risk_score += 15
                risks.append(f"🔴 Sell tax: {float(sell_tax)*100:.1f}%")
        except Exception:
            pass

        safety = "🟢 LOW RISK" if risk_score < 20 else "🟡 MODERATE" if risk_score < 40 else "🔴 HIGH RISK"

        if is_pro:
            detail = "\n".join(f"  {r}" for r in risks) if risks else "  ✅ No significant risks detected."
            report = (
                f"🛡️ <b>ZENITH SECURITY REPORT — PRO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Token:</b> {html.escape(token_name)} ({html.escape(token_symbol)})\n"
                f"<b>Contract:</b> <code>{contract}</code>\n"
                f"<b>Risk Level:</b> {safety} ({risk_score}/100)\n\n"
                f"<b>Security Analysis:</b>\n{detail}\n\n"
                f"<b>On-Chain Metrics:</b>\n"
                f"  • Honeypot: <b>{'⛔ YES' if is_honeypot else '✅ No'}</b>\n"
                f"  • Source Verified: <b>{'✅ Yes' if is_open_source else '❌ No'}</b>\n"
                f"  • Proxy Contract: <b>{'⚠️ Yes' if is_proxy else '✅ No'}</b>\n"
                f"  • Buy Tax: <b>{float(buy_tax)*100:.1f}%</b>\n"
                f"  • Sell Tax: <b>{float(sell_tax)*100:.1f}%</b>\n"
                f"  • Holders: <b>{holder_count}</b>\n"
                f"  • LP Holders: <b>{lp_holder_count}</b>\n"
            )
            kb = [
                [InlineKeyboardButton("📊 DexScreener", url=f"https://dexscreener.com/ethereum/{contract}")],
                [InlineKeyboardButton("🔙 Terminal", callback_data="ui_main_menu")],
            ]
        else:
            report = (
                f"🔍 <b>ZENITH SURFACE SCAN</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Token:</b> {html.escape(token_name)} ({html.escape(token_symbol)})\n"
                f"<b>Contract:</b> <code>{contract[:6]}...{contract[-4:]}</code>\n"
                f"<b>Risk Level:</b> {safety}\n\n"
                f"<b>Security:</b>\n"
                f"  • Honeypot: <b>{'⛔ YES' if is_honeypot else '✅ No'}</b>\n"
                f"  • Tax Rates: <i>[Pro Required]</i>\n"
                f"  • Holder Analysis: <i>[Pro Required]</i>\n"
                f"  • Full Risk Breakdown: <i>[Pro Required]</i>\n\n"
                f"⚠️ <i>Upgrade to Pro for complete security intelligence.</i>"
            )
            kb = [[InlineKeyboardButton("🔙 Terminal", callback_data="ui_main_menu")]]

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
            "🆕 <b>New Pair Scanner</b>\n\n"
            "No new pairs detected in the last ~10 minutes.\n"
            "<i>Check back soon — scanner runs continuously.</i>",
            reply_markup=get_back_button(), parse_mode="HTML",
        )
        return

    lines = ["🆕 <b>NEWLY CREATED PAIRS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for p in pairs:
        t0 = f"{p['token0'][:6]}...{p['token0'][-4:]}"
        t1 = f"{p['token1'][:6]}...{p['token1'][-4:]}"
        if is_pro:
            lines.append(
                f"<b>Pair:</b> {t0} / {t1}\n"
                f"<b>Pool:</b> <code>{p['pair']}</code>\n"
                f"<b>Block:</b> {p['block']:,}\n"
                f"<a href='https://etherscan.io/tx/{p['tx_hash']}'>View Tx</a> · "
                f"<a href='https://dexscreener.com/ethereum/{p['pair']}'>Chart</a>\n"
            )
        else:
            lines.append(
                f"<b>Pair:</b> {t0} / {t1}\n"
                f"<b>Pool:</b> <i>[Pro Required]</i>\n"
                f"<b>Block:</b> {p['block']:,}\n"
            )

    if not is_pro:
        lines.append("\n<i>Upgrade to Pro for pool addresses, tx links, and live charts.</i>")

    await msg.edit_text("\n".join(lines), reply_markup=get_back_button(), parse_mode="HTML", disable_web_page_preview=True)
