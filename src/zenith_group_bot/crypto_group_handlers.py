import contextlib
import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.animation import send_loading_message
from core.logger import setup_logger
from core.subscription import SubscriptionRepo, get_fear_greed_index, get_prices, resolve_token_id
from zenith_group_bot.flood_control import add_warning, check_bot_command_limit, get_flood_action
from zenith_group_bot.repository import SettingsRepo
from zenith_group_bot.ui import (
    get_alert_pro_msg,
    get_alert_redirect,
    get_flood_cooldown,
    get_flood_mute,
    get_flood_warning,
    get_gas_redirect,
    get_market_overview,
    get_price_card,
    get_token_not_found,
)

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
                await update.message.reply_text(get_flood_cooldown(update.effective_user.first_name, remaining))
        else:
            warning_count = add_warning(user_id)
            action, duration = get_flood_action(warning_count, is_pro)

            if action == "warn":
                with contextlib.suppress(Exception):
                    await update.message.reply_text(get_flood_warning(update.effective_user.first_name))
            elif action == "mute":
                try:
                    await context.bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + duration)
                    await update.message.reply_text(get_flood_mute(update.effective_user.first_name, duration))
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
        await update.message.reply_text(get_token_not_found(symbol), parse_mode="HTML")
        return

    data = prices[token_id]
    price = data.get("usd", 0)
    change = data.get("usd_24h_change", 0)

    msg = get_price_card(data.get("name", symbol), symbol, price, change, is_pro, data)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_group_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    user_id = update.effective_user.id
    is_pro = await SubscriptionRepo.is_pro(user_id)

    if not is_pro:
        await update.message.reply_text(get_alert_pro_msg(), parse_mode="HTML")
        return

    await update.message.reply_text(get_alert_redirect(), parse_mode="HTML")


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

    loading = await send_loading_message(update, context, "Loading market data...")

    fng = await get_fear_greed_index()
    prices = await get_prices(["bitcoin", "ethereum"])

    btc = prices.get("bitcoin", {})
    eth = prices.get("ethereum", {})

    msg = get_market_overview(btc, eth, fng, is_pro)

    if loading:
        await loading.edit_text(msg, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_group_gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.chat.type not in ["group", "supergroup"]:
        return

    await update.message.reply_text(get_gas_redirect(), parse_mode="HTML")


def register_group_crypto_handlers(app):
    app.add_handler(CommandHandler("price", cmd_group_price))
    app.add_handler(CommandHandler("alert", cmd_group_alert))
    app.add_handler(CommandHandler("market", cmd_group_market))
    app.add_handler(CommandHandler("gas", cmd_group_gas))
    logger.info("Registered group crypto handlers")
