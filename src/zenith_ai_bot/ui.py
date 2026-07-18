from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID
from core.formatters import format_progress_bar

PERSONAS = {
    "default": {"emoji": "🤖", "name": "Default", "description": "General purpose AI assistant"},
    "coder": {"emoji": "💻", "name": "Coder", "description": "Code expert - debugging, writing, explaining"},
    "writer": {"emoji": "✍️", "name": "Writer", "description": "Creative writing, content creation"},
    "analyst": {"emoji": "📊", "name": "Analyst", "description": "Data analysis, insights, reports"},
    "tutor": {"emoji": "🎓", "name": "Tutor", "description": "Teaching, explanations, learning"},
    "debate": {"emoji": "⚔️", "name": "Debate", "description": "Argumentative discussions"},
    "roast": {"emoji": "🔥", "name": "Roast", "description": "Witty comebacks and roasts"},
}


def get_ai_dashboard(is_pro: bool, persona: str, usage: dict) -> InlineKeyboardMarkup:
    persona_info = PERSONAS.get(persona, PERSONAS["default"])
    persona_label = f"{persona_info['emoji']} {persona_info['name']}"

    message_limit = usage.get("message_limit", 10) if not is_pro else usage.get("message_limit", 100)
    messages_used = usage.get("messages_used", 0)

    message_bar = format_progress_bar(messages_used, message_limit)

    rows = [
        [
            InlineKeyboardButton(
                f"{'💎' if is_pro else '🆓'} {'PRO ACTIVE' if is_pro else 'FREE TIER'}", callback_data="ai_status"
            )
        ],
        [
            InlineKeyboardButton(f"🎭 Persona: {persona_label}", callback_data="ai_personas"),
            InlineKeyboardButton(f"📊 {message_bar}", callback_data="ai_usage"),
        ],
        [
            InlineKeyboardButton("🔬 Research", callback_data="ai_research_help"),
            InlineKeyboardButton("📝 Summarize", callback_data="ai_summarize_help"),
        ],
        [
            InlineKeyboardButton("💻 Code", callback_data="ai_code_help"),
            InlineKeyboardButton("🎨 Imagine", callback_data="ai_imagine_help"),
        ],
        [InlineKeyboardButton("💬 Chat History", callback_data="ai_history")],
    ]
    if not is_pro:
        rows.append([InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")])
    return InlineKeyboardMarkup(rows)


def get_persona_keyboard(current: str, is_pro: bool = False) -> InlineKeyboardMarkup:
    available_personas = PERSONAS if is_pro else {"default": PERSONAS["default"]}

    rows = []
    for key, info in available_personas.items():
        marker = " ✅" if key == current else ""
        rows.append(
            [InlineKeyboardButton(f"{info['emoji']} {info['name']}{marker}", callback_data=f"ai_persona_{key}")]
        )

    if not is_pro:
        rows.append([InlineKeyboardButton("💎 Unlock More Personas", url=f"tg://user?id={ADMIN_USER_ID}")])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="ai_main_menu")])
    return InlineKeyboardMarkup(rows)


def get_persona_preview_msg(persona_key: str) -> str:
    """Get the preview message for a persona."""
    info = PERSONAS.get(persona_key, PERSONAS["default"])

    return f"<b>{info['emoji']} {info['name']}</b>\n\n" f"{info['description']}\n\n" f"<i>Switch to this persona?</i>"


def get_confirm_persona_switch(persona_key: str) -> InlineKeyboardMarkup:
    info = PERSONAS.get(persona_key, PERSONAS["default"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"✅ Switch to {info['name']}", callback_data=f"ai_switch_persona_{persona_key}")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="ai_personas")],
        ]
    )


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Terminal", callback_data="ai_main_menu")]])


def get_history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑️ Clear History", callback_data="ai_clear_history_confirm")],
            [InlineKeyboardButton("🔙 Back", callback_data="ai_main_menu")],
        ]
    )


def get_confirm_clear_history() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Yes, Clear All", callback_data="ai_clear_history")],
            [InlineKeyboardButton("✖ Cancel", callback_data="ai_history")],
        ]
    )


def get_confirm_clear_history_msg() -> str:
    return (
        "⚠️ <b>Clear Chat History?</b>\n\n"
        "This will delete all your conversation history with the AI.\n"
        "This action cannot be undone."
    )


def get_usage_card(usage: dict, is_pro: bool = False) -> str:
    """Format usage display card."""
    message_limit = usage.get("message_limit", 10) if not is_pro else usage.get("message_limit", 100)
    messages_used = usage.get("messages_used", 0)
    messages_remaining = max(0, message_limit - messages_used)

    message_bar = format_progress_bar(messages_used, message_limit)

    message = f"""
<b>📊 Daily Usage</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>💬 Messages:</b>
{message_bar}
<i>{messages_remaining}/{message_limit} remaining</i>
"""

    if is_pro:
        search_remaining = usage.get("searches_remaining", "Unlimited")
        research_remaining = usage.get("research_remaining", "Unlimited")

        message += f"""
<b>🔍 Searches:</b> {search_remaining}
<b>🔬 Research:</b> {research_remaining}
"""

    message += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

    if not is_pro and messages_used >= message_limit * 0.8:
        message += "<i>⚠️ You're running low on messages! Upgrade to PRO for 100/day.</i>"

    return message


