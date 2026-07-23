from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import ADMIN_USER_ID
from core.formatters import (
    format_alert,
    format_card,
    format_header,
    format_kv,
    format_progress_bar,
)
from core.llm_fallback import AVAILABLE_MODELS
from core.ui_components import pro_feature_locked_msg, pro_upgrade_keyboard
from zenith_ai_bot.prompts import PERSONAS


def get_ai_dashboard(
    is_pro: bool, persona: str, usage: dict, selected_model: str = "llama-3.3-70b-versatile"
) -> InlineKeyboardMarkup:
    persona_info = PERSONAS.get(persona, PERSONAS["default"])
    persona_label = f"{persona_info['icon']} {persona_info['name']}"

    model_info = AVAILABLE_MODELS.get(selected_model, AVAILABLE_MODELS["llama-3.3-70b-versatile"])
    model_label = f"{model_info['icon']} {model_info['name']}"

    message_limit = usage.get("message_limit", 100) if is_pro else usage.get("message_limit", 10)
    messages_used = usage.get("messages_used", 0)
    message_bar = format_progress_bar(messages_used, message_limit, length=12)

    tier_label = "💎 PRO MEMBERSHIP ACTIVE" if is_pro else "⚪ STANDARD FREE TIER"
    rows = [
        [InlineKeyboardButton(tier_label, callback_data="ai_status")],
        [
            InlineKeyboardButton(f"🧠 Persona: {persona_label}", callback_data="ai_personas"),
            InlineKeyboardButton(f"⚙️ Engine: {model_label}", callback_data="ai_models"),
        ],
        [
            InlineKeyboardButton("✨ AI Features", callback_data="ai_features_menu"),
            InlineKeyboardButton("📚 Commands Guide", callback_data="ai_help_menu"),
        ],
        [
            InlineKeyboardButton("💬 Chat Memory", callback_data="ai_history"),
            InlineKeyboardButton("🔑 Groq API Key", callback_data="ai_show_key_setup"),
        ],
    ]
    if not is_pro:
        rows.append(
            [InlineKeyboardButton("💎 Upgrade to Pro Bundle (Unlimited Access)", url=f"tg://user?id={ADMIN_USER_ID}")]
        )
    return InlineKeyboardMarkup(rows)


def get_model_selector_keyboard(current_model: str, is_pro: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for model_id, info in AVAILABLE_MODELS.items():
        marker = " [🔒 PRO]" if info["tier"] == "pro" and not is_pro else " ✅" if model_id == current_model else ""
        rows.append(
            [
                InlineKeyboardButton(
                    f"{info['icon']} {info['name']} ({info['description']}){marker}",
                    callback_data=f"ai_set_model_{model_id}",
                )
            ]
        )
    if not is_pro:
        rows.append([InlineKeyboardButton("💎 Unlock All 70B & DeepSeek Models", url=f"tg://user?id={ADMIN_USER_ID}")])
    rows.append([InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")])
    return InlineKeyboardMarkup(rows)


def get_model_selector_msg(current_model: str) -> str:
    m_info = AVAILABLE_MODELS.get(current_model, AVAILABLE_MODELS["llama-3.3-70b-versatile"])
    engine_label = f"{m_info['icon']} {m_info['name']}"
    return (
        f"{format_header('AI Intelligence Engine', 'Select your active neural processor', 'MODELS')}\n"
        f"{format_kv('Active Engine', engine_label, '⚡')}\n"
        f"  <i>└ {m_info['description']}</i>\n\n"
        f"All models are protected by Zenith's high-reliability circuit-breaker & auto-fallback matrix."
    )


def get_persona_keyboard(current: str, is_pro: bool = False) -> InlineKeyboardMarkup:
    available = PERSONAS if is_pro else {"default": PERSONAS["default"]}
    rows = []
    for key, info in available.items():
        marker = " ✅" if key == current else ""
        rows.append([InlineKeyboardButton(f"{info['icon']} {info['name']}{marker}", callback_data=f"ai_persona_{key}")])
    if not is_pro:
        rows.append([InlineKeyboardButton("💎 Unlock 6 Specialized AI Personas", url=f"tg://user?id={ADMIN_USER_ID}")])
    rows.append([InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")])
    return InlineKeyboardMarkup(rows)


def get_persona_preview_msg(persona_key: str) -> str:
    info = PERSONAS.get(persona_key, PERSONAS["default"])
    persona_title = f"{info['icon']} {info['name']}"
    return (
        f"{format_header(persona_title, 'AI Personality Profile', 'PERSONA')}\n"
        f"{info.get('description', '')}\n\n"
        f"Would you like to switch your neural persona to <b>{info['name']}</b>?"
    )


def get_confirm_persona_switch(persona_key: str) -> InlineKeyboardMarkup:
    info = PERSONAS.get(persona_key, PERSONAS["default"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"✅ Activate {info['name']}", callback_data=f"ai_switch_persona_{persona_key}")],
            [InlineKeyboardButton("✕ Cancel", callback_data="ai_personas")],
        ]
    )


def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")]])


def get_history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑️ Clear Context Memory", callback_data="ai_clear_history_confirm")],
            [InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")],
        ]
    )


def get_confirm_clear_history() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚠️ Yes, Purge Memory", callback_data="ai_clear_history")],
            [InlineKeyboardButton("✕ Cancel", callback_data="ai_history")],
        ]
    )


