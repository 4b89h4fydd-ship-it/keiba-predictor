"""frame_number extraction, with no network or other field dependencies."""
import re
from arvexq.ingest.field_normalization import _clean
# Prefix match, not a whole-token exact match: a zero-padded or
# state-suffixed class token ("Waku01", "Waku1_on") is the same frame
# cell, and the old ^Waku(\d)$ read every such layout as frame 0 —
# one of the readings that let the 2026-11-28 garble through (all
# frames 0 while the numbers were permuted).
_NK_WAKU_RE = re.compile(r"^Waku0*(\d{1,2})(?:\D|$)")

def _nk_row_frame(tr) -> int:
    for td in tr.find_all("td"):
        for cls in (td.get("class") or []):
            m = _NK_WAKU_RE.match(str(cls))
            if m and 1 <= int(m.group(1)) <= 8:
                return int(m.group(1))
    return 0

extract = _nk_row_frame
