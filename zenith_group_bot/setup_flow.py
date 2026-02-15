import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from zenith_group_bot.repository import SettingsRepo

logger = logging.getLogger("SETUP_FLOW")

async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    bot_username = context.bot.username

    member = await context.bot.get_chat_member(chat_id, user_id)
    if member.status not in ["administrator", "creator"]:
        try: await update.message.delete()
        except: pass
        return

    existing = await SettingsRepo.get_settings(chat_id)
    if existing and existing.is_active and existing.owner_id != user_id:
        return await update.message.reply_text(f"⚠️ This group is secured by Owner ID: {existing.owner_id}.")

    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status != "administrator":
            return await update.message.reply_text("❌ Missing Permissions. Promote me to Administrator.")
        if not bot_member.can_delete_messages or not bot_member.can_restrict_members:
            return await update.message.reply_text("❌ Ensure I have: \n• **Delete Messages**\n• **Ban Users**", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to check permissions: {e}")
        return await update.message.reply_text("❌ Error checking permissions.")

    await SettingsRepo.upsert_settings(chat_id, user_id, update.effective_chat.title)

    keyboard = [[InlineKeyboardButton("⚙️ Configure Zenith Group BOT (Private DM)", url=f"[https://t.me/](https://t.me/){bot_username}?start=setup_{chat_id}")]]
    await update.message.reply_text(
        "🛡️ <b>Zenith Group BOT Configuration</b>\n\nClick below to securely configure my settings.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def cmd_start_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private": return
    
    args = context.args
    if args and args[0].startswith("setup_"):
        # Bug Fix: Malicious or accidental Deep-link Injection Guard
        try:
            chat_id = int(args[0].split("_")[1])
        except (IndexError, ValueError):
            return await update.message.reply_text("❌ Invalid setup configuration link.")
        
        settings = await SettingsRepo.get_settings(chat_id)
        if not settings:
             return await update.message.reply_text("⏳ This setup session has expired or the group was unregistered.")
            
        if settings.owner_id != update.effective_user.id:
            return await update.message.reply_text("❌ Authentication failed. You do not own this session.")

        keyboard = [
            [InlineKeyboardButton("Abuse Detection Only", callback_data=f"feat_abuse_{chat_id}")],
            [InlineKeyboardButton("Spam & Link Shield Only", callback_data=f"feat_spam_{chat_id}")],
            [InlineKeyboardButton("Both (Recommended)", callback_data=f"feat_both_{chat_id}")]
        ]
        await update.message.reply_text(
            f"⚙️ <b>Configuring:</b> {settings.group_name}\n\nStep 1: What features would you like to enable?",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )
    else:
        tutorial = (
            "👋 <b>Welcome to Zenith Open Source Projects!</b>\n"
            "I am an enterprise-grade group moderation bot designed to stop spam, raids, and abuse.\n\n"
            "<b>🛠️ How to setup your group in 4 steps:</b>\n"
            "1️⃣ Add me to your Telegram group.\n"
            "2️⃣ Promote me to <b>Administrator</b>.\n"
            "3️⃣ Type <code>/setup</code> in your group chat.\n"
            "4️⃣ Click the secure button I generate to configure your custom settings here.\n\n"
        )
        await update.message.reply_text(tutorial, parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("feat_"):
        _, feature_type, chat_id = data.split("_")
        
        if not await SettingsRepo.get_settings(int(chat_id)):
            return await query.edit_message_text("⏳ Menu expired. Group data not found.")
            
        await SettingsRepo.upsert_settings(int(chat_id), query.from_user.id, None, features=feature_type)
        
        keyboard = [
            [InlineKeyboardButton("Low (Forgiving)", callback_data=f"str_low_{chat_id}")],
            [InlineKeyboardButton("Medium (Standard)", callback_data=f"str_medium_{chat_id}")],
            [InlineKeyboardButton("Strict (Zero Tolerance)", callback_data=f"str_strict_{chat_id}")]
        ]
        await query.edit_message_text("Step 2: Select the filtering strength.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("str_"):
        _, strength_type, chat_id = data.split("_")
        if not await SettingsRepo.get_settings(int(chat_id)):
            return await query.edit_message_text("⏳ Menu expired. Group data not found.")

        settings = await SettingsRepo.upsert_settings(int(chat_id), query.from_user.id, None, strength=strength_type, is_active=True)
        
        await query.edit_message_text(
            f"✅ <b>Setup Complete!</b>\n\nZenith is actively monitoring <b>{settings.group_name}</b>.",
            parse_mode="HTML"
        )
        try: await context.bot.send_message(int(chat_id), "✅ <b>Zenith Group BOT Configuration Complete.</b>\nAll security systems are online.", parse_mode="HTML")
        except: pass

    elif data.startswith("del_"):
        chat_id = int(data.split("_")[1])
        success = await SettingsRepo.wipe_group_container(chat_id, query.from_user.id)
        if success:
            await query.edit_message_text("🗑️ Container wiped successfully. All data erased.")
            try: await context.bot.send_message(chat_id, "⚠️ Zenith Group BOT has been unregistered. Security offline.")
            except: pass
        else:
            await query.edit_message_text("❌ Failed to wipe data.")

async def cmd_deletegroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private": return
    groups = await SettingsRepo.get_owned_groups(update.effective_user.id)
    if not groups: return await update.message.reply_text("You don't have any active setups.")
    keyboard = [[InlineKeyboardButton(f"🗑️ Wipe {g.group_name}", callback_data=f"del_{g.chat_id}")] for g in groups]
    await update.message.reply_text("Select a group container to completely erase:", reply_markup=InlineKeyboardMarkup(keyboard))