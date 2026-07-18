from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID
from core.formatters import format_address, format_progress_bar


def get_main_dashboard(
    is_pro: bool = False, alert_count: int = 0, alert_limit: int = 1, wallet_count: int = 0, wallet_limit: int = 0
):
    pro_badge = "🟢" if is_pro else "🔴"
    tier = "PRO" if is_pro else "STANDARD"

    alert_indicator = f" ({alert_count}/{alert_limit})" if alert_limit > 0 else ""
    wallet_indicator = f" ({wallet_count}/{wallet_limit})" if wallet_limit > 0 else ""

    keyboard = [
        [
            InlineKeyboardButton("📊 Market Intelligence", callback_data="ui_market"),
            InlineKeyboardButton("⛽ Gas Tracker", callback_data="ui_gas"),
        ],
        [
            InlineKeyboardButton("🔍 Token Security Scan", callback_data="ui_audit"),
            InlineKeyboardButton("🗂️ Audit Vault", callback_data="ui_saved_audits"),
        ],
        [
            InlineKeyboardButton("💰 Portfolio & P/L", callback_data="ui_portfolio"),
            InlineKeyboardButton(f"🔔 Price Alerts{alert_indicator}", callback_data="ui_price_alerts"),
        ],
        [
            InlineKeyboardButton(f"👁️ Wallet Tracker{wallet_indicator}", callback_data="ui_wallet_tracker"),
            InlineKeyboardButton("📈 Smart Money Pulse", callback_data="ui_volume"),
        ],
        [
            InlineKeyboardButton("🆕 New Pair Scanner", callback_data="ui_new_pairs"),
            InlineKeyboardButton("📡 Live Orderflow", callback_data="ui_whale_radar"),
        ],
        [
            InlineKeyboardButton(f"{pro_badge} {tier} ACCESS", callback_data="ui_pro_info"),
            InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_audits_keyboard(audits):
    keyboard = []
    for a in audits:
        short_contract = format_address(a.contract, 6, 4)
        keyboard.append(
            [
                InlineKeyboardButton(f"📜 {short_contract}", callback_data=f"ui_view_audit_{a.id}"),
                InlineKeyboardButton("🗑️", callback_data=f"ui_del_audit_{a.id}"),
            ]
        )
    if audits:
        keyboard.append([InlineKeyboardButton("🚨 Wipe Entire Vault", callback_data="ui_clear_audits")])
    keyboard.append([InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_alerts_keyboard(alerts, is_pro: bool = False):
    keyboard = []

    for a in alerts:
        direction_icon = "📈" if a.direction == "above" else "📉"
        triggered = "✅" if a.is_triggered else ""
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{direction_icon} {a.token_symbol} {a.direction} ${a.target_price:,.2f} {triggered}",
                    callback_data=f"ui_alert_{a.id}",
                ),
                InlineKeyboardButton("🗑️", callback_data=f"ui_del_alert_confirm_{a.id}"),
            ]
        )
    keyboard.append([InlineKeyboardButton("➕ Add Alert", callback_data="ui_add_alert_help")])
    keyboard.append([InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_delete_alert(alert) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes, Delete", callback_data=f"ui_del_alert_{alert.id}"),
                InlineKeyboardButton("✖ Cancel", callback_data="ui_price_alerts"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="ui_price_alerts")],
        ]
    )


def get_confirm_delete_alert_msg(alert) -> str:
    direction_icon = "📈" if alert.direction == "above" else "📉"
    return (
        f"⚠️ <b>Confirm Delete Alert?</b>\n\n"
        f"{direction_icon} <b>{alert.token_symbol}</b> {alert.direction} <b>${alert.target_price:,.2f}</b>\n\n"
        f"<i>This action cannot be undone.</i>"
    )


def get_wallets_keyboard(wallets, is_pro: bool = False):
    keyboard = []
    limit = 5 if is_pro else 0

    for w in wallets:
        short_addr = format_address(w.wallet_address, 6, 4)
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"👁️ {w.label}: {short_addr}",
                    callback_data=f"ui_wallet_{w.id}",
                ),
                InlineKeyboardButton("🗑️", callback_data=f"ui_untrack_confirm_{w.id}"),
            ]
        )

    if limit > 0:
        keyboard.append(
            [InlineKeyboardButton(f"➕ Track Wallet ({len(wallets)}/{limit})", callback_data="ui_track_help")]
        )
    else:
        keyboard.append([InlineKeyboardButton("➕ Track Wallet", callback_data="ui_track_help")])

    keyboard.append([InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_untrack_wallet(wallet) -> InlineKeyboardMarkup:
    format_address(wallet.wallet_address, 6, 4)
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes, Untrack", callback_data=f"ui_untrack_{wallet.id}"),
                InlineKeyboardButton("✖ Cancel", callback_data="ui_wallet_tracker"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="ui_wallet_tracker")],
        ]
    )


def get_confirm_untrack_msg(wallet) -> str:
    short_addr = format_address(wallet.wallet_address, 8, 6)
    return (
        f"⚠️ <b>Confirm Untrack Wallet?</b>\n\n"
        f"👁️ <b>{wallet.label}</b>\n"
        f"<code>{short_addr}</code>\n\n"
        f"<i>You will stop receiving transaction alerts for this wallet.</i>"
    )


def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")]])


