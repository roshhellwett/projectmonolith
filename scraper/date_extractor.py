import re
import unicodedata
from datetime import datetime
from core.config import TARGET_YEAR

ANCHOR_PATTERN = r"(?i)(?:dated?|no|kolkata|issue|on)\s*[:\-]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"
FALLBACK_PATTERN = r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"

def extract_date(text: str):
    if not text:
        return None
    
    clean_text = unicodedata.normalize("NFKD", text)
    clean_text = " ".join(clean_text.split()).strip()

    match = re.search(ANCHOR_PATTERN, clean_text)
    if not match:
        match = re.search(FALLBACK_PATTERN, clean_text)
        
    if match:
        date_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
        normalized = date_str.replace("-", "/").replace(".", "/")
        normalized = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", normalized, flags=re.I)
        
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d/%b/%Y"):
            try:
                dt = datetime.strptime(normalized, fmt)
                if dt.year == TARGET_YEAR:
                    return dt
            except ValueError:
                continue
                
    return None