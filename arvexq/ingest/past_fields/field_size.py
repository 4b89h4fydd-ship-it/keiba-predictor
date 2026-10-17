"""54: Official historical number of runners."""
import re

def extract_field_size(text):
    m=re.search(r"(\d{1,2})\s*頭",text or "")
    return int(m.group(1)) if m else 0
