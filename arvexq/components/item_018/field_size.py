"""#18 Count distinct, valid observed JRA race-card horse numbers.

Do not fail the whole card for a malformed source row; a duplicate race-card
row must not inflate the observed count. This does not certify the full roster.
"""
import math
import re


def extract(horses):
    observed = set()
    for horse in horses or ():
        if not isinstance(horse, dict):
            continue
        value = horse.get("horseNumber")
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            number = value
        elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
            number = int(value)
        elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,2}", value.strip()):
            number = int(value.strip())
        else:
            continue
        if 1 <= number <= 18:
            observed.add(number)
    return len(observed)