def get_feature_help_msg(feature: str, is_pro: bool = False) -> tuple:
    """Get help message and keyboard for a feature."""
    help_messages = {
        "research": (
            "🔬 <b>Deep Research</b>\n\n"
            "Perform multi-pass research on any topic and get a synthesized report.\n\n"
            "<b>Usage:</b> /research [topic]\n\n"
            "<b>Example:</b>\n"
            "/research impact of Bitcoin on global economy"
        ),
        "summarize": (
            "📝 <b>Document Summarizer</b>\n\n"
            "Summarize articles, YouTube videos, or long documents.\n\n"
            "<b>Usage:</b> /summarize [URL or text]\n\n"
            "<b>Example:</b>\n"
            "/summarize https://example.com/article"
        ),
        "code": (
            "💻 <b>Code Expert</b>\n\n"
            "Generate code, debug issues, or explain programming concepts.\n\n"
            "<b>Usage:</b> /code [your prompt]\n\n"
            "<b>Example:</b>\n"
            "/code write a Python function to fibonacci"
        ),
        "imagine": (
            "🎨 <b>Image Prompt Crafter</b>\n\n"
            "Generate optimized prompts for AI image generators like Midjourney, DALL-E.\n\n"
            "<b>Usage:</b> /imagine [your idea]\n\n"
            "<b>Example:</b>\n"
            "/imagine a cyberpunk city at night"
        ),
    }

    message = help_messages.get(feature, "Feature help not available.")

    if feature not in help_messages:
        return message, get_back_button()

    if feature in ["research", "summarize"] and not is_pro:
        message += "\n\n🔒 <b>Pro Feature</b>\nUpgrade to PRO to unlock this feature."
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
                [InlineKeyboardButton("🔙 Back", callback_data="ai_main_menu")],
            ]
        )
    else:
        keyboard = get_back_button()

    return message, keyboard


def get_typing_indicator_msg() -> str:
    return "⏳ <i>Thinking...</i>"


def get_generating_response_msg(persona: str = None) -> str:
    """Message shown while AI is generating response."""
    persona_info = PERSONAS.get(persona, PERSONAS["default"])
    return f"🤖 <i>{persona_info['name']} is typing...</i>"


def get_pro_feature_msg(feature: str) -> tuple:
    """Returns message and keyboard for locked pro feature."""
    message = (
        f"🔒 <b>Pro Feature: {feature}</b>\n\n"
        "This feature is available exclusively for PRO members.\n\n"
        "💎 <b>Pro Benefits (₹149/month):</b>\n"
        "• Unlimited messages\n"
        "• 7 AI personas\n"
        "• Deep research\n"
        "• Document summarizer\n"
        "• Code interpreter\n"
        "• Chat history\n"
        "• Image prompt crafter"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
            [InlineKeyboardButton("🔑 Activate Key", callback_data="ai_activate_help")],
            [InlineKeyboardButton("🔙 Back", callback_data="ai_main_menu")],
        ]
    )

    return message, keyboard


def get_limit_reached_msg(feature: str, current: int, limit: int) -> str:
    """Message when user hits a limit."""
    return (
        f"🚫 <b>Limit Reached: {feature}</b>\n\n"
        f"You've used {current}/{limit} for today.\n\n"
        "⏰ Resets at midnight UTC.\n\n"
        "💎 Upgrade to PRO for higher limits."
    )


def get_ai_welcome_msg(name: str, is_pro: bool, days_left: int = 0, usage: dict = None) -> str:
    """Welcome message for AI bot."""
    tier_badge = "💎 PRO" if is_pro else "🆓 Free"
    tier_info = f"{days_left} days remaining" if is_pro else "Limited features"

    message_limit = usage.get("message_limit", 10) if not is_pro else usage.get("message_limit", 100)
    messages_used = usage.get("messages_used", 0)
    messages_remaining = max(0, message_limit - messages_used)

    message = f"""
<b>🤖 Zenith AI Assistant</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👋 Welcome, <b>{name}</b>!

<b>Tier:</b> {tier_badge} ({tier_info})

<b>Today's Usage:</b>
💬 Messages: {messages_remaining}/{message_limit} remaining
"""

    if not is_pro:
        message += """
━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>Upgrade to PRO:</b>
• 100 messages/day
• 6 AI personas
• Deep research
• Document summarizer
• Code interpreter
"""

    message += """
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Commands:</b>
• /ask [question] - Chat with AI
• /persona - Switch AI personality
• /research - Deep research
• /summarize - Summarize content
• /code - Code assistance
• /imagine - Image prompts
• /history - View chat history
"""

    return message


def get_history_list_msg(history: list) -> str:
    """Format chat history list."""
    if not history:
        return "💬 <b>Chat History</b>\n\nNo messages yet. Start chatting with /ask!"

    message = "💬 <b>Chat History</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, msg in enumerate(history[-10:], 1):
        role = msg.get("role", "user")
        content = msg.get("content", "")[:50]
        if len(msg.get("content", "")) > 50:
            content += "..."

        emoji = "👤" if role == "user" else "🤖"
        message += f"{i}. {emoji} {content}\n"

    message += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "<i>Use /clear to delete all history.</i>"

    return message


def get_no_search_results_msg() -> str:
    return (
        "🔍 <b>No Results Found</b>\n\n"
        "I couldn't find any relevant information for your query.\n\n"
        "Try:\n"
        "• Using different keywords\n"
        "• Being more specific\n"
        "• Checking the spelling"
    )


def get_research_progress_msg(stage: str) -> str:
    """Get progress message for research stages."""
    stages = {
        "searching": "🔍 Searching for information...",
        "analyzing": "📊 Analyzing sources...",
        "synthesizing": "✨ Synthesizing report...",
        "complete": "✅ Research complete!",
    }
    return stages.get(stage, stage)
