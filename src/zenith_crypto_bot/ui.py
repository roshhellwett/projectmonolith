from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID
from core.formatters import format_address, format_divider


def get_main_dashboard(is_pro: bool = False, alert_count: int = 0, alert_limit: int = 1, wallet_count: int = 0, wallet_limit: int = 0):
    tier = "PRO" if is_pro else "STANDARD"
    alert_info = f" ({alert_count}/{alert_limit})" if alert_limit > 0 else ""
    wallet_info = f" ({wallet_count}/{wallet_limit})" if wallet_limit > 0 else ""

    keyboard = [
        [InlineKeyboardButton("Market Intelligence", callback_data="ui_market"),
         InlineKeyboardButton("Gas Tracker", callback_data="ui_gas")],
        [InlineKeyboardButton("Token Security Scan", callback_data="ui_audit"),
         InlineKeyboardButton("Audit Vault", callback_data="ui_saved_audits")],
        [InlineKeyboardButton("Portfolio & P/L", callback_data="ui_portfolio"),
         InlineKeyboardButton(f"Price Alerts{alert_info}", callback_data="ui_price_alerts")],
        [InlineKeyboardButton(f"Wallet Tracker{wallet_info}", callback_data="ui_wallet_tracker"),
         InlineKeyboardButton("Smart Money Pulse", callback_data="ui_volume")],
        [InlineKeyboardButton("New Pair Scanner", callback_data="ui_new_pairs"),
         InlineKeyboardButton("Live Orderflow", callback_data="ui_whale_radar")],
        [InlineKeyboardButton(f"{tier} ACCESS", callback_data="ui_pro_info"),
         InlineKeyboardButton("Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_audits_keyboard(audits):
    keyboard = []
    for a in audits:
        short = format_address(a.contract, 6, 4)
        keyboard.append([InlineKeyboardButton(short, callback_data=f"ui_view_audit_{a.id}"),
                          InlineKeyboardButton("Delete", callback_data=f"ui_del_audit_{a.id}")])
    if audits:
        keyboard.append([InlineKeyboardButton("Clear All", callback_data="ui_clear_audits")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_alerts_keyboard(alerts, is_pro: bool = False):
    keyboard = []
    for a in alerts:
        direction = "Above" if a.direction == "above" else "Below"
        label = f"{a.token_symbol} {direction} ${a.target_price:,.2f}"
        if a.is_triggered:
            label += " (Triggered)"
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"ui_alert_{a.id}"),
            InlineKeyboardButton("Delete", callback_data=f"ui_del_alert_confirm_{a.id}"),
        ])
    keyboard.append([InlineKeyboardButton("Add Alert", callback_data="ui_add_alert_help")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_delete_alert(alert):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes, Delete", callback_data=f"ui_del_alert_{alert.id}"),
         InlineKeyboardButton("Cancel", callback_data="ui_price_alerts")],
    ])


def get_confirm_delete_alert_msg(alert):
    direction = "above" if alert.direction == "above" else "below"
    return (
        f"Confirm Delete Alert?\n\n"
        f"{alert.token_symbol} {direction} ${alert.target_price:,.2f}\n\n"
        f"This action cannot be undone."
    )


def get_wallets_keyboard(wallets, is_pro: bool = False):
    keyboard = []
    for w in wallets:
        short = format_address(w.wallet_address, 6, 4)
        keyboard.append([
            InlineKeyboardButton(f"{w.label}: {short}", callback_data=f"ui_wallet_{w.id}"),
            InlineKeyboardButton("Untrack", callback_data=f"ui_untrack_confirm_{w.id}"),
        ])
    limit = 5 if is_pro else 0
    if limit > 0:
        keyboard.append([InlineKeyboardButton(f"Track Wallet ({len(wallets)}/{limit})", callback_data="ui_track_help")])
    else:
        keyboard.append([InlineKeyboardButton("Track Wallet", callback_data="ui_track_help")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_untrack_wallet(wallet):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes, Untrack", callback_data=f"ui_untrack_{wallet.id}"),
         InlineKeyboardButton("Cancel", callback_data="ui_wallet_tracker")],
    ])


def get_confirm_untrack_msg(wallet):
    short = format_address(wallet.wallet_address, 8, 6)
    return (
        f"Confirm Untrack Wallet?\n\n"
        f"{wallet.label}\n"
        f"<code>{short}</code>\n\n"
        f"You will stop receiving transaction alerts for this wallet."
    )


def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="ui_main_menu")]])


