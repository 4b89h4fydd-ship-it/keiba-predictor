"""Provider-neutral parsing of observed official payout tables.

This module owns only the factual table-to-row conversion.  It does not select
bet types, calculate returns, or change prediction output.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup

_log = logging.getLogger(__name__)


_ALIASES = {
    "単勝": "単勝", "複勝": "複勝",
    "枠連": "枠連", "枠複": "枠連", "枠連複": "枠連",
    # 枠連単 (frame exacta) is a real NAR pool listed on the official
    # payout tables of some tracks （川崎・船橋・金沢・大井・浦和）. It
    # must map to its own type: while it was unrecognised, its rows were
    # read as continuation rows of the preceding 馬連複 section and the
    # frame-exacta amount was stored as a second, phantom 馬連 payout
    # for the same combination (Kawasaki 2026-11-09 1R/4R et al.).
    "枠連単": "枠連単",
    "馬連": "馬連", "馬複": "馬連", "馬連複": "馬連",
    "ワイド": "ワイド",
    "馬単": "馬単", "馬連単": "馬単",
    "3連複": "3連複", "三連複": "3連複", "３連複": "3連複",
    "3連単": "3連単", "三連単": "3連単", "３連単": "3連単",
}
_LABEL_KEYS = sorted(_ALIASES, key=len, reverse=True)

# Combination arity per bet type: 単勝・複勝 are single numbers, 枠連・
# 馬連・馬単・ワイド are pairs, 3連複・3連単 are triples. An entry whose
# combination carries any other count of numbers is not a payout row for
# that type (the JRA text-fallback used to emit popularity numbers and
# neighbouring amounts as combinations; see _parse_refund_dl below).
_COMBINATION_ARITY = {
    "単勝": 1, "複勝": 1,
    "枠連": 2, "枠連単": 2, "馬連": 2, "馬単": 2, "ワイド": 2,
    "3連複": 3, "3連単": 3,
}


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")))


def _cell_lines(cell: Any) -> list[str]:
    copy = BeautifulSoup(str(cell), "html.parser")
    for br in copy.find_all("br"):
        br.replace_with("\n")
    values: list[str] = []
    for value in copy.get_text("\n").splitlines():
        value = _norm(value)
        if value:
            values.append(value)
    return values


def parse_payouts(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Parse official payout tables, including NAR line-break cells."""
    out: list[dict[str, Any]] = []
    positions: dict[tuple[str, str], int] = {}

    def add(kind: str, combo: str, amount: str) -> None:
        kind = _ALIASES.get(kind, kind)
        combo = _norm(combo)
        amount = _norm(amount)
        combo_match = re.fullmatch(r"\d+(?:[-→・]\d+){0,2}", combo)
        amount_match = re.fullmatch(r"([\d,]+)円?", amount)
        if not combo_match or not amount_match:
            return
        arity = _COMBINATION_ARITY.get(kind)
        if arity is not None and len(re.findall(r"\d+", combo)) != arity:
            return
        value = int(amount_match.group(1).replace(",", ""))
        # A (type, combination) pair can only ever pay ONE amount, so
        # deduplicate on the pair alone — the previous key also carried
        # the amount, which let the same combination be stored twice
        # whenever two different amounts were paired with it. A repeat
        # with the same amount is a no-op; a repeat with a different
        # amount means the page carried the pool twice (interim and
        # final tables), so the later, final value wins and the
        # conflict is logged rather than silently storing both rows.
        key = (kind, combo)
        if key in positions:
            kept = out[positions[key]]
            if kept["amount"] == value:
                return
            _log.warning(
                "payout amount conflict for %s %s: %s -> %s (kept final)",
                kind, combo, kept["amount"], value)
            kept["amount"] = value
            return
        positions[key] = len(out)
        out.append({"type": kind, "combination": combo, "amount": value})

    # JRA official result pages do not put payouts in a <table> at all:
    # they live in <div class="refund_area"> as <dl><dt>券種</dt><dd>
    # rows of <div class="line"><div class="num">組合せ</div><div
    # class="yen">金額円</div><div class="pop">人気</div></div>. Parse
    # that structure directly, pairing each combination with the amount
    # in its own line. (Before this, JRA pages fell through to the raw
    # text fallback at the bottom, which zipped independently collected
    # combination-shaped lines and amount tokens: popularity numbers
    # and neighbouring amounts landed in the combination field, e.g.
    # 複勝 "170" or ワイド "133", and ticket graders reading those
    # rows lost every multi-line payout type.)
    for dl in soup.find_all("dl"):
        dt = dl.find("dt")
        dd = dl.find("dd")
        if dt is None or dd is None:
            continue
        kind = _ALIASES.get(_norm(dt.get_text()))
        if kind is None:
            continue
        lines = dd.find_all(class_="line")
        for line in lines or [dd]:
            num_el = line.find(class_="num")
            yen_el = line.find(class_="yen")
            if num_el is None or yen_el is None:
                continue
            add(kind, num_el.get_text(), yen_el.get_text())

    for table in soup.find_all("table"):
        current = ""
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"], recursive=False)
            if not cells:
                continue
            cell_lines = [_cell_lines(cell) for cell in cells]
            flat = [value for group in cell_lines for value in group]
            label_i = None
            label_raw = ""
            for index, group in enumerate(cell_lines):
                for value in group:
                    hit = next((key for key in _LABEL_KEYS if _norm(value) == _norm(key)), None)
                    if hit:
                        label_i = index
                        label_raw = hit
                        break
                if label_i is not None:
                    break
            if label_i is not None:
                current = _ALIASES[label_raw]
                payload = [value for group in cell_lines[label_i + 1:] for value in group]
            elif current:
                # A row with no recognised label is a continuation row
                # of the current pool only when it OPENS with a
                # combination or an amount (multi-row pools list their
                # label once, with rowspan). A row that opens with any
                # other text opens a section this parser does not know:
                # attributing its rows to the previous pool is how the
                # NAR 枠連単 row was stored as a phantom second 馬連
                # payout. Close the section and skip the row instead.
                first = _norm(cell_lines[0][0]) if cell_lines and cell_lines[0] else ""
                if (first
                        and not re.fullmatch(r"\d+(?:[-→・]\d+){0,2}", first)
                        and not re.fullmatch(r"[\d,]+円", first)):
                    current = ""
                    continue
                payload = flat
            else:
                continue

            combos = [value for value in payload if re.fullmatch(r"\d+(?:[-→・]\d+){0,2}", _norm(value))]
            amounts = [value for value in payload if re.fullmatch(r"[\d,]+円", _norm(value))]
            # Some providers (netkeiba's Payout_Detail_Table) put each
            # number of a combination on its own line inside the
            # combination cell: a 馬連 cell reads "7\n14" for the single
            # combination 7-14, a ワイド cell reads six numbers for its
            # three combinations. When the number-line count is exactly
            # arity x amount count, regroup the single numbers into
            # combinations; pairing each number with the next amount
            # instead stored the first number alone as the combination
            # (netkeiba-sourced JRA payouts, repaired 2026-11-08).
            arity = _COMBINATION_ARITY.get(current)
            if (arity and arity > 1 and amounts
                    and len(combos) == arity * len(amounts)
                    and all(re.fullmatch(r"\d+", _norm(c)) for c in combos)):
                combos = ["-".join(combos[i:i + arity])
                          for i in range(0, len(combos), arity)]
            for combo, amount in zip(combos, amounts):
                add(current, combo, amount)

    if not out:
        raw = unicodedata.normalize("NFKC", soup.get_text("\n"))
        raw = re.sub(r"[ \t]+", "", raw)
        labels = "|".join(re.escape(key) for key in _LABEL_KEYS)
        chunks = list(re.finditer(rf"(?m)^({labels})\s*$", raw))
        for index, match in enumerate(chunks):
            kind = _ALIASES.get(_norm(match.group(1)), _norm(match.group(1)))
            segment = raw[match.end():chunks[index + 1].start() if index + 1 < len(chunks) else match.end() + 500]
            combos = re.findall(r"(?m)^(?:\s*)(\d+(?:[-→・]\d+){0,2})(?:\s*)$", segment)
            amounts = re.findall(r"([\d,]+)\s*円", segment)
            for combo, amount in zip(combos, amounts):
                add(kind, combo, amount + "円")
    return out


__all__ = ["parse_payouts"]
