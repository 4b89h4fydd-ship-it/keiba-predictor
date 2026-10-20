"""Observed JRA race number parsing; no inferred race identity."""
import re

def _jra_race_no_from_cname(cname:str)->int:
    m=re.search(r"pw01dde(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "")
    race_no=int(m.group(1)) if m else 0
    return race_no if 1 <= race_no <= 12 else 0