def get_limit_reached_card(feature: str, current: int, limit: int, is_pro: bool = False):
    if is_pro:
        msg = f"Limit Reached: {feature}\n\nYou've reached your maximum of {limit}. Remove some to add more."
    else:
        msg = (
            f"Limit Reached: {feature}\n\n"
            f"Current: {current}/{limit}\n"
            f"Upgrade to PRO: {limit * 5}x more\n\n"
            f"Pro Benefits:\n"
            f"\u2022 25 price alerts (vs 1)\n"
            f"\u2022 5 tracked wallets (vs 0)\n"
            f"\u2022 Full security scans"
        )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
        [InlineKeyboardButton("Back", callback_data="ui_main_menu")],
    ])
    return msg, kb


def get_already_tracked_msg(wallet_label: str = None):
    if wallet_label:
        return (
            f"Already Tracked\n\n"
            f"This wallet is already being tracked as {wallet_label}.\n\n"
            f"Use /untrack [ADDRESS] to remove it first."
        )
    return (
        "Already Tracked\n\n"
        "This wallet is already in your tracking list.\n\n"
        "Use /wallets to view your tracked wallets."
    )


def get_pro_feature_msg(feature: str):
    msg = (
        f"Pro Feature: {feature}\n\n"
        f"This feature is available exclusively for PRO members.\n\n"
        f"Pro Benefits:\n"
        f"\u2022 Unlimited price alerts\n"
        f"\u2022 5 whale wallet tracking\n"
        f"\u2022 Full GoPlus security scans\n"
        f"\u2022 Real-time smart money alerts\n"
        f"\u2022 Unlimited portfolio positions\n"
        f"\u2022 New pair scanner\n"
        f"\u2022 Fear & Greed Index"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
        [InlineKeyboardButton("Activate Key", callback_data="ui_activate_help")],
        [InlineKeyboardButton("Back", callback_data="ui_main_menu")],
    ])
    return msg, kb


def get_welcome_msg(name: str, is_pro: bool = False, days_left: int = 0):
    title = "Zenith Crypto Terminal"
    if is_pro:
        detail = (
            f"PRO Active \u2014 {days_left} days remaining\n"
            "Full access: real-time alerts, wallet tracking, deep security scans."
        )
    else:
        detail = (
            "Standard Access (Free)\n"
            "Limited to delayed data and surface-level scans.\n"
            "Use /activate [KEY] to unlock Pro."
        )
    return (
        f"<b>{title}</b>\n"
        f"{format_divider()}\n"
        f"Welcome, <b>{name}</b>.\n\n"
        f"{detail}\n\n"
        f"{format_divider()}\n"
        f"<b>Available Modules:</b>\n"
        f"\u2022 Market Intel \u2014 Fear & Greed, Top Movers\n"
        f"\u2022 Token Scanner \u2014 Smart contract security audits\n"
        f"\u2022 Portfolio P/L \u2014 Track positions with live pricing\n"
        f"\u2022 Price Alerts \u2014 Automated threshold notifications\n"
        f"\u2022 Wallet Tracker \u2014 Copy-trade whale movements\n"
        f"\u2022 New Pairs \u2014 Fresh liquidity pool detection\n"
        f"\u2022 Gas Optimizer \u2014 Time your trades for lowest fees\n\n"
        f"Select a module below to begin."
    )


def get_pro_info_msg(is_pro: bool, days_left: int, user_id: int) -> str:
    status = f"Active \u2014 {days_left} days remaining" if is_pro else "Inactive \u2014 Standard Tier"
    pro_features = (
        "\nPro Features:\n"
        "\u2022 25 Price Alerts (vs 1 free)\n"
        "\u2022 5 Wallet Trackers\n"
        "\u2022 20 Portfolio Positions (vs 3 free)\n"
        "\u2022 Full Security Reports\n"
        "\u2022 Top Gainers/Losers Data\n"
        "\u2022 New Pair Pool Addresses\n"
        "\u2022 Instant Notifications"
    )
    return (
        f"<b>Zenith Pro</b>\n{format_divider()}\n\n"
        f"Status: {status}\n{pro_features}\n"
        f"Activation:\n/activate ZENITH-XXXX-XXXX\n\n"
        f"Account ID: {user_id}"
    )