def get_confirm_clear_history_msg() -> str:
    return format_alert(
        "Purge Context Memory",
        "This will permanently wipe your active conversation history with the AI.\nContextual awareness will reset to fresh state.",
        "WARNING",
    )


def get_usage_card(usage: dict, is_pro: bool = False) -> str:
    items = [
        f"Neural Queries: <code>{usage['queries']}</code>",
        f"Document Summaries: <code>{usage['summarizes']}</code>",
        f"Active Persona: <b>{usage['persona'].capitalize()}</b>",
    ]
    return (
        f"{format_header('Daily Telemetry', 'Quotas & Neural Usage', 'USAGE')}\n"
        f"{format_card('Current Consumption', items, '📊')}\n\n"
        f"<i>⚡ Using your personal API key (Unlimited)</i>"
    )


def get_welcome_msg(usage: dict, persona: str) -> str:
    p = PERSONAS.get(persona, PERSONAS["default"])
    items = [
        f"Active Persona: <b>{p['icon']} {p['name']}</b>",
        f"Usage Mode: <b>BYOK (Unlimited)</b>",
    ]
    text = (
        f"{format_header('Zenith AI Terminal', 'Autonomous Neural Intelligence Engine')}\n"
        f"{format_card('System Status', items, '⚡')}"
    )
    return text


def get_status_msg(is_pro: bool, days: int) -> str:
    if is_pro:
        items = [
            "Full access to all 6 AI Personas",
            "Multi-pass Deep Research Engine",
            "Principal Code Architect generator",
            "Visual Prompt Crafter for AI art",
            "Context memory (10 message rolling window)",
        ]
        return (
            f"{format_header('Subscription Status', 'Zenith Pro Membership', 'ACTIVE')}\n"
            f"{format_kv('Days Remaining', f'{days} days', '🗓️')}\n"
            f"{format_kv('System Tier', 'Pro Suite', '💎')}\n\n"
            f"{format_card('Unlocked Pro Capabilities', items, '✨')}"
        )
    items = [
        "Default assistant persona only",
        "No Context memory",
    ]
    return (
        f"{format_header('Subscription Status', 'Standard Tier Access', 'FREE')}\n"
        f"{format_card('Current Tier Limitations', items, '🔒')}\n\n"
        f"⚡ <i>Unlock the full potential of Zenith AI with our Pro Bundle. Contact @roshhellwett or use <code>/activate YOUR-KEY</code>.</i>"
    )

