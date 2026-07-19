from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID
from core.formatters import format_divider, format_progress_bar
from zenith_ai_bot.prompts import PERSONAS


def get_ai_dashboard(is_pro: bool, persona: str, usage: dict) -> InlineKeyboardMarkup:
    persona_info = PERSONAS.get(persona, PERSONAS["default"])
    persona_label = f"{persona_info['icon']} {persona_info['name']}"

    message_limit = usage.get("message_limit", 100) if is_pro else usage.get("message_limit", 10)
    messages_used = usage.get("messages_used", 0)
    message_bar = format_progress_bar(messages_used, message_limit)

    tier_label = "PRO ACTIVE" if is_pro else "FREE TIER"
    rows = [
        [InlineKeyboardButton(tier_label, callback_data="ai_status")],
        [
            InlineKeyboardButton(f"Persona: {persona_label}", callback_data="ai_personas"),
            InlineKeyboardButton(f"{message_bar}", callback_data="ai_usage"),
        ],
        [
            InlineKeyboardButton("Research", callback_data="ai_research_help"),
            InlineKeyboardButton("Summarize", callback_data="ai_summarize_help"),
        ],
        [
            InlineKeyboardButton("Code", callback_data="ai_code_help"),
            InlineKeyboardButton("Imagine", callback_data="ai_imagine_help"),
        ],
        [
            InlineKeyboardButton("Chat History", callback_data="ai_history"),
            InlineKeyboardButton("🔑 Groq Key", callback_data="ai_show_key_setup"),
        ],
    ]
    if not is_pro:
        rows.append([InlineKeyboardButton("Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")])
    return InlineKeyboardMarkup(rows)


def get_persona_keyboard(current: str, is_pro: bool = False) -> InlineKeyboardMarkup:
    available = PERSONAS if is_pro else {"default": PERSONAS["default"]}
    rows = []
    for key, info in available.items():
        marker = " \u2714" if key == current else ""
        rows.append([InlineKeyboardButton(f"{info['icon']} {info['name']}{marker}", callback_data=f"ai_persona_{key}")])
    if not is_pro:
        rows.append([InlineKeyboardButton("Unlock More Personas", url=f"tg://user?id={ADMIN_USER_ID}")])
    rows.append([InlineKeyboardButton("Back", callback_data="ai_main_menu")])
    return InlineKeyboardMarkup(rows)


def get_persona_preview_msg(persona_key: str) -> str:
    info = PERSONAS.get(persona_key, PERSONAS["default"])
    return f"<b>{info['icon']} {info['name']}</b>\n\n{info.get('description', '')}\n\nSwitch to this persona?"


def get_confirm_persona_switch(persona_key: str) -> InlineKeyboardMarkup:
    info = PERSONAS.get(persona_key, PERSONAS["default"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Switch to {info['name']}", callback_data=f"ai_switch_persona_{persona_key}")],
            [InlineKeyboardButton("Cancel", callback_data="ai_personas")],
        ]
    )


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="ai_main_menu")]])


def get_history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Clear History", callback_data="ai_clear_history_confirm")],
            [InlineKeyboardButton("Back", callback_data="ai_main_menu")],
        ]
    )


def get_confirm_clear_history() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, Clear All", callback_data="ai_clear_history")],
            [InlineKeyboardButton("Cancel", callback_data="ai_history")],
        ]
    )


def get_confirm_clear_history_msg() -> str:
    return (
        "<b>Clear Chat History?</b>\n\n"
        "This will delete all your conversation history with the AI.\n"
        "This action cannot be undone."
    )


def get_usage_card(usage: dict, is_pro: bool = False) -> str:
    q_limit = 60 if is_pro else 5
    s_limit = "Unlimited" if is_pro else "1"
    lines = [
        "<b>Today's Usage</b>",
        format_divider(),
        "",
        f"Queries: {usage['queries']}/{q_limit}",
        f"Summaries: {usage['summarizes']}/{s_limit}",
        f"Active Persona: {usage['persona'].capitalize()}",
        "",
        "Usage resets daily at midnight UTC.",
    ]
    return "\n".join(lines)