def get_help_msg() -> str:
    return (
        "<b>Zenith Crypto Bot \u2014 Full Guide</b>\n"
        f"{format_divider()}\n\n"
        "<b>Price Commands:</b>\n"
        "\u2022 /price [symbol] \u2014 Get token price (e.g., /price BTC)\n"
        "\u2022 /market \u2014 Market overview + Fear & Greed\n"
        "\u2022 /gas \u2014 Ethereum gas prices\n\n"
        "<b>Alerts & Tracking:</b>\n"
        "\u2022 /alert [token] [above/below] [price] \u2014 Set price alert\n"
        "\u2022 /alerts \u2014 View your price alerts\n"
        "\u2022 /track [address] [label] \u2014 Track wallet (Pro)\n"
        "\u2022 /wallets \u2014 View tracked wallets (Pro)\n\n"
        "<b>Portfolio:</b>\n"
        "\u2022 /addtoken [symbol] [entry_price] [qty] \u2014 Add position\n"
        "\u2022 /portfolio \u2014 View your portfolio\n"
        "\u2022 /removetoken [symbol] \u2014 Remove position\n\n"
        "<b>Security:</b>\n"
        "\u2022 /audit [contract] \u2014 Scan token for risks\n\n"
        "<b>Pro Features (from ₹149/month):</b>\n"
        "\u2022 Unlimited price alerts\n"
        "\u2022 Wallet tracking (5 wallets)\n"
        "\u2022 Full security audits\n"
        "\u2022 New pair scanner\n"
        "\u2022 Fear & Greed Index\n"
        "\u2022 Top movers gainers/losers\n"
        "\u2022 Advanced portfolio analytics\n\n"
        "<b>Group Usage:</b>\n"
        "Add bot to groups and use:\n"
        "\u2022 /price [symbol] \u2014 Get prices in group\n"
        "\u2022 /market \u2014 Market overview\n\n"
        "<b>Upgrade to Pro:</b>\n"
        "Contact @admin to get your activation key!"
    )


def get_audit_help() -> str:
    return (
        "<b>Token Security Scanner</b>\n\n"
        "Scan any ERC-20 contract for vulnerabilities:\n"
        "/audit 0x6982508145454Ce325dDbE47a25d4ec3d2311933"
    )


def get_audit_vault_empty() -> str:
    return "Audit Vault\n\nEmpty. Run a scan: /audit [contract]"


def get_audit_vault_select() -> str:
    return "Audit Vault\n\nSelect a record:"


def get_audit_deleted() -> str:
    return "Record removed."


def get_audit_vault_cleared() -> str:
    return "Vault cleared."


def get_alert_help() -> str:
    return (
        "<b>Price Alert Setup</b>\n\n"
        "Format: /alert [TOKEN] [above/below] [PRICE]\n\n"
        "Examples:\n"
        "\u2022 /alert BTC above 100000\n"
        "\u2022 /alert ETH below 2000\n"
        "\u2022 /alert SOL above 250\n\n"
        "Tip: Use comma separators for large numbers, e.g., 100,000"
    )


def get_alert_direction_error() -> str:
    return (
        "Invalid Direction\n\n"
        "Direction must be above or below.\n\n"
        "Example: /alert BTC above 100000"
    )


def get_alert_price_error(msg: str) -> str:
    return f"Invalid Price\n\n{msg}\n\nExample: /alert BTC above 100000"


def get_alert_token_not_found(symbol: str) -> str:
    return (
        f"Token Not Found\n\n"
        f"Token {symbol} was not found.\n\n"
        "Try a different symbol or check for typos."
    )


def get_alert_created(symbol: str, direction: str, target_price: float) -> str:
    return (
        f"Alert Created\n\n"
        f"{symbol} \u2192 {direction} ${target_price:,.2f}\n\n"
        f"You'll receive an instant notification when the price crosses your target."
    )


def get_alerts_empty() -> str:
    return (
        "<b>Price Alerts</b>\n\n"
        "No active alerts.\n\n"
        "Create one:\n"
        "/alert BTC above 100000"
    )


def get_alerts_loading() -> str:
    return "Loading your alerts..."


def get_alerts_loaded() -> str:
    return "<b>Your Active Alerts</b>"


def get_delalert_usage() -> str:
    return "Usage: /delalert [ID]"


def get_delalert_result(deleted: bool) -> str:
    return "Alert removed." if deleted else "Alert not found."


def get_delalert_invalid() -> str:
    return "Invalid alert ID."


def get_track_help() -> str:
    return (
        "<b>Wallet Tracker</b>\n\n"
        "Format: /track [ADDRESS] [LABEL]\n\n"
        "Example:\n"
        "/track 0x28C6c06298d514Db089934071355E5743bf21d60 Binance14\n\n"
        "Tip: Label helps you identify the wallet (e.g., Whale, Exchange, DeFi)"
    )


