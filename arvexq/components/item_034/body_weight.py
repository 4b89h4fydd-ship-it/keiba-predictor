"""Extract and normalize only body_weight from a provider row. Missing values remain absent."""
import re
from arvexq.ingest.entry_fields.dom import weight_text

def extract(row):
    match = re.search(r"(\d{3})\s*(?:[（(]\s*([+\-]?\d+)\s*[）)])?", weight_text(row))
    return int(match.group(1)) if match else None


def _safe_body_weight_value(value):
    if value in (None,""):return None
    try:
        m=re.search(r"(?<!\d)(\d{3})(?!\d)",str(value))
        x=int(m.group(1)) if m else int(round(float(value)))
    except Exception:return None
    return x if 250<=x<=800 else None