def get_welcome_msg(is_pro: bool, days_left: int, usage: dict, persona: str) -> str:
    p = PERSONAS.get(persona, PERSONAS["default"])
    if is_pro:
        status = f"PRO Active \u2014 {days_left} day{'s' if days_left != 1 else ''} remaining"
    else:
        status = "FREE Tier \u2014 Upgrade for unlimited power"

    q_limit = 60 if is_pro else 5
    lines = [
        "Zenith AI Terminal",
        format_divider(),
        "",
        status,
        f"Persona: {p['name']}",
        f"Queries Today: {usage['queries']}/{q_limit}",
        "",
        "Commands:",
        "\u2022 /zenith [question] \u2014 Ask anything",
        "\u2022 /persona [name] \u2014 Switch AI personality",
        "\u2022 /research [topic] \u2014 Deep research",
        "\u2022 /summarize [text] \u2014 Summarize text",
        "\u2022 /code [desc] \u2014 Code generator",
        "\u2022 /imagine [desc] \u2014 Image prompts",
        "\u2022 /history \u2014 Chat memory",
        "\u2022 /setkey [key] \u2014 Connect Groq API key",
        "",
        "Pro Required for research, code, imagine, history, non-default personas.",
    ]
    return "\n".join(f"<b>{line}</b>" if i == 0 else line for i, line in enumerate(lines))


def get_status_msg(is_pro: bool, days: int) -> str:
    if is_pro:
        return (
            f"<b>Pro Subscription</b>\n{format_divider()}\n\n"
            f"Status: Active\n"
            f"Remaining: {days} day{'s' if days != 1 else ''}\n\n"
            f"<b>Pro Benefits:</b>\n"
            f"\u2022 60 queries/hour (12x Free)\n"
            f"\u2022 4096 token responses (4x Free)\n"
            f"\u2022 6 AI Personas\n"
            f"\u2022 Deep Research Mode\n"
            f"\u2022 Code Generator\n"
            f"\u2022 Image Prompt Crafter\n"
            f"\u2022 Chat Memory (10 messages)\n"
            f"\u2022 Unlimited Summarization"
        )
    return (
        f"<b>Free Tier</b>\n{format_divider()}\n\n"
        f"<b>Limits:</b>\n"
        f"\u2022 5 queries/hour\n"
        f"\u2022 1024 token responses\n"
        f"\u2022 Default persona only\n"
        f"\u2022 1 summary/day\n\n"
        f"Unlock everything:\n"
        f"/activate [YOUR_KEY]"
    )


def get_personas_locked_msg() -> str:
    return (
        "<b>Pro Feature: AI Personas</b>\n\n"
        "Switch between specialized AI personalities:\n"
        "\u2022 Coder \u2014 Production-grade code\n"
        "\u2022 Writer \u2014 Creative content\n"
        "\u2022 Analyst \u2014 Strategic analysis\n"
        "\u2022 Tutor \u2014 Patient teaching\n"
        "\u2022 Debate \u2014 Devil's advocate\n"
        "\u2022 Roast \u2014 Comedy roasts\n\n"
        "/activate [YOUR_KEY]"
    )


def get_personas_select_msg() -> str:
    return "<b>Select Persona</b>\n\nChoose your AI personality:"


def get_persona_switched_msg(persona_key: str) -> str:
    p = PERSONAS.get(persona_key, PERSONAS["default"])
    return f"Persona Switched\n\n{p['icon']} Now talking to {p['name']}"


def get_history_locked_msg() -> str:
    return (
        "<b>Pro Feature: Chat Memory</b>\n\n"
        "Zenith remembers your last 10 messages for contextual follow-ups.\n\n"
        "/activate [YOUR_KEY]"
    )


def get_history_empty_msg() -> str:
    return "<b>Chat Memory</b>\n\nNo history yet. Start chatting with /zenith!"


def get_history_list_msg(history: list) -> str:
    if not history:
        return get_history_empty_msg()

    lines = ["<b>Chat Memory</b>", format_divider(), ""]
    for msg in history[-6:]:
        role_icon = "User" if msg.role == "user" else "Zenith"
        preview = escape(msg.content[:80] + ("..." if len(msg.content) > 80 else ""))
        lines.append(f"<b>{role_icon}</b> <i>{escape(preview)}</i>")

    count = len(history)
    lines.append(f"\n{count} messages stored. Last 10 used for context.")
    return "\n".join(lines)


def get_history_cleared_msg(deleted: int) -> str:
    return f"History Cleared\n\n{deleted} messages removed."