def get_track_address_error(msg: str) -> str:
    return f"Invalid Address\n\n{msg}\n\nExample:\n0x28C6c06298d514Db089934071355E5743bf21d60"


def get_track_label_error(msg: str) -> str:
    return f"Invalid Label\n\n{msg}"


def get_track_success(label: str, address: str) -> str:
    return (
        f"Wallet Tracked\n\n"
        f"{label}\n"
        f"<code>{address}</code>\n\n"
        f"You'll receive alerts when this wallet makes transactions."
    )


def get_wallets_empty() -> str:
    return (
        "<b>Wallet Tracker</b>\n\n"
        "No tracked wallets.\n\n"
        "Track a wallet:\n"
        "/track 0x... MyLabel"
    )


def get_wallets_loading() -> str:
    return "Loading wallets..."


def get_wallets_loaded() -> str:
    return "<b>Your Tracked Wallets</b>"


def get_untrack_help() -> str:
    return (
        "<b>Untrack Wallet</b>\n\n"
        "Usage: /untrack [ADDRESS]\n\n"
        "Example:\n"
        "/untrack 0x28C6c06298d514Db089934071355E5743bf21d60"
    )


def get_untrack_success() -> str:
    return "Wallet Untracked\n\nYou will no longer receive alerts for this wallet."


def get_untrack_not_found() -> str:
    return (
        "Wallet Not Found\n\n"
        "This wallet is not in your tracking list.\n\n"
        "Use /wallets to see your tracked wallets."
    )


def get_addtoken_help() -> str:
    return (
        "<b>Portfolio Tracker</b>\n\n"
        "Format: /addtoken [TOKEN] [ENTRY_PRICE] [QTY]\n\n"
        "Examples:\n"
        "\u2022 /addtoken BTC 95000 0.5\n"
        "\u2022 /addtoken ETH 2500  (qty defaults to 1)"
    )


def get_addtoken_portfolio_full(count: int, limit: int, is_pro: bool) -> str:
    hint = "Upgrade to Pro for 20 slots." if not is_pro else "Maximum 20 positions."
    return f"Portfolio full ({count}/{limit}). {hint}"


def get_addtoken_invalid() -> str:
    return "Invalid price or quantity."


def get_addtoken_not_found(symbol: str) -> str:
    return f"Token {symbol} not found."


def get_addtoken_success(symbol: str, quantity: float, entry_price: float, current_price: float, pnl_pct: float) -> str:
    return (
        f"Position Added\n\n"
        f"{symbol} x {quantity}\n"
        f"Entry: ${entry_price:,.2f} \u2192 Now: ${current_price:,.2f}\n"
        f"P/L: {pnl_pct:+.2f}%"
    )


def get_portfolio_empty() -> str:
    return "<b>Portfolio</b>\n\nEmpty. Add positions with:\n/addtoken BTC 95000 0.5"


def get_portfolio_loading() -> str:
    return "Loading live portfolio data..."


def get_portfolio_card(tokens: list, prices: dict) -> str:
    lines = ["<b>Portfolio Overview</b>", format_divider(), ""]
    total_invested = 0
    total_current = 0
    for t in tokens:
        cp = prices.get(t.token_id, {}).get("usd", 0)
        change_24h = prices.get(t.token_id, {}).get("usd_24h_change", 0)
        invested = t.entry_price * t.quantity
        cur = cp * t.quantity
        pnl_pct = ((cp - t.entry_price) / t.entry_price * 100) if t.entry_price > 0 else 0
        pnl_usd = cur - invested
        total_invested += invested
        total_current += cur
        lines.append(f"<b>{t.token_symbol}</b> x {t.quantity}")
        lines.append(f"   ${t.entry_price:,.2f} \u2192 ${cp:,.2f} ({pnl_pct:+.1f}%) ${pnl_usd:+,.2f}")
        lines.append(f"   24h: {change_24h:+.1f}%\n")

    tp = total_current - total_invested
    tpct = ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0
    lines.append(f"{format_divider()}")
    lines.append(f"<b>Total P/L: ${tp:+,.2f} ({tpct:+.1f}%)</b>")
    lines.append(f"Invested: ${total_invested:,.2f} \u2192 Value: ${total_current:,.2f}")
    return "\n".join(lines)


def get_removetoken_usage() -> str:
    return "Usage: /removetoken BTC"


def get_removetoken_result(deleted: bool) -> str:
    return "Position removed." if deleted else "Token not in portfolio."


def get_market_loading() -> str:
    return "Scanning global market sentiment..."


