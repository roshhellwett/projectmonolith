import re
from pathlib import Path

ui_files = [
    Path("src/zenith_crypto_bot/ui.py"),
    Path("src/zenith_group_bot/ui.py"),
    Path("src/zenith_support_bot/ui.py"),
    Path("src/zenith_admin_bot/ui.py"),
    Path("src/zenith_ai_bot/ui.py"),
]

for p in ui_files:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")

    # 1. f"{format_divider()}\n\n" or f"{format_divider('─', 24)}\n\n"
    text = re.sub(r'\s*f"\{format_divider\([^)]*\)\}\\n\\n"', r'\n        ""', text)

    # 2. f"\n{format_divider('─', 24)}" or f"\n{format_divider()}" inside f-string
    text = re.sub(r"\\n\{format_divider\([^)]*\)\}", "", text)

    # 3. standalone lines.append(f"{format_divider()}")
    text = re.sub(r'lines\.append\(f"\{format_divider\([^)]*\)\}"\)\n', "", text)

    # 4. format_divider(), inside list literals
    text = re.sub(r"^\s*format_divider\([^)]*\),\s*\n", "", text, flags=re.MULTILINE)

    # 5. lines = ["<b>Title</b>", format_divider(), ""] -> lines = ["<b>Title</b>", ""]
    text = re.sub(r'lines\s*=\s*\[([^,]+),\s*format_divider\([^)]*\),\s*""\]', r'lines = [\1, ""]', text)

    # 6. Any remaining f"{format_divider()}" or {format_divider()}
    text = re.sub(r"\{format_divider\([^)]*\)\}\\n\\n", r"\\n", text)
    text = re.sub(r"\{format_divider\([^)]*\)\}\\n", r"", text)
    text = re.sub(r'f"\{format_divider\([^)]*\)\}",?\n', "\n", text)

    # Clean up f"<b>Header</b>\n" followed by "" -> f"<b>Header</b>\n\n"
    text = re.sub(r'f"<b>([^<]+)</b>\\n"\s*""', r'f"<b>\1</b>\\n\\n"', text)
    text = re.sub(r'f"<b>([^<]+)</b>\\n"\s*\+\s*""', r'f"<b>\1</b>\\n\\n"', text)

    p.write_text(text, encoding="utf-8")
    print(f"Cleaned {p}")
