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
    lines = p.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # If line is lines.append(format_divider(...)) or lines.append(f"{format_divider(...)}")
        if re.fullmatch(r'lines\.append\(f?"?\{?format_divider\([^)]*\)\}?"?\)', stripped):
            continue
        # If line inside list is just format_divider(),
        if re.fullmatch(r"format_divider\([^)]*\),", stripped):
            continue
        # If line is just f"{format_divider()}\n\n" inside multiline tuple/string
        if re.fullmatch(r'f"\{format_divider\([^)]*\)\}\\n\\n"', stripped):
            # Replace with empty string or newline string keeping exact leading indentation
            leading = line[: len(line) - len(line.lstrip())]
            new_lines.append(f'{leading}""')
            continue
        if re.fullmatch(r'f"\{format_divider\([^)]*\)\}"', stripped):
            continue

        # Inline replacements within a line:
        # e.g. lines = ["<b>Title</b>", format_divider(), ""] -> lines = ["<b>Title</b>", ""]
        line = re.sub(r',\s*format_divider\([^)]*\),\s*""', r', ""', line)
        # e.g. f"<b>Title</b>\n{format_divider()}\n\n" inside a single line
        line = re.sub(r"\\n\{format_divider\([^)]*\)\}\\n\\n", r"\\n\\n", line)
        line = re.sub(r"\\n\{format_divider\([^)]*\)\}", r"", line)

        new_lines.append(line)

    text = "\n".join(new_lines) + "\n"
    # Clean up empty string artifacts: f"<b>Header</b>\n" followed by "" inside parens
    # Let ruff take care of formatting after
    p.write_text(text, encoding="utf-8")
    print(f"Cleaned {p}")