def get_help_msg(is_pro: bool) -> str:
    lines = [
        "<b>Zenith AI Bot \u2014 Full Guide</b>",
        format_divider(),
        "",
        "<b>Main Commands:</b>",
        "\u2022 /start \u2014 Start the bot and see dashboard",
        "\u2022 /zenith [question] \u2014 Ask AI anything",
        "\u2022 /setkey [key] \u2014 Connect Groq API key",
        "\u2022 /mykey \u2014 Check API key status",
        "\u2022 /delkey \u2014 Remove API key",
        "\u2022 /help \u2014 Show this help message",
        "",
        "<b>Personas:</b>",
        "\u2022 /persona \u2014 View/switch AI personality",
        "  Available: Default, Coder, Writer, Analyst, Tutor, Debate, Roast",
        "",
        "<b>Text Tools:</b>",
        "\u2022 /summarize [text] \u2014 Summarize long text",
        "  (Reply to a message with /summarize)",
        "",
        "<b>Pro Features:</b>",
        "\u2022 /research [topic] \u2014 Deep research on any topic",
        "\u2022 /code [description] \u2014 Generate code in any language",
        "\u2022 /imagine [description] \u2014 Create image prompts",
        "\u2022 /history \u2014 View chat memory",
        "",
        "<b>Pro Benefits:</b>",
        "\u2022 Unlimited messages",
        "\u2022 7 AI personas",
        "\u2022 Longer responses",
        "\u2022 Priority support",
        "",
        "<b>Group Usage:</b>",
        "Add bot to groups and use:",
        "\u2022 /ask [question] \u2014 Ask AI in group",
        "\u2022 /grouphelp \u2014 Group-specific help",
        "",
        "<b>Upgrade to Pro:</b>",
        "Contact @admin to get your activation key!",
    ]
    return "\n".join(lines)


def get_activate_help() -> str:
    return "<b>Activate Pro</b>\n\n" "Usage: /activate [YOUR_KEY]\n\n" "Contact admin to purchase a Pro key."


def get_zenith_no_query_msg() -> str:
    return "Please provide a question or reply to a message with /zenith !"


def get_queue_full_msg() -> str:
    return "Zenith AI is currently at maximum capacity. Please try again shortly."


def get_worker_error_msg() -> str:
    return "Connection to AI lost. Please try again."


def get_no_key_msg() -> str:
    return (
        "To use AI features, please connect your Groq API key:\n"
        "<code>/setkey gsk_xxxx</code>\n\n"
        "Get a free key in 2 minutes at <b>console.groq.com</b>!"
    )


def get_ai_key_status_msg(has_key: bool):
    if has_key:
        return (
            "<b>Groq API Key Settings</b>\n"
            f"{format_divider()}\n\n"
            "Your Groq API key is currently connected and active.\n\n"
            "\u2022 To replace your key: <code>/setkey gsk_your_new_key</code>\n"
            "\u2022 To remove your key: <code>/delkey</code>\n\n"
            "This key powers your AI responses across both Zenith AI Bot and Crypto Bot."
        ), InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="ai_main_menu")]])
    return (
        "<b>Groq API Key Settings</b>\n"
        f"{format_divider()}\n\n"
        "No Groq API key is connected yet.\n\n"
        "To get set up in 2 minutes:\n"
        "1. Go to <b>console.groq.com</b> \u2192 API Keys\n"
        "2. Create a free API key\n"
        "3. Send it here:\n"
        "<code>/setkey gsk_your_api_key</code>"
    ), InlineKeyboardMarkup([
        [InlineKeyboardButton("How to get a free key", url="https://console.groq.com")],
        [InlineKeyboardButton("◀️ Back", callback_data="ai_main_menu")]
    ])


def get_ai_key_set_success_msg():
    text = (
        "<b>Groq API Key Connected!</b>\n"
        f"{format_divider()}\n\n"
        "Your Groq API key has been verified and saved. \U0001f680\n\n"
        "You can now use all AI capabilities right here using <code>/zenith [question]</code> or in any supported commands!"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back to Dashboard", callback_data="ai_main_menu")]])
    return text, kb


def get_ai_key_deleted_msg():
    text = (
        "<b>Groq API Key Removed</b>\n"
        f"{format_divider()}\n\n"
        "Your Groq API key has been deleted."
    )
    return text, InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="ai_main_menu")]])


def get_activate_help_msg() -> str:
    return "<b>Activate Pro</b>\n\n" "Usage: /activate [YOUR_KEY]\n\n" "Contact admin to purchase a Pro key."


def get_activate_help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Buy Pro", url=f"tg://user?id={ADMIN_USER_ID}")],
            [InlineKeyboardButton("Back", callback_data="ai_main_menu")],
        ]
    )


