from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_dashboard():
    """The high-tech dashboard for all users."""
    keyboard = [
        [InlineKeyboardButton("🐋 Live Whale Radar", callback_data="ui_whale_radar")],
        [InlineKeyboardButton("🛡️ Token Audit", callback_data="ui_audit"),
         InlineKeyboardButton("📈 Volume Pulse", callback_data="ui_volume")],
        [InlineKeyboardButton("💎 Unlock Pro Access", callback_data="ui_pro_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_welcome_msg(name: str):
    return (
        f"🚀 <b>Welcome to Zenith Whale, {name}!</b>\n\n"
        "I am your 24/7 blockchain intelligence terminal. I track the top 1% of wallets to give you the ultimate market edge.\n\n"
        "<b>🟢 FREE SERVICES:</b>\n"
        "• <b>Dolphin Alerts:</b> Transfers $50k - $250k.\n"
        "• <b>Blurred Tracking:</b> You see the move, but wallet IDs are hidden.\n"
        "• <b>Standard Audit:</b> 3 scans per day.\n\n"
        "<b>💎 PRO SERVICES (Activation Required):</b>\n"
        "• <b>Whale Alerts:</b> Instant notifications for $1M+ moves.\n"
        "• <b>Unmasked Wallets:</b> Direct links to Solscan/Etherscan.\n"
        "• <b>Smart Identity:</b> We label wallets (e.g., 'Binance Cold Wallet').\n"
        "• <b>Unlimited Audits:</b> Scan any contract, anytime."
    )