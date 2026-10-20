"""42: Historical race date (JRA official card)."""
import re
from datetime import date

def extract_date(text):
    m=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",text or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)),int(m.group(2)),int(m.group(3))).isoformat()
    except ValueError:
        return None
