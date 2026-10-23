"""JRA official race-date extraction (200-item responsibility #8).

No network access or inference: invalid calendar dates remain unknown.
"""
import re
from datetime import date


def extract(cname: str) -> str:
    match = re.search(r"(20\d{6})/[0-9A-Fa-f]{2}$", cname or "")
    if not match:
        return ""
    raw = match.group(1)
    try:
        return date.fromisoformat(f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}").isoformat()
    except ValueError:
        return ""
