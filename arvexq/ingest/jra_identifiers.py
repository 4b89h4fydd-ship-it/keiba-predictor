"""Parse JRA source identifiers without application state."""
import re
from datetime import date

def _jra_date_from_cname(cname:str)->str:
    m=re.search(r"(20\d{6})/[0-9A-Fa-f]{2}$",cname or "")
    if not m:return ""
    x=m.group(1)
    try:
        return date.fromisoformat(f"{x[:4]}-{x[4:6]}-{x[6:8]}").isoformat()
    except ValueError:
        return ""

def _jra_race_no_from_cname(cname:str)->int:
    m=re.search(r"pw01dde(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "")
    return int(m.group(1)) if m else 0

