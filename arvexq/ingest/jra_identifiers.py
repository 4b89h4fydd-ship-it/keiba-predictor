"""Parse JRA source identifiers without application state."""
import re
from datetime import date

def _jra_date_from_cname(cname:str)->str:
    m=re.search(r"(20\d{6})/[0-9A-Fa-f]{2}$",cname or "")
    if not m:return ""
    x=m.group(1)
    iso=f"{x[:4]}-{x[4:6]}-{x[6:8]}"
    try:
        date.fromisoformat(iso)
    except ValueError:
        return ""
    return iso

from arvexq.components.item_011.race_number import _jra_race_no_from_cname
