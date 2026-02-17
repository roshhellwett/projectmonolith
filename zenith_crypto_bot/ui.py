from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_dashboard(is_pro: bool = False):
    """The clean, institutional dashboard for all users."""
    status_text = "🟢 Zenith Pro: Active" if is_pro else "🔒 Upgrade to Zenith Pro"
    radar_text = "⚡ Live On-Chain Radar (Pro)" if is_pro else "📊 Live On-Chain Radar (Standard)"
    
    keyboard = [
        [InlineKeyboardButton(radar_text, callback_data="ui_whale_radar")],
        [InlineKeyboardButton("🔍 Smart Contract Audit", callback_data="ui_audit")],
        [InlineKeyboardButton("📈 DEX Volume Pulse", callback_data="ui_volume")],
        [InlineKeyboardButton(status_text, callback_data="ui_pro_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return to Main Menu", callback_data="ui_main_menu")]])

def get_welcome_msg(name: str):
    return (
        f"<b>Welcome to Zenith, {name}.</b>\n\n"
        "Zenith is an advanced on-chain analytics terminal. We monitor network mempools, track institutional capital routing, and audit smart contracts in real time to provide actionable market asymmetry.\n\n"
        "<b>📊 STANDARD TIER (Current)</b>\n"
        "• <b>Network Alerts:</b> Delayed tracking of mid-cap transfers ($50k+).\n"
        "• <b>Data Masking:</b> Transaction routing is visible, but exact wallet addresses and hashes are redacted.\n"
        "• <b>Basic Audits:</b> Surface-level contract vulnerability checks.\n\n"
        "<b>⚡ PRO TIER (Requires Activation)</b>\n"
        "• <b>Institutional Alerts:</b> Zero-latency push notifications for major capital movements ($1M+).\n"
        "• <b>Full Transparency:</b> Unredacted wallet addresses and direct block explorer links.\n"
        "• <b>Execution Integration:</b> One-click routing to decentralized exchanges (DEX) for instant trade execution.\n"
        "• <b>Deep-Scan Audits:</b> Comprehensive bytecode decompilation, tax analysis, and honeypot detection.\n\n"
        "<i>Select a module below to initialize your terminal.</i>"
    )