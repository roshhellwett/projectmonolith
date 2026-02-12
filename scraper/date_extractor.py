import re
from datetime import datetime

DATE_PATTERNS = [
    r"Date[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
    r"Dated[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
    r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})"
]

def extract_date(text: str):
    if not text:
        return None

    clean_text = " ".join(text.split()).strip()

    for pattern in DATE_PATTERNS:
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            # Capture numbers, normalize separators
            date_str = match.group(1) if "(" in pattern else match.group()
            normalized = date_str.replace("-", "/").replace(".", "/")
            
            try:
                dt = datetime.strptime(normalized, "%d/%m/%Y")
                # 🛡️ SYSTEM PROTECTION: Reject dates before 2024
                # This kills 'garbage' dates automatically.
                if 2024 <= dt.year <= 2027:
                    return dt
            except ValueError:
                continue
    return None