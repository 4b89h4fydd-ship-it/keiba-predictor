"""Parse observed JRA official race-card single-win odds and popularity.

Independent fact-only parser. This preserves the existing source format and
return defaults from app._jra_parse_race; it does not forecast missing odds.
"""
import re


def parse_win_odds(info_text: str, horse_name: str) -> tuple[float, int]:
    """Return officially printed win odds and popularity or (0.0, 0)."""
    tail = info_text.split(horse_name, 1)[1] if horse_name in info_text else info_text
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*\((\d+)番人気\)", tail)
    if match:
        try:
            return float(match.group(1)), int(match.group(2))
        except (ValueError, TypeError):
            pass
    return 0.0, 0
