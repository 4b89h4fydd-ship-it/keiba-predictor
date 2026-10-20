"""51: Observed last 3F when an explicit 3F value is supplied."""
import re

def extract_last3f_seconds(text):
    m=re.search(r"3F\s*(\d{2}(?:\.\d)?)",text or "")
    return float(m.group(1)) if m else None
