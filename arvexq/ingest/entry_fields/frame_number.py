"""frame_number extraction, with no network or other field dependencies."""
import re
from arvexq.components.item_040.field_normalization import _clean
_NK_WAKU_RE = re.compile(r"^Waku(\d)$")

def _nk_row_frame(tr) -> int:
    for td in tr.find_all("td"):
        for cls in (td.get("class") or []):
            m = _NK_WAKU_RE.match(str(cls))
            if m and 1 <= int(m.group(1)) <= 8:
                return int(m.group(1))
    return 0

extract = _nk_row_frame
