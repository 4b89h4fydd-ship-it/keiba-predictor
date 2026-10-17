"""Extract and normalize only carried_weight from a provider row. Missing values remain absent."""
import re
from .dom import horse_info, text

def extract(row):
    info = horse_info(row)
    for node in (info.select_one("dd.Jockey") if info is not None else None, row.select_one("td.Jockey")):
        match = re.search(r"(\d{2}(?:\.\d)?)\s*$", text(node))
        if match:
            value = float(match.group(1))
            if value: return value
    return 0.0


def _safe_carried_weight_value(value, body_weight=None):
    if value in (None,""):return None
    try:x=float(re.sub(r"[^0-9.+-]","",str(value)))
    except Exception:return None
    # Strict mode: 斤量 is already a kg value. Do not auto-divide 3-digit values,
    # because a horse body weight such as 500 can otherwise become a false 50kg.
    if 35<=x<=80:return round(x,1)
    return None
