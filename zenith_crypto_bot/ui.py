from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_dashboard(is_pro: bool = False):
    """Professional institutional-grade trading terminal dashboard."""
    pro_badge = "🟢" if is_pro else "🔴"
    tier = "PRO" if is_pro else "STANDARD"
    
    keyboard = [
        [InlineKeyboardButton("📊 Market Intelligence", callback_data="ui_market"),
         InlineKeyboardButton("⛽ Gas Tracker", callback_data="ui_gas")],
        [InlineKeyboardButton("🔍 Token Security Scan", callback_data="ui_audit"),
         InlineKeyboardButton("🗂️ Audit Vault", callback_data="ui_saved_audits")],
        [InlineKeyboardButton("💰 Portfolio & P/L", callback_data="ui_portfolio"),
         InlineKeyboardButton("🔔 Price Alerts", callback_data="ui_price_alerts")],
        [InlineKeyboardButton("👁️ Wallet Tracker", callback_data="ui_wallet_tracker"),
         InlineKeyboardButton("📈 Smart Money Pulse", callback_data="ui_volume")],
        [InlineKeyboardButton("🆕 New Pair Scanner", callback_data="ui_new_pairs"),
         InlineKeyboardButton("📡 Live Orderflow", callback_data="ui_whale_radar")],
        [InlineKeyboardButton(f"{pro_badge} {tier} ACCESS", callback_data="ui_pro_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_audits_keyboard(audits):
    """Interactive audit history with individual actions."""
    keyboard = []
    for a in audits:
        short_contract = f"{a.contract[:6]}...{a.contract[-4:]}"
        keyboard.append([
            InlineKeyboardButton(f"📜 {short_contract}", callback_data=f"ui_view_audit_{a.id}"),
            InlineKeyboardButton("🗑️", callback_data=f"ui_del_audit_{a.id}")
        ])
    if audits:
        keyboard.append([InlineKeyboardButton("🚨 Wipe Entire Vault", callback_data="ui_clear_audits")])
    keyboard.append([InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_alerts_keyboard(alerts):
    """Interactive price alert list."""
    keyboard = []
    for a in alerts:
        direction_icon = "📈" if a.direction == "above" else "📉"
        keyboard.append([
            InlineKeyboardButton(
                f"{direction_icon} {a.token_symbol} {a.direction} ${a.target_price:,.2f}",
                callback_data=f"ui_noop_{a.id}"
            ),
            InlineKeyboardButton("🗑️", callback_data=f"ui_del_alert_{a.id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_wallets_keyboard(wallets):
    """Interactive tracked wallets list."""
    keyboard = []
    for w in wallets:
        short_addr = f"{w.wallet_address[:6]}...{w.wallet_address[-4:]}"
        keyboard.append([
            InlineKeyboardButton(
                f"👁️ {w.label}: {short_addr}",
                callback_data=f"ui_noop_{w.id}"
            ),
            InlineKeyboardButton("🗑️", callback_data=f"ui_untrack_{w.id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")]])

def get_welcome_msg(name: str, is_pro: bool = False, days_left: int = 0):
    pro_badge = "🟢" if is_pro else "🔴"
    tier_name = "PRO" if is_pro else "STANDARD"
    
    if is_pro:
        tier_detail = (
            f"<b>⚡ {pro_badge} PRO ACCESS — {days_left} days remaining</b>\n"
            "Full access to institutional-grade intelligence: real-time alerts, "
            "wallet tracking, deep security scans, and zero-latency market data."
        )
    else:
        tier_detail = (
            f"<b>📊 {pro_badge} STANDARD ACCESS (Free)</b>\n"
            "Limited access to delayed data and surface-level scans.\n"
            "Use <code>/activate [KEY]</code> to unlock Pro."
        )

    return (
        f"<b>ZENITH OPEN SOURCE PROJECTS v2.0 — {tier_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Welcome, <b>{name}</b>.\n\n"
        f"{tier_detail}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Available Modules</b>\n"
        "• <b>Market Intel</b> — Fear & Greed, Top Movers, BTC Dominance\n"
        "• <b>Token Scanner</b> — Real smart contract security audits\n"
        "• <b>Portfolio P/L</b> — Track your positions with live pricing\n"
        "• <b>Price Alerts</b> — Automated threshold notifications\n"
        "• <b>Wallet Tracker</b> — Copy-trade whale movements\n"
        "• <b>New Pairs</b> — Fresh liquidity pool detection\n"
        "• <b>Gas Optimizer</b> — Time your trades for lowest fees\n\n"
        "<i>Select a module below to begin.</i>"
    )