"""NAR official carried weight; independent from a horse's body mass."""
import re


def extract(values, index):
    if not 0 <= index < len(values):
        return None
    match = re.search(r"(?<!\d)(\d{2}(?:\.\d)?)(?!\d)", values[index])
    if match:
        try:
            observed = float(match.group(1))
            if 35 <= observed <= 80:
                return round(observed, 1)
        except (TypeError, ValueError):
            pass
    return None
