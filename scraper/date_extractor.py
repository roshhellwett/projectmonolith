import re
from datetime import datetime


DATE_PATTERNS = [
    r"\d{2}-\d{2}-\d{4}",  # DD-MM-YYYY
    r"\d{2}/\d{2}/\d{4}",  # DD/MM/YYYY
    r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
]


def extract_date(text: str):

    if not text:
        return None

    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            date_str = match.group()
            # Try multiple formats
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

    return None