def get_api_key_status_msg(api_key: str | None, tokens_used: int) -> str:
    if not api_key:
        return (
            "🔑 <b>Groq API Key Required</b>\n\n"
            "You are using Zenith in <b>BYOK (Bring Your Own Key)</b> mode. This allows for unlimited usage without daily limits!\n\n"
            "<b>Status:</b> ❌ Not configured\n\n"
            "To unlock all AI features, please set your Groq API key using:\n"
            "<code>/setkey [your_key]</code>"
        )
    
    masked_key = f"{api_key[:8]}•••••••••••••••••••••••••••••{api_key[-4:]}" if len(api_key) > 12 else "••••••••"
    return (
        "🔑 <b>Groq API Key Active</b>\n\n"
        "You are using Zenith in <b>BYOK (Bring Your Own Key)</b> mode. This allows for unlimited usage without daily limits!\n\n"
        f"<b>Status:</b> ✅ Active\n"
        f"<b>Key:</b> <code>{masked_key}</code>\n"
        f"<b>Total Tokens Used:</b> <code>{tokens_used:,}</code>\n\n"
        "<i>To rotate or reset your key, use the following command:</i>\n"
        "<code>/rotate [new_key]</code> (This will also reset your token count)"
    )


def get_personas_locked_msg() -> str:
    items = [
        "<b>Coder</b> — Production-grade software & debugging",
        "<b>Writer</b> — Creative prose & content mastery",
        "<b>Analyst</b> — Strategic data & market breakdowns",
        "<b>Tutor</b> — Patient, step-by-step educational explanations",
        "<b>Debate</b> — Rigorous dialectic & counter-arguments",
        "<b>Roast</b> — Witty comedy & sharp satire",
    ]
    return (
        f"{format_header('Specialized AI Personas', 'Custom Neural Profiles', 'PRO REQUIRED')}\n"
        f"{format_card('Available Personalities', items, '🧠')}\n\n"
        f"💎 <i>Upgrade to Pro to unlock all specialized neural personas using <code>/activate YOUR-KEY</code>.</i>"
    )


def get_personas_select_msg() -> str:
    return f"{format_header('Select Neural Persona', 'Tailor the AI tone and domain focus', 'PERSONAS')}\nSelect your desired persona below:"


def get_persona_switched_msg(persona_key: str) -> str:
    p = PERSONAS.get(persona_key, PERSONAS["default"])
    return format_alert(
        f"Persona Switched: {p['name']}",
        f"{p['icon']} Your neural assistant is now configured as <b>{p['name']}</b>.\nContext personality adapted.",
        "SUCCESS",
    )


def get_history_locked_msg() -> str:
    return format_alert(
        "Chat Memory Locked",
        "Zenith's rolling context memory (retaining recent messages for multi-turn conversations) requires a Pro membership.\n\nActivate using <code>/activate YOUR-KEY</code>.",
        "PRO",
    )


def get_history_empty_msg() -> str:
    return (
        f"{format_header('Context Memory', 'Active Conversation Buffer', 'EMPTY')}\n"
        f"📭 No conversation history stored.\nStart chatting using <code>/zenith [question]</code> to build context."
    )


def get_history_list_msg(history: list) -> str:
    if not history:
        return get_history_empty_msg()

    lines = [
        format_header("Context Memory", "Rolling 10-Message Buffer", f"{len(history)} MSGS"),
        "<b>Recent Turn Log:</b>",
    ]
    for msg in history[-6:]:
        role_icon = "👤 <b>You:</b>" if msg.role == "user" else "🤖 <b>Zenith:</b>"
        preview = escape(msg.content[:85] + ("..." if len(msg.content) > 85 else ""))
        lines.append(f"  {role_icon} <i>{preview}</i>")

    lines.append("")
    lines.append(f"▫️ <code>{len(history)}</code> total turns recorded in buffer.")
    return "\n".join(lines)


