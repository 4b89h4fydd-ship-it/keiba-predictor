"""#19 Observed official first-place purse in yen, no synthetic estimate."""
import re
def extract_first_prize(text):
    m=re.search(r"1着\s*([\d,.]+)",text or "")
    if not m:return 0
    try:return int(float(m.group(1).replace(",",""))*10000)
    except (TypeError,ValueError,OverflowError):return 0
