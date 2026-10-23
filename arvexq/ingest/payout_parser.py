"""Provider-neutral parsing of observed official payout tables.

This module owns only the factual table-to-row conversion.  It does not select
bet types, calculate returns, or change prediction output.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup


_ALIASES = {
    "単勝": "単勝", "複勝": "複勝",
    "枠連": "枠連", "枠複": "枠連", "枠連複": "枠連",
    "馬連": "馬連", "馬複": "馬連", "馬連複": "馬連",
    "ワイド": "ワイド",
    "馬単": "馬単", "馬連単": "馬単",
    "3連複": "3連複", "三連複": "3連複", "３連複": "3連複",
    "3連単": "3連単", "三連単": "3連単", "３連単": "3連単",
}
_LABEL_KEYS = sorted(_ALIASES, key=len, reverse=True)


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
    seen: set[tuple[str, str, int]] = set()

    def add(kind: str, combo: str, amount: str) -> None:
        kind = _ALIASES.get(kind, kind)
        combo = _norm(combo)
        amount = _norm(amount)
        combo_match = re.fullmatch(r"\d+(?:[-→・]\d+){0,2}", combo)
        amount_match = re.fullmatch(r"([\d,]+)円?", amount)
        if not combo_match or not amount_match:
            return
        value = int(amount_match.group(1).replace(",", ""))
        key = (kind, combo, value)
        if key in seen:
            return
        seen.add(key)
        out.append({"type": kind, "combination": combo, "amount": value})

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
                payload = flat
            else:
                continue

            combos = [value for value in payload if re.fullmatch(r"\d+(?:[-→・]\d+){0,2}", _norm(value))]
            amounts = [value for value in payload if re.fullmatch(r"[\d,]+円", _norm(value))]
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