def get_history_cleared_msg(deleted: int) -> str:
    return format_alert(
        "Memory Purged Successfully",
        f"Cleared <b>{deleted}</b> messages from context buffer.\nNeural state reset to clean starting baseline.",
        "SUCCESS",
    )


def get_help_msg() -> str:
    cmds = [
        "<code>/zenith [question]</code> — Query autonomous intelligence",
        "<code>/persona [name]</code> — Switch specialized AI personality",
        "<code>/research [topic]</code> — Deep multi-source investigative reports",
        "<code>/summarize [text/url]</code> — Condense documents & YouTube links",
        "<code>/code [desc]</code> — Principal code generator & refactoring",
        "<code>/imagine [desc]</code> — Visual prompt crafter for AI image models",
        "<code>/history</code> — Inspect or wipe active memory buffer",
        "<code>/setkey [key]</code> — Connect personal Groq API key",
        "<code>/mykey</code> — Inspect API key verification status",
        "<code>/delkey</code> — Remove personal API key",
        "<code>/help</code> — Display comprehensive terminal guide",
    ]
    text = (
        f"{format_header('Terminal Documentation', 'Zenith AI Codex Guide', 'GUIDE')}\n"
        f"{format_card('Quick Command Registry', cmds, '⚡')}\n\n"
        f"<b>🤖 Group Intelligence:</b> Add Zenith to any group and use <code>/ask [question]</code> for instant collaborative AI answers."
    )
    return text

def get_ai_features_msg() -> str:
    return (
        f"{format_header('AI Features', 'Specialized Neural Tools', 'FEATURES')}\n"
        f"Explore Zenith's powerful multi-modal capabilities."
    )

def get_ai_features_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔬 Deep Research", callback_data="ai_research_help"),
            InlineKeyboardButton("📝 Summarize Text", callback_data="ai_summarize_help"),
        ],
        [
            InlineKeyboardButton("💻 Code Architect", callback_data="ai_code_help"),
            InlineKeyboardButton("🎨 Imagine UI/Art", callback_data="ai_imagine_help"),
        ],
        [InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")]
    ])

def get_ai_help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")]
    ])


def get_activate_help() -> str:
    return format_alert(
        "License Activation",
        "Enter your license key using the format:\n<code>/activate ZENITH-XXXX-XXXX</code>\n\nContact @roshhellwett to acquire your Pro bundle key.",
        "PRO",
    )


def get_zenith_no_query_msg() -> str:
    return format_alert(
        "Missing Query Parameter",
        "Please provide your question alongside the command:\n<code>/zenith [your question here]</code>\n\nOr reply directly to any message with <code>/zenith</code>.",
        "WARNING",
    )


def get_queue_full_msg() -> str:
    return format_alert(
        "System At Max Capacity",
        "The neural cluster is processing maximum concurrent queries.\nPlease retry your request in a few seconds.",
        "WARNING",
    )


def get_worker_error_msg() -> str:
    return format_alert(
        "Neural Link Interrupted",
        "Lost connection during response synthesis. Our fallback circuit breaker is re-routing.\nPlease try your query again.",
        "ERROR",
    )


def get_no_key_msg() -> str:
    return (
        f"{format_header('API Key Required', 'Connect Groq to activate features', 'SETUP')}\n"
        f"To execute AI requests, please connect a free Groq API key:\n"
        f"<code>/setkey gsk_xxxx</code>\n\n"
        f"<b>⚡ How to get a free key in 60 seconds:</b>\n"
        f"  1. Visit <b>console.groq.com</b> and sign in\n"
        f"  2. Navigate to API Keys → Create API Key\n"
        f"  3. Copy your key and send: <code>/setkey gsk_your_key</code>"
    )


