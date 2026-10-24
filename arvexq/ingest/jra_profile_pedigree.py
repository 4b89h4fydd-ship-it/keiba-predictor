"""Read observed lineage from the ALREADY USED JRA horse-profile HTML.

No independent crawler, guessed bloodline or unverified pedigree rating.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

_LABELS = {"父": "sire", "母": "dam", "母の父": "damSire"}
_INVALID = set(_LABELS) | {"性別", "馬齢", "調教師名", "馬主名", "生年月日", "生産牧場", "毛色", "産地"}


def parse_jra_profile_pedigree(html: str) -> dict[str, object]:
    if not isinstance(html, str) or not html.strip():
        return {}
    soup = BeautifulSoup(html, "html.parser")
    pedigree = {}
    # The official racehorse profile uses paired labels and values; only
    # adjacent profile values count, never free-text search / race result text.
    for label in soup.find_all(["th", "dt", "p", "span", "div"]):
        name = label.get_text(" ", strip=True)
        if name not in _LABELS or label.find(["table", "dl", "th", "dt"]):
            continue
        # Prefer the owning cell in layouts wrapping a label with a <p>.
        anchor = label
        if label.name in ("p", "span", "div") and label.parent is not None and label.parent.name in ("th", "dt"):
            anchor = label.parent
        target = anchor.find_next_sibling(["td", "dd", "div", "p", "span"])
        if target is None:
            continue
        value = target.get_text(" ", strip=True)
        if not value or len(value) > 90 or value in _INVALID:
            continue
        pedigree.setdefault(_LABELS[name], value)
    return {"pedigree": pedigree} if pedigree else {}
