import asyncio
import time
from typing import Optional, Callable, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, RetryAfter
from telegram.ext import ContextTypes


async def send_typing_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send typing action to indicate bot is processing."""
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
    except Exception:
        pass


async def send_upload_photo_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send upload photo action."""
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_photo"
        )
    except Exception:
        pass


async def send_upload_document_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send upload document action."""
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_document"
        )
    except Exception:
        pass


async def send_loading_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str = "⏳ Processing...",
    keyboard: Optional[InlineKeyboardMarkup] = None
) -> Optional[Any]:
    """Send a loading message and return the message object."""
    try:
        if update.callback_query:
            msg = await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            msg = await update.message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return msg
    except BadRequest:
        pass
    return None


async def edit_with_animation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> Optional[Any]:
    """Edit message with animation effect - try callback first, then message reply."""
    try:
        if update.callback_query:
            return await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
    except BadRequest:
        pass
    
    try:
        if update.message:
            return await update.message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
    except Exception:
        pass
    return None


async def update_loading_dots(
    message,
    context: ContextTypes.DEFAULT_TYPE,
    base_text: str,
    dot_count: int = 3,
    max_iterations: int = 6
) -> None:
    """Update a message with animated dots to show progress."""
    for i in range(max_iterations):
        dots = "." * ((i % dot_count) + 1)
        try:
            await message.edit_text(
                text=f"{base_text}{dots}",
                parse_mode="HTML"
            )
        except BadRequest:
            break
        await asyncio.sleep(0.5)


async def edit_with_stages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    stages: list[str],
    final_text: str,
    final_keyboard: Optional[InlineKeyboardMarkup] = None,
    delay: float = 0.8
) -> Optional[Any]:
    """Show progress through multiple stages, then final message."""
    msg = None
    
    for stage in stages:
        try:
            if msg is None:
                if update.callback_query:
                    msg = await update.callback_query.edit_message_text(
                        text=f"⏳ {stage}...",
                        parse_mode="HTML"
                    )
                elif update.message:
                    msg = await update.message.reply_text(
                        text=f"⏳ {stage}...",
                        parse_mode="HTML"
                    )
            else:
                msg = await msg.edit_text(
                    text=f"⏳ {stage}...",
                    parse_mode="HTML"
                )
        except BadRequest:
            pass
        await asyncio.sleep(delay)
    
    return await edit_with_animation(
        update, context, final_text, final_keyboard
    )


async def show_progress_bar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
    current: int,
    total: int,
    unit: str = "items"
) -> Optional[Any]:
    """Show a text-based progress bar."""
    bar_length = 15
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    percentage = int(100 * current / total) if total > 0 else 0
    
    text = f"<b>{title}</b>\n\n"
    text += f"{bar} {percentage}%\n"
    text += f"<i>{current}/{total} {unit}</i>"
    
    return await edit_with_animation(update, context, text)


def create_processing_keyboard(
    cancel_callback: str = "proc_cancel",
    cancel_text: str = "✖ Cancel"
) -> InlineKeyboardMarkup:
    """Create a keyboard showing processing state with cancel option."""
    keyboard = [
        [InlineKeyboardButton("⏳ Processing...", callback_data="proc_none")]
    ]
    if cancel_callback:
        keyboard.append([
            InlineKeyboardButton(cancel_text, callback_data=cancel_callback)
        ])
    return InlineKeyboardMarkup(keyboard)


def create_retry_keyboard(
    retry_callback: str = "retry_action",
    help_callback: str = "get_help"
) -> InlineKeyboardMarkup:
    """Create a keyboard with retry and help options."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Retry", callback_data=retry_callback),
            InlineKeyboardButton("❓ Help", callback_data=help_callback)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_confirm_keyboard(
    confirm_callback: str,
    cancel_callback: str = "confirm_cancel",
    confirm_text: str = "✅ Confirm",
    cancel_text: str = "✖ Cancel"
) -> InlineKeyboardMarkup:
    """Create a confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(confirm_text, callback_data=confirm_callback),
            InlineKeyboardButton(cancel_text, callback_data=cancel_callback)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_undo_keyboard(
    undo_callback: str,
    undo_text: str = "↩️ Undo",
    timeout_seconds: int = 10
) -> InlineKeyboardMarkup:
    """Create an undo keyboard with timeout indication."""
    keyboard = [
        [InlineKeyboardButton(f"{undo_text} ({timeout_seconds}s)", callback_data=undo_callback)]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_success_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
    message: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    emoji: str = "✅"
) -> Optional[Any]:
    """Send a formatted success message."""
    text = f"<b>{emoji} {title}</b>\n\n"
    text += f"{message}"
    
    return await edit_with_animation(update, context, text, keyboard)


async def send_error_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
    message: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    show_retry: bool = True
) -> Optional[Any]:
    """Send a formatted error message with optional retry."""
    text = f"<b>⚠️ {title}</b>\n\n"
    text += f"{message}"
    
    if show_retry and keyboard is None:
        keyboard = create_retry_keyboard()
    
    return await edit_with_animation(update, context, text, keyboard)


async def send_info_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
    message: str,
    keyboard: Optional[InlineKeyboardMarkup] = None
) -> Optional[Any]:
    """Send a formatted info message."""
    text = f"<b>ℹ️ {title}</b>\n\n"
    text += f"{message}"
    
    return await edit_with_animation(update, context, text, keyboard)


async def safe_edit_message(
    message,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> bool:
    """Safely edit a message, handling various errors."""
    try:
        await message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode
        )
        return True
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return True
        return False
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
            return True
        except Exception:
            return False
    except Exception:
        return False


async def delete_message_safe(
    message,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Safely delete a message."""
    try:
        await message.delete()
        return True
    except Exception:
        return False


def format_loading_stages(stages: list[str]) -> list[str]:
    """Format loading stages for display."""
    emojis = ["🔍", "📊", "⚙️", "🎯", "✨"]
    formatted = []
    for i, stage in enumerate(stages):
        emoji = emojis[i] if i < len(emojis) else "⏳"
        formatted.append(f"{emoji} {stage}")
    return formatted