def get_ai_key_status_msg(has_key: bool):
    if has_key:
        text = (
            f"{format_header('Groq API Configuration', 'Key Verification & Status', 'CONNECTED')}\n"
            f"{format_kv('Status', 'Verified & Active', '✅')}\n"
            f"{format_kv('Scope', 'Shared across AI & Crypto Bots', '🔒')}\n\n"
            f"<b>Key Operations:</b>\n"
            f"  ▫️ Update key: <code>/setkey gsk_new_key</code>\n"
            f"  ▫️ Disconnect key: <code>/delkey</code>"
        )
        return text, InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")]])

    text = (
        f"{format_header('Groq API Configuration', 'Key Verification & Status', 'DISCONNECTED')}\n"
        f"No personal API key is currently linked to your profile.\n\n"
        f"<b>Get started in 2 minutes:</b>\n"
        f"  1. Go to <b>console.groq.com</b> → API Keys\n"
        f"  2. Generate a free high-speed API key\n"
        f"  3. Link it right here using:\n"
        f"     <code>/setkey gsk_your_api_key</code>"
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🌐 Get Free Groq API Key", url="https://console.groq.com")],
            [InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")],
        ]
    )
    return text, kb


def get_ai_key_set_success_msg():
    text = format_alert(
        "Groq API Key Verified!",
        "Your private API key has been securely linked and validated with high-speed inference clusters.\n\nYou now have full access to all AI commands via <code>/zenith [question]</code>!",
        "SUCCESS",
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")]])
    return text, kb


def get_ai_key_deleted_msg():
    text = format_alert(
        "API Key Disconnected", "Your private Groq API key has been removed from our encrypted store.", "INFO"
    )
    return text, InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")]])


def get_activate_help_msg() -> str:
    return get_activate_help()


def get_activate_help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💎 Unlock Pro Membership", url=f"tg://user?id={ADMIN_USER_ID}")],
            [InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")],
        ]
    )


