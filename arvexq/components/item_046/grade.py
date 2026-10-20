"""46: Explicit official class/grade indicator, not inferred from performance."""
import re

def extract_class(text):
    m=re.search(r"(?:Jpn\s*[ⅠⅡⅢI]{1,3}|G\s*[ⅠⅡⅢI]{1,3}|(?:1|2|3)勝クラス|新馬|未勝利|オープン)",text or "",re.I)
    return m.group(0).strip() if m else None
