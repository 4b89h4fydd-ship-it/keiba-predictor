"""42: Historical race date (JRA official card)."""
import re

def extract_date(text):
    m=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",text or "")
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None