# Feature help messages with interactive quick-action triggers
def get_feature_help_msg(feature: str, is_pro: bool = False) -> tuple:
    messages = {
        "research": (
            f"{format_header('Deep Research Engine', 'Multi-Source Investigative Synthesis', 'PRO' if is_pro else 'LOCKED')}\n"
            f"Performs comprehensive multi-pass web sweeps and synthesizes authoritative reports.\n\n"
            f"<b>Command Syntax:</b>\n<code>/research [TOPIC]</code>\n\n"
            f"Or select an interactive sample below to execute immediately:\n"
            + (
                "\n<i>⚡ Pro Active — Full investigative pipeline unlocked.</i>"
                if is_pro
                else "\n<i>🔒 Pro Membership required to run deep research.</i>"
            )
        ),
        "summarize": (
            f"{format_header('Precision Summarizer', 'Condense Documents & Links', 'ACTIVE')}\n"
            f"Extracts core takeaways, executive summaries, and action items from lengthy texts or YouTube videos.\n\n"
            f"<b>Command Syntax:</b>\n<code>/summarize [TEXT]</code> (or reply to any message)\n\n"
            f"Or test with our pre-loaded samples right now:\n"
            + (f"\n<i>⚡ Daily Allowance: Unlimited (BYOK)</i>")
        ),
        "code": (
            f"{format_header('Code Architect', 'Principal Software Generation & Debugging', 'PRO' if is_pro else 'LOCKED')}\n"
            f"Generates production-grade, modular, clean code in any language with detailed architecture notes.\n\n"
            f"<b>Command Syntax:</b>\n<code>/code [DESCRIPTION]</code>\n\n"
            f"Or trigger an instant architectural build below:\n"
            + (
                "\n<i>⚡ Pro Active — Full code generation unlocked.</i>"
                if is_pro
                else "\n<i>🔒 Pro Membership required to run code architect.</i>"
            )
        ),
        "imagine": (
            f"{format_header('Visual Prompt Crafter', 'Optimized AI Art Engineering', 'PRO' if is_pro else 'LOCKED')}\n"
            f"Designs rich, lighting-aware, high-precision prompts for Midjourney v6, DALL-E 3, and Stable Diffusion.\n\n"
            f"<b>Command Syntax:</b>\n<code>/imagine [DESCRIPTION]</code>\n\n"
            f"Or test with our visual concept templates below:\n"
            + (
                "\n<i>⚡ Pro Active — Full visual engineering unlocked.</i>"
                if is_pro
                else "\n<i>🔒 Pro Membership required to run visual prompt crafter.</i>"
            )
        ),
    }
    message = messages.get(feature, "Feature documentation unavailable.")

    rows = []
    if feature == "research":
        rows = [
            [InlineKeyboardButton("💡 Quick Run: AI Trends 2026", callback_data="ai_quick_res_aitrends")],
            [InlineKeyboardButton("💡 Quick Run: Quantum Computing Moats", callback_data="ai_quick_res_quantum")],
            [InlineKeyboardButton("💡 Quick Run: DeFi Security Auditing", callback_data="ai_quick_res_defi")],
        ]
    elif feature == "summarize":
        rows = [
            [InlineKeyboardButton("💡 Quick Run: Technical Whitepaper", callback_data="ai_quick_sum_whitepaper")],
            [InlineKeyboardButton("💡 Quick Run: Earnings Call Summary", callback_data="ai_quick_sum_earnings")],
        ]
    elif feature == "code":
        rows = [
            [InlineKeyboardButton("💡 Quick Run: FastAPI Auth with JWT", callback_data="ai_quick_code_fastapi")],
            [InlineKeyboardButton("💡 Quick Run: React Data Table Hooks", callback_data="ai_quick_code_react")],
            [InlineKeyboardButton("💡 Quick Run: Telegram Bot Architecture", callback_data="ai_quick_code_tgbot")],
        ]
    elif feature == "imagine":
        rows = [
            [InlineKeyboardButton("💡 Quick Run: Cyberpunk Neo-Tokyo Rain", callback_data="ai_quick_img_cyberpunk")],
            [InlineKeyboardButton("💡 Quick Run: Deep Space Nebula Horizon", callback_data="ai_quick_img_nebula")],
            [InlineKeyboardButton("💡 Quick Run: Minimalist Luxury Watch UI", callback_data="ai_quick_img_watch")],
        ]

    rows.append([InlineKeyboardButton("« Back to Dashboard", callback_data="ai_main_menu")])
    return message, InlineKeyboardMarkup(rows)


def get_pro_feature_msg(feature: str) -> tuple:
    message = pro_feature_locked_msg(feature)
    keyboard = pro_upgrade_keyboard(back_data="ai_main_menu")
    return message, keyboard


def get_limit_reached_msg(feature: str, current: int, limit: int) -> str:
    return format_alert(
        f"Limit Exceeded: {feature}",
        f"You have utilized <code>{current} / {limit}</code> requests for today.\nQuotas refresh automatically at midnight UTC.\n\nUpgrade to Zenith Pro for 12x higher limits and unlimited access.",
        "WARNING",
    )


def get_research_help() -> str:
    return (
        f"{format_header('Research Command', 'Syntax & Examples', 'HELP')}\n"
        f"<b>Format:</b> <code>/research [TOPIC]</code>\n\n"
        f"<b>Examples:</b>\n"
        f"  ▫️ <code>/research AI regulation frameworks in Europe 2026</code>\n"
        f"  ▫️ <code>/research high-frequency trading latency optimization</code>\n"
        f"  ▫️ <code>/research solid-state battery commercialization timeline</code>\n\n"
        f"<i>Tip: Provide clear constraints for deeper investigative synthesis.</i>"
    )


