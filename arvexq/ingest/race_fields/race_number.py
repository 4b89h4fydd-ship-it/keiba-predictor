"""JRA official race-number extraction (200-item responsibility #11).

The source token is mandatory; do not borrow an index from a different race.
"""
import re


def extract(cname: str) -> int:
    match = re.search(r"pw01dde(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/", cname or "")
    return int(match.group(1)) if match else 0
