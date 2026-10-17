"""Extract and normalize only trainer from a provider row. Missing values remain absent."""
import re
from .dom import horse_info, text

def extract(row):
    value = text(row.select_one("td.Trainer"))
    if value: return value
    info = horse_info(row)
    if info is not None:
        for selector in ("div.Horse05 a", "div.Horse05"):
            value = re.sub(r"^(栗東|美浦|地方|外国)\s*[・･]\s*", "", text(info.select_one(selector)))
            if value: return value
    return ""
