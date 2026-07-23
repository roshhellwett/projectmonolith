import re

with open('A:/projectmonolith/src/run_ai_bot.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove Buy Pro button from cmd_help
text = re.sub(
    r'\s*buttons = \[\]\s*if not tier\.is_pro:\s*buttons\.append\(\[InlineKeyboardButton\("Buy Pro", url=f"tg://user\?id=\{ADMIN_USER_ID\}"\)\]\)\s*buttons\.append\(\[InlineKeyboardButton\("Back", callback_data="ai_main_menu"\)\]\)',
    '\n    buttons = [[InlineKeyboardButton("Back", callback_data="ai_main_menu")]]',
    text
)

# Remove ai_activate_help block completely
text = re.sub(
    r'\s*elif query\.data == "ai_activate_help":.*?(?=\s*elif query\.data in \("ai_research_help")',
    '',
    text,
    flags=re.DOTALL
)

# Remove old ai_research_help block completely
text = re.sub(
    r'\s*elif query\.data in \("ai_research_help", "ai_summarize_help", "ai_code_help", "ai_imagine_help"\):.*?(?=\s*elif query\.data == "ai_models":)',
    '',
    text,
    flags=re.DOTALL
)

with open('A:/projectmonolith/src/run_ai_bot.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Final cleanup done.")
