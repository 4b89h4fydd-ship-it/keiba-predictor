"""JRA official race-card body weight from explicitly printed kilogram values.

Retains app._jra_parse_race's existing exact-match and missing-value semantics.
"""
import re


def extract(info_text: str) -> int:
    full = re.search(r"(\d{3})\s*kg\s*[（(]\s*([+\-]?\d+)\s*[）)]", info_text)
    if full:
        try:
            return int(full.group(1))
        except (ValueError, TypeError):
            return 0
    match = re.search(r"(\d{3})\s*kg", info_text)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            pass
    return 0