def get_market_card(fng_val: int, fng_class: str, gauge_bar: str, btc_price: float, btc_change: float, eth_price: float, eth_change: float, gainers: list, losers: list, is_pro: bool) -> str:
    lines = [
        "<b>Market Intelligence</b>",
        format_divider(),
        "",
        f"Fear & Greed: {fng_val}/100 \u2014 {fng_class}",
        gauge_bar,
        "",
        f"BTC: ${btc_price:,.0f} ({btc_change:+.1f}%)",
        f"ETH: ${eth_price:,.0f} ({eth_change:+.1f}%)",
        "",
    ]
    if is_pro and gainers:
        lines.append("<b>Top Gainers (24h)</b>")
        for g in gainers[:5]:
            pct = g.get("price_change_percentage_24h", 0) or 0
            lines.append(f"  \u2022 {g['symbol'].upper()} ${g.get('current_price', 0):,.4f} ({pct:+.1f}%)")
        lines.append("")
        lines.append("<b>Top Losers (24h)</b>")
        for loser in losers[:5]:
            pct = loser.get("price_change_percentage_24h", 0) or 0
            lines.append(f"  \u2022 {loser['symbol'].upper()} ${loser.get('current_price', 0):,.4f} ({pct:+.1f}%)")
    else:
        lines.append("Top Gainers/Losers: [Pro Required]")
    return "\n".join(lines)


def get_gas_loading() -> str:
    return "Reading Ethereum mempool..."


def get_gas_unavailable() -> str:
    return "Gas data unavailable. ETH RPC may be offline."


def get_gas_card(gas: dict) -> str:
    gwei = gas["gas_gwei"]
    if gwei < 15:
        level = "Low \u2014 Excellent time to trade."
    elif gwei < 30:
        level = "Moderate \u2014 Acceptable for most transactions."
    elif gwei < 60:
        level = "High \u2014 Consider waiting for lower fees."
    else:
        level = "Very High \u2014 Delay non-urgent transactions."

    return (
        f"<b>Ethereum Gas Tracker</b>\n"
        f"{format_divider()}\n\n"
        f"Current Gas: {gwei:.1f} Gwei \u2014 {level}\n"
        f"Base Fee: {gas['base_fee_gwei']:.1f} Gwei\n\n"
        f"Priority Tiers:\n"
        f"  Low: {gas['priority_low']:.1f} Gwei\n"
        f"  Medium: {gas['priority_medium']:.1f} Gwei\n"
        f"  High: {gas['priority_high']:.1f} Gwei\n\n"
        f"Recommendation: {level}"
    )


def get_whale_radar_on(is_pro: bool) -> str:
    if is_pro:
        return (
            "Orderflow: Online\n\n"
            "Monitoring mempool for institutional trades ($1M+).\n"
            "Leave chat open for live signals."
        )
    return (
        "Orderflow: Online\n\n"
        "Receiving delayed mid-cap volume.\n"
        "Upgrade to Pro for real-time + unredacted data."
    )


def get_volume_pulse(is_pro: bool) -> str:
    if is_pro:
        return (
            "<b>Smart Money Inflow Detected</b>\n\n"
            "Pair: PEPE / WETH\n"
            "Volume (5m): +840% Spike\n"
            "Smart Money: 14 known wallets buying\n"
            "Contract: <code>0x6982508145454Ce325dDbE47a25d4ec3d2311933</code>\n\n"
            "Sudden volume from high-win-rate wallets indicates insider accumulation."
        )
    return (
        "<b>Volume Anomaly Detected</b>\n\n"
        "Pair: PEPE / WETH\n"
        "Volume: +840% Spike\n"
        "Contract: [Pro Required]\n"
        "Insight: [Pro Required]\n\n"
        "Upgrade to Pro for full analysis."
    )


def get_new_pairs_loading() -> str:
    return "Scanning Uniswap V2 Factory..."


def get_new_pairs_empty() -> str:
    return (
        "<b>New Pair Scanner</b>\n\n"
        "No new pairs detected in the last ~10 minutes.\n"
        "Check back soon \u2014 scanner runs continuously."
    )


def get_new_pairs_card(pairs: list, is_pro: bool) -> str:
    lines = ["<b>Newly Created Pairs</b>", format_divider(), ""]
    for p in pairs:
        t0 = f"{p['token0'][:6]}...{p['token0'][-4:]}"
        t1 = f"{p['token1'][:6]}...{p['token1'][-4:]}"
        if is_pro:
            lines.append(
                f"Pair: {t0} / {t1}\n"
                f"Pool: <code>{p['pair']}</code>\n"
                f"Block: {p['block']:,}\n"
                f"<a href='https://etherscan.io/tx/{p['tx_hash']}'>View Tx</a>"
            )
        else:
            lines.append(f"Pair: {t0} / {t1}\nPool: [Pro Required]\nBlock: {p['block']:,}\n")
    if not is_pro:
        lines.append("\nUpgrade to Pro for pool addresses, tx links, and live charts.")
    return "\n".join(lines)


