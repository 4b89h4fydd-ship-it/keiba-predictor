"""horse_number extraction, with no network or other field dependencies."""
import re
from arvexq.ingest.field_normalization import _clean
_NK_ODDS_ID_RE = re.compile(r"^odds-1_(\d{1,2})$")

def _nk_row_horse_no(tr, index: int | None = None) -> int:
    """netkeiba HorseList 行の馬番。

    現行DOMは馬番セルが無く、オッズ span の id (odds-1_01) と行順が馬番を持つ。
    旧DOMは td.Umaban に馬番があったため両対応にする。
    """
    o = tr.find("span", id=_NK_ODDS_ID_RE)
    if o is not None:
        m = _NK_ODDS_ID_RE.match(str(o.get("id") or ""))
        if m and int(m.group(1)) > 0:
            return int(m.group(1))
    um = tr.find("td", class_=re.compile(r"^Umaban"))
    if um is not None:
        m = re.search(r"\d{1,2}", _clean(um.get_text(" ", strip=True)))
        if m and int(m.group()) > 0:
            return int(m.group())
    if index is not None:
        return int(index) + 1
    return 0

extract = _nk_row_horse_no
