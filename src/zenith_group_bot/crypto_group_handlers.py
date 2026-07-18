import contextlib
import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.logger import setup_logger
from core.subscription import SubscriptionRepo, get_fear_greed_index, get_prices, resolve_token_id
from zenith_group_bot.flood_control import add_warning, check_bot_command_limit, get_flood_action
from zenith_group_bot.repository import SettingsRepo

logger = setup_logger("GROUP_CRYPTO")

bot_app = None


def set_group_crypto_bot(app):
    global bot_app
    bot_app = app


async def cmd_group_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = update.message.chat.id
    user_id = update.effective_user.id

    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active:
        return

    is_pro = await SubscriptionRepo.is_pro(user_id)
    is_flooding, msg, remaining = check_bot_command_limit(user_id, is_pro)

    if is_flooding:
        if remaining > 0:
            with contextlib.suppress(Exception):
                await update.message.reply_text(
                    f"⏳ {update.effective_user.first_name}, please wait {remaining}s between commands.",
                    parse_mode="HTML",
                )
        else:
            warning_count = add_warning(user_id)
            action, duration = get_flood_action(warning_count, is_pro)

            if action == "warn":
                with contextlib.suppress(Exception):
                    await update.message.reply_text(
                        f"⚠️ {update.effective_user.first_name}, you're sending too many commands!", parse_mode="HTML"
                    )
            elif action == "mute":
                try:
                    await context.bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + duration)
                    await update.message.reply_text(
                        f"🔇 {update.effective_user.first_name} muted for {duration//3600}h due to spam.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to mute: {e}")
            elif action == "kick":
                try:
                    await context.bot.ban_chat_member(chat_id, user_id)
                    await context.bot.unban_chat_member(chat_id, user_id)
                except Exception as e:
                    logger.error(f"Failed to kick: {e}")
        return

    symbol = context.args[0].upper() if context.args else "BTC"

    token_id = resolve_token_id(symbol)
    prices = await get_prices([token_id])

    if token_id not in prices:
        await update.message.reply_text(f"⚠️ Token <code>{symbol}</code> not found.", parse_mode="HTML")
        return

    data = prices[token_id]
    price = data.get("usd", 0)
    change = data.get("usd_24h_change", 0)

    icon = "🟢" if change >= 0 else "🔴"

    msg = (
        f"💰 <b>{data.get('name', symbol)} ({symbol})</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Price:</b> ${price:,.2f}\n"
        f"{icon} <b>24h:</b> {change:+.2f}%\n"
    )

    if is_pro:
        msg += f"<b>Market Cap:</b> ${data.get('market_cap', 'N/A'):,.}\n"
        msg += f"<b>Volume 24h:</b> ${data.get('total_volume', 'N/A'):,.}\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_group_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        await update.message.reply_text(
            "🔔 <b>Price Alerts (Pro Only)</b>\n\n"
            "Create price alerts to get notified when tokens hit your target price.\n\n"
            "💎 <b>Pro Benefits (₹149/month):</b>\n"
            "• Unlimited price alerts\n"
            "• Wallet tracking\n"
            "• Portfolio manager\n\n"
            "Contact @admin to upgrade!",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        "🔔 <b>Price Alerts</b>\n\n"
        "Use /alert in private chat with @ZenithCryptoBot to create alerts.\n\n"
        "Example: <code>/alert BTC above 100000</code>",
        parse_mode="HTML",
    )


async def cmd_group_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = update.message.chat.id
    user_id = update.effective_user.id

    settings = await SettingsRepo.get_settings(chat_id)
    if not settings or not settings.is_active:
        return

    is_pro = await SubscriptionRepo.is_pro(user_id)
    is_flooding, msg, remaining = check_bot_command_limit(user_id, is_pro)

    if is_flooding:
        return

    msg = await update.message.reply_text("<i>Loading market data...</i>", parse_mode="HTML")

    fng = await get_fear_greed_index()
    prices = await get_prices(["bitcoin", "ethereum"])

    fng_val = fng.get("value", 0) if fng else 0
    fng_class = fng.get("classification", "N/A") if fng else "N/A"

    btc = prices.get("bitcoin", {})
    eth = prices.get("ethereum", {})

    lines = [
        "📊 <b>MARKET OVERVIEW</b>\n" "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        f"<b>BTC:</b> ${btc.get('usd', 0):,.0f} ({btc.get('usd_24h_change', 0):+.1f}%)",
        f"<b>ETH:</b> ${eth.get('usd', 0):,.0f} ({eth.get('usd_24h_change', 0):+.1f}%)",
    ]

    if is_pro and fng:
        lines.append(f"\n<b>Fear & Greed:</b> {fng_val}/100 - {fng_class}")
    elif fng:
        lines.append("\n<b>Fear & Greed:</b> <i>[Pro Required]</i>")

    await msg.edit_text("\n".join(lines), parse_mode="HTML")


async def cmd_group_gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    await update.message.reply_text(
        "⛽ <b>Gas Tracker</b>\n\n" "Use /gas in private chat with @ZenithCryptoBot for gas prices.", parse_mode="HTML"
    )


def register_group_crypto_handlers(app):
    app.add_handler(CommandHandler("price", cmd_group_price))
    app.add_handler(CommandHandler("alert", cmd_group_alert))
    app.add_handler(CommandHandler("market", cmd_group_market))
    app.add_handler(CommandHandler("gas", cmd_group_gas))
    logger.info("Registered group crypto handlers")
