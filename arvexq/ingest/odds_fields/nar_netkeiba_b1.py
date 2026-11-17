"""Observed netkeiba NAR 単勝・複勝 (type=b1) desktop odds page parsing.

The b1 page carries two tables with identical headers
(枠 | 馬番 | 印 | 選択 | 馬名 | オッズ): one is the win table (a
bare number per runner), the other is the place table (an observed
range "low - high" per runner). Neither table has a 複勝 header, so
a table is classified by its cells — a table whose odds cells hold
range separators is the place table (win cells never contain one),
and a bare number inside a place table is a low == high range.
A range's first number is never read as a win odd. Place ranges
are observed values only; nothing is derived from the win odds.
"""
import re

from bs4 import BeautifulSoup

from arvexq.ingest.field_normalization import _clean
from arvexq.ingest.place_odds import place_odds

_RANGE_SEP = re.compile(r"[-～〜~]")


def _parse_nar_netkeiba_b1_html(html: str) -> dict:
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = []
        header_idx = -1
        for ri, tr in enumerate(rows[:4]):
            vals = [_clean(c.get_text(" ", strip=True)).replace(" ", "")
                    for c in tr.find_all(["th", "td"])]
            if any("馬番" in x for x in vals) and any("オッズ" in x for x in vals):
                header = vals
                header_idx = ri
                break
        if not header:
            continue

        def idxpart(part):
            for i, x in enumerate(header):
                if part in x:
                    return i
            return -1

        ino = idxpart("馬番")
        iodd = idxpart("オッズ")
        if ino < 0 or iodd < 0:
            continue
        entries = []
        for tr in rows[header_idx + 1:]:
            vals = [_clean(c.get_text(" ", strip=True))
                    for c in tr.find_all(["th", "td"])]
            if ino >= len(vals) or iodd >= len(vals):
                continue
            mn = re.fullmatch(r"\D*(\d{1,2})\D*", vals[ino])
            if not mn:
                continue
            no = int(mn.group(1))
            if no <= 0 or no > 30:
                continue
            entries.append((no, vals[iodd].replace(",", "")))
        if not entries:
            continue
        is_place_table = any(_RANGE_SEP.search(cell) for _no, cell in entries)
        for no, cell in entries:
            if is_place_table:
                if _RANGE_SEP.search(cell):
                    po = place_odds(cell)
                else:
                    single = place_odds(cell)
                    po = single if single and single["placeOddsLow"] == single["placeOddsHigh"] else None
                if po:
                    out.setdefault(no, {}).update(po)
            else:
                if _RANGE_SEP.search(cell):
                    continue
                mo = re.fullmatch(r"\d+(?:\.\d+)?", cell)
                if mo:
                    odd = float(mo.group())
                    if odd > 0:
                        out.setdefault(no, {})["winOdds"] = odd
    return out
