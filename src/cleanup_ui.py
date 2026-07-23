import re

with open('A:/projectmonolith/src/zenith_ai_bot/ui.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix get_model_selector_keyboard
text = re.sub(
    r'def get_model_selector_keyboard\(current_model: str, is_pro: bool = False\) -> InlineKeyboardMarkup:\s+rows = \[\]\s+for model_id, info in AVAILABLE_MODELS\.items\(\):\s+marker = .*\s+rows\.append\(\s+\[\s+InlineKeyboardButton\(\s+f"\{info\[\'icon\'\]\} \{info\[\'name\'\]\} \(\{info\[\'description\'\]\}\)\{marker\}",\s+callback_data=f"ai_set_model_\{model_id\}",\s+\)\s+\]\s+\)\s+if not is_pro:\s+rows\.append\(\[InlineKeyboardButton\("💎 Unlock All 70B & DeepSeek Models", url=f"tg://user\?id=\{ADMIN_USER_ID\}"\)\]\)',
    'def get_model_selector_keyboard(current_model: str) -> InlineKeyboardMarkup:\n    rows = []\n    for model_id, info in AVAILABLE_MODELS.items():\n        marker = " ✅" if model_id == current_model else ""\n        rows.append(\n            [\n                InlineKeyboardButton(\n                    f"{info[\'icon\']} {info[\'name\']} ({info[\'description\']}){marker}",\n                    callback_data=f"ai_set_model_{model_id}",\n                )\n            ]\n        )',
    text,
    flags=re.MULTILINE
)

# Fix get_persona_keyboard
text = re.sub(
    r'def get_persona_keyboard\(current: str, is_pro: bool = False\) -> InlineKeyboardMarkup:\s+available = PERSONAS if is_pro else \{"default": PERSONAS\["default"\]\}\s+rows = \[\]\s+for key, info in available\.items\(\):\s+marker = " ✅" if key == current else ""\s+rows\.append\(\[InlineKeyboardButton\(f"\{info\[\'icon\'\]\} \{info\[\'name\'\]\}\{marker\}", callback_data=f"ai_persona_\{key\}"\)\]\)\s+if not is_pro:\s+rows\.append\(\[InlineKeyboardButton\("💎 Unlock 6 Specialized AI Personas", url=f"tg://user\?id=\{ADMIN_USER_ID\}"\)\]\)',
    'def get_persona_keyboard(current: str) -> InlineKeyboardMarkup:\n    available = PERSONAS\n    rows = []\n    for key, info in available.items():\n        marker = " ✅" if key == current else ""\n        rows.append([InlineKeyboardButton(f"{info[\'icon\']} {info[\'name\']}{marker}", callback_data=f"ai_persona_{key}")])',
    text,
    flags=re.MULTILINE
)

# Remove get_status_msg, get_history_locked_msg, get_personas_locked_msg, get_activate_help
text = re.sub(r'def get_status_msg\(.*?\)\s*->\s*str:.*?(?=\n\n\w|def get_api_key_status_msg)', '', text, flags=re.DOTALL)
text = re.sub(r'def get_personas_locked_msg\(.*?\)\s*->\s*str:.*?(?=\n\ndef get_personas_select_msg)', '', text, flags=re.DOTALL)
text = re.sub(r'def get_history_locked_msg\(.*?\)\s*->\s*str:.*?(?=\n\ndef get_history_list_msg)', '', text, flags=re.DOTALL)
text = re.sub(r'def get_activate_help\(.*?\)\s*->\s*str:.*?(?=\n\ndef get_zenith_no_query_msg)', '', text, flags=re.DOTALL)

with open('A:/projectmonolith/src/zenith_ai_bot/ui.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("UI cleanup done.")