def build_gauge(value: int) -> str:
    filled = value // 5
    empty = 20 - filled
    return f"{'█' * filled}{'░' * empty} {value}%"


def get_audit_scanning_stages(contract: str) -> list:
    return [
        "Connecting to GoPlus Security Oracle",
        f"Scanning bytecode for {contract[:8]}...",
        "Analyzing risk vectors",
    ]


def get_audit_no_data(contract: str) -> str:
    return (
        "<b>Token Security Scanner</b>\n"
        f"{format_divider()}\n\n"
        f"Contract: <code>{contract}</code>\n\n"
        "No on-chain data found. The contract may be too new, on a different chain, or invalid.\n\n"
        "Tip: Ensure this is an Ethereum (ERC-20) contract address."
    )


def get_risk_label(risk_score: int) -> str:
    if risk_score < 20:
        return "Low Risk"
    elif risk_score < 40:
        return "Moderate Risk"
    return "High Risk"


def get_audit_pro_report(token_name: str, token_symbol: str, contract: str, safety: str, risk_score: int, risks: list, is_honeypot: bool, is_open_source: bool, is_proxy: bool, buy_tax: str, sell_tax: str, holder_count: str, lp_holder_count: str) -> str:
    detail_lines = [f"  {r}" for r in risks] if risks else ["  No significant risks detected."]
    return (
        f"<b>Zenith Security Report \u2014 PRO</b>\n"
        f"{format_divider()}\n\n"
        f"Token: {token_name} ({token_symbol})\n"
        f"Contract: <code>{contract}</code>\n"
        f"Risk Level: {safety} ({risk_score}/100)\n\n"
        f"Security Analysis:\n{chr(10).join(detail_lines)}\n\n"
        f"On-Chain Metrics:\n"
        f"  Honeypot: {'Yes' if is_honeypot else 'No'}\n"
        f"  Source Verified: {'Yes' if is_open_source else 'No'}\n"
        f"  Proxy Contract: {'Yes' if is_proxy else 'No'}\n"
        f"  Buy Tax: {float(buy_tax)*100:.1f}%\n"
        f"  Sell Tax: {float(sell_tax)*100:.1f}%\n"
        f"  Holders: {holder_count}\n"
        f"  LP Holders: {lp_holder_count}"
    )


def get_audit_free_report(token_name: str, token_symbol: str, contract: str, safety: str, is_honeypot: bool) -> str:
    return (
        f"<b>Zenith Surface Scan</b>\n"
        f"{format_divider()}\n\n"
        f"Token: {token_name} ({token_symbol})\n"
        f"Contract: <code>{contract[:6]}...{contract[-4:]}</code>\n"
        f"Risk Level: {safety}\n\n"
        f"Security:\n"
        f"  Honeypot: {'Yes' if is_honeypot else 'No'}\n"
        f"  Tax Rates: [Pro Required]\n"
        f"  Holder Analysis: [Pro Required]\n"
        f"  Full Risk Breakdown: [Pro Required]\n\n"
        f"Upgrade to Pro for complete security intelligence."
    )


def get_portfolio_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Position", callback_data="ui_add_token_help")],
        [InlineKeyboardButton("Back", callback_data="ui_main_menu")],
    ])


def get_activate_help() -> str:
    return "Invalid Format. Use: /activate [YOUR_KEY]"


def get_token_not_found_msg(symbol: str) -> str:
    return (
        f"Token Not Found\n\n"
        f"Token {symbol} was not found.\n\n"
        "Try a different symbol or check for typos."
    )


def get_pro_features_section() -> str:
    return "\n\nTop Gainers/Losers: [Pro Required]"


def get_institutional_transfer(asset: str, amount: int, dest: str, insight: str, utc: str) -> str:
    return (
        f"<b>Institutional Transfer</b>\n"
        f"{format_divider()}\n\n"
        f"Asset: {amount:,} {asset}\n"
        f"Destination: {dest}\n"
        f"Insight: {insight}\n"
        f"Time: {utc}"
    )


def get_onchain_transfer(asset: str, amount: int, dest: str, utc: str) -> str:
    return (
        f"<b>On-Chain Transfer</b>\n"
        f"{format_divider()}\n\n"
        f"Asset: {amount:,} {asset}\n"
        f"Destination: {dest}\n"
        f"Insight: [Pro Required]\n"
        f"Time: Delayed"
    )


