import os
import re

src_dir = "A:/projectmonolith/src"

def replace_in_file(filepath, old, new):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

# 1. Update zenith_crypto_bot and run_crypto_bot to use CryptoSubscriptionRepo
for root, _, files in os.walk(src_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            # Crypto bot files
            if "zenith_crypto_bot" in filepath or "run_crypto_bot.py" in filepath or "run_ai_bot.py" in filepath:
                # Wait, run_ai_bot.py doesn't use it anymore, I cleaned it up in a previous turn.
                replace_in_file(filepath, "class CryptoSubscriptionRepo", "class CryptoSubscriptionRepo")
                replace_in_file(filepath, "CryptoSubscriptionRepo", "CryptoSubscriptionRepo")

# 2. Update zenith_group_bot and run_group_bot to use GroupCryptoSubscriptionRepo
for root, _, files in os.walk(src_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            if "zenith_group_bot" in filepath or "run_group_bot.py" in filepath:
                replace_in_file(filepath, "from core.subscription import CryptoSubscriptionRepo", "from zenith_group_bot.repository import GroupCryptoSubscriptionRepo")
                replace_in_file(filepath, "CryptoSubscriptionRepo", "GroupCryptoSubscriptionRepo")

# 3. Clean up core.subscription imports that just imported market service functions
for root, _, files in os.walk(src_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            if "zenith_group_bot" in filepath:
                # Fix the market imports if they were importing from core.subscription
                replace_in_file(filepath, "from core.subscription import", "from zenith_crypto_bot.market_service import")

