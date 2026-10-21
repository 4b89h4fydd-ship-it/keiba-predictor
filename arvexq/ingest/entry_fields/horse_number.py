"""horse_number extraction, with no network or other field dependencies."""
import re
from arvexq.components.item_040.field_normalization import _clean
_NK_ODDS_ID_RE = re.compile(r"^odds-1_(\d{1,2})$")

def _nk_row_horse_no(tr, index: int | None = None) -> int:
    """netkeiba HorseList 行の馬番。

    現行DOMは馬番セルが無く、オッズ span の id (odds-1_01) が馬番を持つ。
    旧DOMは td.Umaban に馬番があったため両対応にする。
    index引数は呼出互換のため保持するが、未観測の馬番を行順から作らない。
    """
    o = tr.find("span", id=_NK_ODDS_ID_RE)
    if o is not None:
        m = _NK_ODDS_ID_RE.match(str(o.get("id") or ""))
        if m and 1 <= int(m.group(1)) <= 18:
            return int(m.group(1))
    um = tr.find("td", class_=re.compile(r"^Umaban"))
    if um is not None:
        m = re.fullmatch(r"\d{1,2}", _clean(um.get_text(" ", strip=True)))
        if m and 1 <= int(m.group()) <= 18:
            return int(m.group())
    return 0

extract = _nk_row_horse_no