def get_subscription_expiring(user_id: int, days_left: int) -> str:
    return (
        f"<b>Subscription Expiring Soon</b>\n"
        f"{format_divider()}\n\n"
        f"Your Zenith Pro expires in {days_left} day{'s' if days_left != 1 else ''}.\n\n"
        f"To renew, contact the admin and provide your ID:\n"
        f"<code>{user_id}</code>\n\n"
        f"After payment, your subscription will be extended instantly."
    )


def get_subscription_expired(user_id: int) -> str:
    return (
        f"<b>Pro Subscription Ended</b>\n"
        f"{format_divider()}\n\n"
        f"Your Zenith Pro access has expired.\n"
        f"Pro features (wallet tracker, full security scans, extended alerts) are now locked.\n\n"
        f"To renew: Contact the admin with your ID:\n"
        f"<code>{user_id}</code>\n\n"
        f"Your data (alerts, portfolio, wallets) is preserved and will be available again once you renew."
    )


# ── AI Co-Pilot ────────────────────────────────────────────

def get_ai_no_key_msg():
    text = (
        "<b>Crypto AI Co-Pilot</b>\n"
        f"{format_divider()}\n\n"
        "You need a Groq API key to use the AI assistant.\n\n"
        "1. Go to <b>console.groq.com</b> \u2192 API Keys\n"
        "2. Create a free key (free credits included)\n"
        "3. Send it here:\n"
        "<code>/setkey gsk_your_api_key</code>\n\n"
        "Takes 2 minutes!"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("How to get a key", url="https://console.groq.com")],
    ])
    return text, kb


def get_ai_key_set_success_msg():
    text = (
        "<b>Crypto AI Co-Pilot</b>\n"
        f"{format_divider()}\n\n"
        "Your Groq key is connected. You're live! \U0001f680\n\n"
        "Try asking:\n"
        "\u2022 <code>/ai what's in my portfolio?</code>\n"
        "\u2022 <code>/ai analyze the market today</code>\n"
        "\u2022 <code>/ai is BTC a good buy right now?</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Try: My Portfolio", callback_data="ai_followup_what is in my portfolio?")],
        [InlineKeyboardButton("Try: Market Today", callback_data="ai_followup_analyze the crypto market today")],
    ])
    return text, kb


def get_ai_key_status_msg(has_key: bool):
    if has_key:
        return (
            "<b>Groq API Key</b>\n"
            f"{format_divider()}\n\n"
            "Your key is set and active.\n\n"
            "To remove it: /delkey"
        ), InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="ui_main_menu")]])
    return (
        "<b>Groq API Key</b>\n"
        f"{format_divider()}\n\n"
        "No key set.\n\n"
        "Set one: /setkey gsk_your_key"
    ), InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="ui_main_menu")]])


def get_ai_key_deleted_msg():
    text = (
        "<b>Groq API Key</b>\n"
        f"{format_divider()}\n\n"
        "Your key has been removed."
    )
    return text, InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="ui_main_menu")]])


def get_ai_empty_query_msg():
    text = (
        "<b>Crypto AI Co-Pilot</b>\n"
        f"{format_divider()}\n\n"
        "Ask me anything about crypto! Try one of these:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("My Portfolio", callback_data="ai_followup_what is in my portfolio?")],
        [InlineKeyboardButton("Market Overview", callback_data="ai_followup_give me the crypto market overview today")],
        [InlineKeyboardButton("Gas Fees", callback_data="ai_followup_what are current gas fees?")],
        [InlineKeyboardButton("Analyze BTC", callback_data="ai_followup_analyze bitcoin price action")],
        [InlineKeyboardButton("Alert Strategy", callback_data="ai_followup_what price alerts should I set?")],
    ])
    return text, kb


