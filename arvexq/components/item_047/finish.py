"""47: Observed finishing position; 0 means unavailable."""
import re

def extract_finish(text):
    m=re.search(r"(?<!\d)(\d{1,2})\s*着(?!\d)",text or "")
    return int(m.group(1)) if m else 0