# Feature help messages
def get_feature_help_msg(feature: str, is_pro: bool = False) -> tuple:
    messages = {
        "research": (
            "<b>Deep Research</b>\n\n"
            "Multi-source research with news and web analysis.\n\n"
            "Usage: /research [TOPIC]\n" + ("Available with your Pro subscription." if is_pro else "Pro Required")
        ),
        "summarize": (
            "<b>Text Summarizer</b>\n\n"
            "Condense long texts into key takeaways.\n\n"
            "Usage: /summarize [TEXT]\n"
            "Or reply to any message with /summarize\n\n"
            f"Limit: {'Unlimited' if is_pro else '1/day (500 words max)'}"
        ),
        "code": (
            "<b>Code Generator</b>\n\n"
            "Production-ready code from natural language.\n\n"
            "Usage: /code [DESCRIPTION]\n" + ("Available with your Pro subscription." if is_pro else "Pro Required")
        ),
        "imagine": (
            "<b>Image Prompt Crafter</b>\n\n"
            "Optimized prompts for Midjourney, DALL-E, Stable Diffusion.\n\n"
            "Usage: /imagine [DESCRIPTION]\n" + ("Available with your Pro subscription." if is_pro else "Pro Required")
        ),
    }
    message = messages.get(feature, "Feature help not available.")
    if feature in ("research", "code", "imagine") and not is_pro:
        message += "\n\nPro Feature. Upgrade to PRO to unlock."
    return message, get_back_button()


from core.ui_components import pro_feature_locked_msg, pro_upgrade_keyboard


def get_pro_feature_msg(feature: str) -> tuple:
    message = pro_feature_locked_msg(feature)
    keyboard = pro_upgrade_keyboard(back_data="ai_main_menu")
    return message, keyboard


def get_limit_reached_msg(feature: str, current: int, limit: int) -> str:
    return (
        f"Limit Reached: {feature}\n\n"
        f"You've used {current}/{limit} for today.\n\n"
        "Resets at midnight UTC.\n\n"
        "Upgrade to PRO for higher limits."
    )


def get_research_help() -> str:
    return (
        "<b>Deep Research</b>\n\n"
        "Format: /research [TOPIC]\n\n"
        "Examples:\n"
        "\u2022 /research AI regulation in Europe 2025\n"
        "\u2022 /research best programming languages for fintech\n"
        "\u2022 /research electric vehicle market trends\n\n"
        "Tip: Be specific for better results."
    )


def get_code_help() -> str:
    return (
        "<b>Code Generator</b>\n\n"
        "Format: /code [DESCRIPTION]\n\n"
        "Examples:\n"
        "\u2022 /code Python FastAPI REST endpoint for user auth with JWT\n"
        "\u2022 /code React component for a sortable data table\n"
        "\u2022 /code Bash script to backup PostgreSQL database"
    )


def get_summarize_help() -> str:
    return (
        "<b>Text Summarizer</b>\n\n"
        "Usage:\n"
        "\u2022 /summarize [text]\n"
        "\u2022 Reply to any message with /summarize"
    )


def get_imagine_help() -> str:
    return (
        "<b>Image Prompt Crafter</b>\n\n"
        "Format: /imagine [DESCRIPTION]\n\n"
        "Examples:\n"
        "\u2022 /imagine a cyberpunk city at sunset with neon lights\n"
        "\u2022 /imagine portrait of an astronaut in a flower field\n"
        "\u2022 /imagine minimalist logo for a tech startup\n\n"
        "Tip: Be descriptive for better prompts."
    )


def get_summarize_limit_reached() -> str:
    return (
        "Daily limit reached (1/day Free tier).\n\n"
        "Upgrade to Zenith Pro for unlimited summaries.\n"
        "/activate [YOUR_KEY]"
    )


def get_persona_help() -> str:
    personas_list = "\n".join(f"  \u2022 {v['icon']} <code>{k}</code> \u2014 {v['name']}" for k, v in PERSONAS.items())
    return f"<b>AI Personas</b>\n\n" f"{personas_list}\n\n" f"Usage: /persona [name]\n\n" f"Example: /persona coder"


def get_persona_locked() -> str:
    return "\n\nPro required for non-default personas."


def get_persona_unknown(valid: str) -> str:
    return f"Unknown Persona\n\n" f"Available personas: {valid}\n\n" f"Usage: /persona coder"


def get_persona_already_using(name: str) -> str:
    return f"Already Using\n\nYou're already using {name} persona."


def get_code_no_query() -> str:
    return get_code_help()


def get_imagine_no_query() -> str:
    return get_imagine_help()
