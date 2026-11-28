"""horse_number extraction, with no network or other field dependencies."""
import re
from arvexq.ingest.field_normalization import _clean
_NK_ODDS_ID_RE = re.compile(r"^odds-1_(\d{1,2})$")

def _nk_row_horse_no(tr, index: int | None = None) -> int:
    """netkeiba HorseList 行の馬番。

    出馬表テーブル自体の馬番セル (td.Umaban) を正とし、オッズ span の
    id (odds-1_01) はセルが無いレイアウトでのみ補助に使う。span id は
    オッズ表示側の都合で並ぶため、レイアウトやページ状態がずれると
    馬番までずれる (2026-11-28 の番号化けの一因)。
    index引数は呼出互換のため保持するが、未観測の馬番を行順から作らない。
    """
    um = tr.find("td", class_=re.compile(r"^Umaban"))
    if um is not None:
        m = re.fullmatch(r"\d{1,2}", _clean(um.get_text(" ", strip=True)))
        if m and 1 <= int(m.group()) <= 18:
            return int(m.group())
    o = tr.find("span", id=_NK_ODDS_ID_RE)
    if o is not None:
        m = _NK_ODDS_ID_RE.match(str(o.get("id") or ""))
        if m and 1 <= int(m.group(1)) <= 18:
            return int(m.group(1))
    return 0

extract = _nk_row_horse_no