def get_limit_reached_card(feature: str, current: int, limit: int, is_pro: bool = False) -> tuple:
    """Returns (message, keyboard) for limit reached scenario."""
    if is_pro:
        message = (
            f"🚫 <b>Limit Reached: {feature}</b>\n\n"
            f"You've reached your maximum of {limit} {feature.lower()}.\n"
            f"Remove some to add more."
        )
    else:
        message = (
            f"🚫 <b>Limit Reached: {feature}</b>\n\n"
            f"<b>Current:</b> {current}/{limit}\n"
            f"<b>Upgrade to PRO:</b> {limit * 5}x more\n\n"
            f"💎 PRO benefits:\n"
            f"• 25 price alerts (vs 1)\n"
            f"• 5 tracked wallets (vs 0)\n"
            f"• Full security scans"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
            [InlineKeyboardButton("🔙 Back", callback_data="ui_main_menu")],
        ]
    )

    return message, keyboard


def get_already_tracked_msg(wallet_label: str = None) -> str:
    if wallet_label:
        return (
            f"ℹ️ <b>Already Tracked</b>\n\n"
            f"This wallet is already being tracked as <b>{wallet_label}</b>.\n\n"
            f"Use <code>/untrack [ADDRESS]</code> to remove it first."
        )
    return (
        "ℹ️ <b>Already Tracked</b>\n\n"
        "This wallet is already in your tracking list.\n\n"
        "Use <code>/wallets</code> to view your tracked wallets."
    )


def get_pro_feature_msg(feature: str) -> tuple:
    """Returns (message, keyboard) for locked pro feature."""
    message = (
        f"🔒 <b>Pro Feature: {feature}</b>\n\n"
        f"This feature is available exclusively for PRO members.\n\n"
        f"💎 <b>Pro Benefits (₹149/month):</b>\n"
        f"• Unlimited price alerts\n"
        f"• 5 whale wallet tracking\n"
        f"• Full GoPlus security scans\n"
        f"• Real-time smart money alerts\n"
        f"• Unlimited portfolio positions\n"
        f"• New pair scanner\n"
        f"• Fear & Greed Index"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
            [InlineKeyboardButton("🔑 Activate Key", callback_data="ui_activate_help")],
            [InlineKeyboardButton("🔙 Back", callback_data="ui_main_menu")],
        ]
    )

    return message, keyboard


def get_loading_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Processing...", callback_data="ui_loading")]])


def get_retry_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Retry", callback_data=callback_data)],
            [InlineKeyboardButton("❓ Help", callback_data="ui_help")],
        ]
    )


def get_welcome_msg(name: str, is_pro: bool = False, days_left: int = 0, usage: dict = None):
    pro_badge = "🟢" if is_pro else "🔴"
    tier_name = "PRO" if is_pro else "STANDARD"

    if usage:
        alert_bar = format_progress_bar(usage.get("alerts", 0), usage.get("alert_limit", 1))
        wallet_bar = format_progress_bar(usage.get("wallets", 0), usage.get("wallet_limit", 5)) if is_pro else "🔒"
    else:
        alert_bar = "N/A"
        wallet_bar = "N/A" if not is_pro else "0/5"

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
        "<b>📊 Your Usage</b>\n"
        f"• Alerts: {alert_bar}\n"
        f"• Wallets: {wallet_bar}\n\n"
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


def get_portfolio_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add Position", callback_data="ui_add_token_help")],
            [InlineKeyboardButton("🔙 Return to Terminal", callback_data="ui_main_menu")],
        ]
    )


def get_audit_result_msg(audit_data: dict, is_pro: bool = False) -> str:
    """Format audit result message with safety indicators."""
    score = audit_data.get("security_score", 0)

    if score >= 80:
        status = "LOW RISK"
    elif score >= 50:
        status = "MEDIUM RISK"
    else:
        status = "HIGH RISK"

    message = f"""
<b>🔍 Token Security Scan Results</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>Token:</b> {audit_data.get('symbol', 'N/A')}
<b>Risk Score:</b> {score}/100 ({status})

<b>Security Checks:</b>
• Honeypot: {audit_data.get('is_honeypot', 'Unknown')}
• Mint Disabled: {audit_data.get('mint_disabled', 'Unknown')}
• LP Locked: {audit_data.get('lp_locked', 'Unknown')}
• Owner Renounced: {audit_data.get('owner_renounced', 'Unknown')}
"""

    if is_pro:
        message += f"""
<b>Additional Data:</b>
• Buy Tax: {audit_data.get('buy_tax', 'N/A')}%
• Sell Tax: {audit_data.get('sell_tax', 'N/A')}%
• Holder Count: {audit_data.get('holder_count', 'N/A')}
• Top 10 Holders: {audit_data.get('top10_holders_pct', 'N/A')}%
"""

    message += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "<i>Use /saveaudit to save this result.</i>"

    return message


def get_market_card(data: dict, is_pro: bool = False) -> str:
    """Format market intelligence card."""
    fear_greed = data.get("fear_greed_index", 0)

    if fear_greed <= 25:
        fg_emoji = "😱"
        fg_status = "Extreme Fear"
    elif fear_greed <= 45:
        fg_emoji = "😰"
        fg_status = "Fear"
    elif fear_greed <= 55:
        fg_emoji = "😐"
        fg_status = "Neutral"
    elif fear_greed <= 75:
        fg_emoji = "😊"
        fg_status = "Greed"
    else:
        fg_emoji = "🤑"
        fg_status = "Extreme Greed"

    message = f"""
<b>📊 Market Intelligence</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>🧠 Fear & Greed Index:</b>
{fg_emoji} {fear_greed}/100 ({fg_status})
"""

    if is_pro:
        message += f"""
<b>📈 Top Gainers (24h):</b>
{format_progress_bar(1, 1)}

<b>📉 Top Losers (24h):</b>
{format_progress_bar(1, 1)}

<b>₿ BTC Dominance:</b> {data.get('btc_dominance', 'N/A')}%
"""
    else:
        message += "\n<i>💎 Upgrade to PRO for top movers and more.</i>"

    return message