def get_ai_response_msg(response: str, query: str) -> tuple:
    text = (
        f"<b>Crypto AI</b>\n"
        f"{format_divider()}\n\n"
        f"{response}"
    )

    lower = query.lower()
    if any(w in lower for w in ["portfolio", "position", "pnl", "p/l", "bag"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Compare vs BTC", callback_data="ai_followup_compare my portfolio vs bitcoin performance")],
            [InlineKeyboardButton("Top Gainer", callback_data="ai_followup_what is my top performing token?")],
            [InlineKeyboardButton("Market Today", callback_data="ai_followup_give me the crypto market overview today")],
        ])
    elif any(w in lower for w in ["market", "btc", "bitcoin", "eth", "price"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Top Movers", callback_data="ai_followup_what are the top gainers and losers today?")],
            [InlineKeyboardButton("Gas Fees", callback_data="ai_followup_what are current gas fees?")],
            [InlineKeyboardButton("My Portfolio", callback_data="ai_followup_what is in my portfolio?")],
        ])
    elif any(w in lower for w in ["alert", "alert"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("View Alerts", callback_data="ui_price_alerts")],
            [InlineKeyboardButton("Alert Strategy", callback_data="ai_followup_what price alerts should I set for my portfolio?")],
        ])
    elif any(w in lower for w in ["wallet", "whale", "track"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("View Wallets", callback_data="ui_wallet_tracker")],
            [InlineKeyboardButton("Recent Txs", callback_data="ai_followup_analyze recent whale transactions")],
        ])
    elif any(w in lower for w in ["gas", "fee", "gwei"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Live Gas", callback_data="ui_gas")],
            [InlineKeyboardButton("Optimization", callback_data="ai_followup_how can I optimize gas fees for my trades?")],
        ])
    elif any(w in lower for w in ["audit", "token", "contract", "scam"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Run Audit", callback_data="ui_audit")],
            [InlineKeyboardButton("Risk Guide", callback_data="ai_followup_how to avoid crypto scams and rug pulls?")],
        ])
    elif any(w in lower for w in ["sub", "pro", "key", "activate"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Pro Features", callback_data="ui_pro_info")],
            [InlineKeyboardButton("Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
        ])
    elif any(w in lower for w in ["news", "prediction", "outlook", "analysis"]):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Market Outlook", callback_data="ai_followup_give me a crypto market outlook")],
            [InlineKeyboardButton("Technical Analysis", callback_data="ai_followup_technical analysis of bitcoin")],
            [InlineKeyboardButton("My Portfolio", callback_data="ai_followup_what is in my portfolio?")],
        ])
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("My Portfolio", callback_data="ai_followup_what is in my portfolio?")],
            [InlineKeyboardButton("Market Today", callback_data="ai_followup_give me the crypto market overview today")],
            [InlineKeyboardButton("My Alerts", callback_data="ui_price_alerts")],
            [InlineKeyboardButton("Gas Fees", callback_data="ai_followup_what are current gas fees?")],
        ])
    return text, kb


def get_ai_rate_limited_msg():
    text = (
        "<b>Crypto AI</b>\n"
        f"{format_divider()}\n\n"
        "Your Groq key reached its rate limit.\n\n"
        "Wait a bit or replace your key:\n"
        "<code>/setkey gsk_new_key</code>"
    )
    return text, InlineKeyboardMarkup([
        [InlineKeyboardButton("Replace Key", callback_data="ai_followup_how do i set a new groq key?")],
    ])


def get_ai_invalid_key_msg():
    text = (
        "<b>Crypto AI</b>\n"
        f"{format_divider()}\n\n"
        "Your Groq key doesn't seem to work anymore.\n\n"
        "Check it at console.groq.com and update:\n"
        "<code>/setkey gsk_new_key</code>"
    )
    return text, InlineKeyboardMarkup([
        [InlineKeyboardButton("Set New Key", callback_data="ai_followup_how do i set a new groq key?")],
    ])


def get_ai_server_error_msg():
    text = (
        "<b>Crypto AI</b>\n"
        f"{format_divider()}\n\n"
        "Couldn't reach the AI right now.\n\n"
        "Try again in a moment with /ai"
    )
    return text, InlineKeyboardMarkup([
        [InlineKeyboardButton("Try Again", callback_data="ai_followup_what is in my portfolio?")],
    ])


def get_price_alert_triggered(token_symbol: str, direction: str, target_price: float, current_price: float) -> str:
    return (
        f"<b>Price Alert Triggered</b>\n"
        f"{format_divider()}\n\n"
        f"{token_symbol} hit your {direction} target!\n\n"
        f"Target: ${target_price:,.2f}\n"
        f"Current: ${current_price:,.2f}\n\n"
        f"Set another alert with /alert"
    )


def get_wallet_activity(wallet_label: str, direction: str, amount: float, tx_hash: str) -> str:
    return (
        f"<b>Wallet Activity</b>\n"
        f"{format_divider()}\n\n"
        f"Wallet: {wallet_label}\n"
        f"Action: {direction}\n"
        f"Amount: {amount:.4f} ETH\n"
        f"Tx: <a href='https://etherscan.io/tx/{tx_hash}'>{tx_hash[:10]}...</a>"
    )
