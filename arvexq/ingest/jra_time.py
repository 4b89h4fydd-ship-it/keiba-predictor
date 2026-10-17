"""Independent JRA date and race clock parsing."""
import re

def _jra_iso_date(y:int,m:int,d:int)->str:
    return f"{y:04d}-{m:02d}-{d:02d}"

def _jra_parse_time_seconds(txt:str)->float:
    m=re.search(r"(?<!\d)(\d{1,2}):(\d{2}\.\d)(?!\d)",txt or "")
    if not m:return 0.0
    return int(m.group(1))*60+float(m.group(2))
