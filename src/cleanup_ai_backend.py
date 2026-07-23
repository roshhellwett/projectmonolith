import re

with open('A:/projectmonolith/src/run_ai_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_mode = False
for i, line in enumerate(lines):
    # Remove imports
    if 'from zenith_crypto_bot.repository import CryptoSubscriptionRepo' in line:
        continue
    if 'check_ai_rate_limit,' in line:
        line = line.replace('check_ai_rate_limit, ', '')
    
    # Remove cmd_activate completely
    if line.startswith('async def cmd_activate('):
        skip_mode = True
        continue
    if skip_mode:
        if line.startswith('async def '):
            skip_mode = False
        else:
            continue
            
    # Remove activate handler
    if 'CommandHandler("activate", cmd_activate)' in line:
        continue
        
    # Remove CryptoSubscriptionRepo calls and is_pro assignments
    if 'CryptoSubscriptionRepo.' in line:
        continue
    if re.match(r'^\s*is_pro\s*=\s*', line):
        continue
    if re.match(r'^\s*days_left\s*=\s*', line):
        continue
    if re.match(r'^\s*days\s*=\s*', line):
        continue
        
    # Replace usages of is_pro
    if 'get_ai_dashboard(is_pro, persona, usage, selected_model)' in line:
        line = line.replace('is_pro, ', '')
    if 'get_help_msg(is_pro=tier.is_pro)' in line:
        line = line.replace('is_pro=tier.is_pro', '')
    if 'get_feature_help_msg(feature, is_pro)' in line:
        line = line.replace('is_pro', '')
    if 'get_model_selector_keyboard(current_model, is_pro=is_pro)' in line:
        line = line.replace(', is_pro=is_pro', '')
    if 'get_model_selector_keyboard(model_id, is_pro=True)' in line:
        line = line.replace(', is_pro=True', '')
    if 'get_persona_keyboard(current, is_pro=True)' in line:
        line = line.replace(', is_pro=True', '')
    
    # In ai_worker_process queue pop
    if 'is_pro, persona, history = task_item' in line:
        line = line.replace('is_pro, ', '')
        
    # In task_queue.put_nowait
    if '(update, context, placeholder, text, history_text, is_pro, persona, conversation_history)' in line:
        line = line.replace('is_pro, ', '')
        
    # Remove rate limit check block
    if 'allowed, reason = await check_ai_rate_limit' in line:
        # We also need to remove the next two lines:
        # if not allowed:
        #     return await msg.reply_text(reason, parse_mode="HTML")
        pass # Handle this by a regex later or just rely on manual deletion
        
    new_lines.append(line)

text = ''.join(new_lines)

# Fix rate limit block
text = re.sub(
    r'\s*allowed, reason = await check_ai_rate_limit\(user_id, is_pro\)\s*if not allowed:\s*return await msg\.reply_text\(reason, parse_mode="HTML"\)',
    '',
    text
)

# Remove any stray "if is_pro:" or "if not tier.is_pro:" and unindent?
# Actually wait, in cmd_help:
# if not tier.is_pro:
#     text += "\n\n<i>Need assistance? Contact @roshhellwett for license activation.</i>"
text = re.sub(
    r'\s*if not tier\.is_pro:\s*text \+= "\\n\\n<i>Need assistance\? Contact @roshhellwett for license activation\.</i>"',
    '',
    text
)

text = re.sub(
    r'\s*if not getattr\(tier, "is_pro", False\):\s*text \+= "\\n\\n<i>Need assistance\? Contact @roshhellwett for license activation\.</i>"',
    '',
    text
)

# In cmd_start:
text = re.sub(
    r'\s*text = get_status_msg\(is_pro, days\)\s*await update\.message\.reply_text\(text, parse_mode="HTML"\)',
    '',
    text
)
# Wait, cmd_start had a status message call? No, that was in the menu handler for ai_status.
# The menu handler for ai_status is now dead, so we can remove the whole ai_status block!
text = re.sub(
    r'\s*elif query\.data == "ai_status":.*?(?=\s*elif query\.data ==)',
    '',
    text,
    flags=re.DOTALL
)

# Replace get_usage_card(usage, is_pro)
text = text.replace('get_usage_card(usage, is_pro)', 'get_usage_card(usage)')

# Replace is_pro in run_ai_bot where we missed
text = text.replace('is_pro=is_pro', '')

with open('A:/projectmonolith/src/run_ai_bot.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("AI bot backend pro cleanup done.")
