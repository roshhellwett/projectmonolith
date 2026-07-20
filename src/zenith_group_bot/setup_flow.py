import contextlib

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.logger import setup_logger
from core.subscription import SubscriptionRepo
from zenith_group_bot.repository import SettingsRepo
from zenith_group_bot.ui import (
    get_setup_complete_msg,
    get_setup_dm_failed,
    get_setup_dm_sent,
    get_setup_expired,
    get_setup_failed,
    get_setup_group_error,
    get_setup_limit_reached,
    get_setup_not_admin,
    get_setup_start_msg,
    get_setup_step2_msg,
    get_setup_verify_error,
)

logger = setup_logger("SETUP_FLOW")

setup_state = {}

FEATURES_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Anti-Spam Only", callback_data="setup_feat_spam")],
        [InlineKeyboardButton("Anti-Abuse Only", callback_data="setup_feat_abuse")],
        [InlineKeyboardButton("Both (Recommended)", callback_data="setup_feat_both")],
    ]
)

STRENGTH_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Low (5 strikes)", callback_data="setup_str_low")],
        [InlineKeyboardButton("Medium (3 strikes)", callback_data="setup_str_medium")],
        [InlineKeyboardButton("High (2 strikes)", callback_data="setup_str_high")],
    ]
)


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply_text(get_setup_group_error())

    chat_id = msg.chat_id
    user_id = msg.from_user.id

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ("administrator", "creator"):
            return await msg.reply_text(get_setup_not_admin())
    except Exception:
        return await msg.reply_text(get_setup_verify_error())

    is_pro = await SubscriptionRepo.is_pro(user_id)
    existing_groups = await SettingsRepo.count_owned_groups(user_id)

    existing_settings = await SettingsRepo.get_settings(chat_id)
    is_new_group = existing_settings is None or existing_settings.owner_id != user_id

    if is_new_group:
        max_groups = 5 if is_pro else 1
        if existing_groups >= max_groups:
            msg_text = get_setup_limit_reached(existing_groups, max_groups, is_pro)
            return await msg.reply_text(msg_text, parse_mode="HTML")

    group_name = msg.chat.title or f"Group {chat_id}"

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_setup_start_msg(group_name),
            reply_markup=FEATURES_KEYBOARD,
            parse_mode="HTML",
        )
        setup_state[user_id] = {
            "chat_id": chat_id,
            "group_name": group_name,
            "step": "features",
        }
        await msg.reply_text(get_setup_dm_sent())
    except Exception:
        await msg.reply_text(get_setup_dm_failed())


async def setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    with contextlib.suppress(Exception):
        await query.answer()
    user_id = query.from_user.id

    if user_id not in setup_state:
        return await query.edit_message_text(get_setup_expired())

    data = query.data
    state = setup_state[user_id]

    if data.startswith("setup_feat_"):
        feature = data.replace("setup_feat_", "")
        state["features"] = feature
        state["step"] = "strength"
        await query.edit_message_text(
            get_setup_step2_msg(state["group_name"], feature),
            reply_markup=STRENGTH_KEYBOARD,
            parse_mode="HTML",
        )

    elif data.startswith("setup_str_"):
        strength = data.replace("setup_str_", "")
        state["strength"] = strength

        try:
            await SettingsRepo.upsert_settings(
                chat_id=state["chat_id"],
                owner_id=user_id,
                group_name=state["group_name"],
                features=state["features"],
                strength=strength,
                is_active=True,
            )

            is_pro = await SubscriptionRepo.is_pro(user_id)
            msg_text = get_setup_complete_msg(state["group_name"], state["features"], strength, is_pro)
            await query.edit_message_text(msg_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Setup save failed: {e}")
            await query.edit_message_text(get_setup_failed())
        finally:
            setup_state.pop(user_id, None)
