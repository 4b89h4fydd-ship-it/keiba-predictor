"""49: JRA margin matched only to an explicit 3F/rival section."""
import re

def extract_margin_seconds(text, finish):
    m=re.search(r"3F\s*\d{2}(?:\.\d)?\s+[^()]+?\s*\(([+-]?\d+(?:\.\d+)?)\)",text or "")
    value=float(m.group(1)) if m else None
    if value is not None and finish==1:return 0.0
    return value if value is not None and value>=0 else None
