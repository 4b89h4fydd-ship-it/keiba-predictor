"""Extract the observed JRA/NAR affiliation independently of trainer identity.

Input: one netkeiba runner DOM row. Output: 美浦/栗東/地方/外国 or "".
Never infer affiliation from the trainer name or the race venue.
"""
import re
from .dom import horse_info, text

_PREFIX = re.compile(r"^(美浦|栗東|地方|外国)(?=\s*[・･]|\s|$)")

def extract(row):
    explicit = text(row.select_one("td.Affiliation"))
    if explicit in {"美浦", "栗東", "地方", "外国"}:
        return explicit
    info = horse_info(row)
    if info is None:
        return ""
    for selector in ("div.Horse05 a", "div.Horse05"):
        value = text(info.select_one(selector))
        match = _PREFIX.match(value)
        if match:
            return match.group(1)
    return ""