def get_code_help() -> str:
    return (
        f"{format_header('Code Generator Command', 'Syntax & Examples', 'HELP')}\n"
        f"<b>Format:</b> <code>/code [DESCRIPTION]</code>\n\n"
        f"<b>Examples:</b>\n"
        f"  ▫️ <code>/code Python FastAPI REST endpoint with rate limiting</code>\n"
        f"  ▫️ <code>/code React hook for WebSocket reconnection handling</code>\n"
        f"  ▫️ <code>/code Bash script to automate Docker container backups</code>\n\n"
        f"<i>Tip: Specify language, framework, and edge cases needed.</i>"
    )


def get_summarize_help() -> str:
    return (
        f"{format_header('Summarize Command', 'Syntax & Usage', 'HELP')}\n"
        f"<b>Two convenient ways to use:</b>\n"
        f"  1. Direct text: <code>/summarize [long article text here]</code>\n"
        f"  2. Reply to any message or document with: <code>/summarize</code>\n\n"
        f"<i>Condenses complex material into scannable executive bullet points.</i>"
    )


def get_imagine_help() -> str:
    return (
        f"{format_header('Imagine Command', 'Visual Prompt Engineering', 'HELP')}\n"
        f"<b>Format:</b> <code>/imagine [DESCRIPTION]</code>\n\n"
        f"<b>Examples:</b>\n"
        f"  ▫️ <code>/imagine cyberpunk street at twilight, neon reflections, 8k</code>\n"
        f"  ▫️ <code>/imagine minimalist architectural villa overlooking ocean, golden hour</code>\n"
        f"  ▫️ <code>/imagine geometric luxury brand emblem for AI robotics firm</code>\n\n"
        f"<i>Generates studio-grade prompts optimized for Midjourney v6 and DALL-E 3.</i>"
    )


def get_summarize_limit_reached() -> str:
    return format_alert(
        "Daily Limit Reached",
        "You have utilized your 1 free summary for today.\n\nUpgrade to Zenith Pro for unlimited summarization of long documents, articles, and video transcripts.\nUse <code>/activate YOUR-KEY</code> to upgrade.",
        "PRO",
    )


def get_persona_help() -> str:
    items = [f"<b>{v['icon']} {k}</b> — {v['name']}" for k, v in PERSONAS.items()]
    return (
        f"{format_header('AI Personas Registry', 'Available Neural Profiles', 'COMMAND')}\n"
        f"{format_card('Supported Profiles', items, '🎭')}\n\n"
        f"<b>Usage:</b> <code>/persona [name]</code>\n"
        f"<b>Example:</b> <code>/persona coder</code>"
    )


def get_persona_locked() -> str:
    return format_alert(
        "Persona Restricted",
        "Switching away from the Default assistant requires a Pro subscription.\nUse <code>/activate YOUR-KEY</code> to unlock all 6 personas.",
        "PRO",
    )


def get_persona_unknown(valid: str) -> str:
    return format_alert(
        "Invalid Persona Identifier",
        f"The requested persona does not exist.\n\n<b>Valid profiles:</b> <code>{valid}</code>\n\nExample: <code>/persona coder</code>",
        "WARNING",
    )


def get_persona_already_using(name: str) -> str:
    return format_alert(
        "Already Active", f"Your neural assistant is currently operating with the <b>{name}</b> profile.", "INFO"
    )


def get_code_no_query() -> str:
    return get_code_help()


def get_imagine_no_query() -> str:
    return get_imagine_help()


def get_key_required_msg() -> str:
    return (
        "🔐 <b>Groq API Key Required</b>\n\n"
        "You are using Zenith in <b>BYOK (Bring Your Own Key)</b> mode. "
        "This allows for unlimited usage without daily limits!\n\n"
        "Status: ❌ <b>Not configured</b>\n\n"
        "To unlock all features, please set your personal Groq API key using:\n"
        "<code>/setkey [your_key]</code>\n\n"
        "<i>Get your free key at <a href='https://console.groq.com'>console.groq.com</a></i>"
    )
