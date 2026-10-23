"""NAR official carried weight; independent from a horse's body mass."""
import re


def extract(values, index, *, banei=False):
    if not 0 <= index < len(values):
        return None
    cell = str(cell).strip()
    if banei:
        # Only parse an explicit three-digit weight from the official column.
        match = re.fullmatch(r"(\\d{3})(?:\\.0)?\\s*(?:kg|㎏)?", cell, re.IGNORECASE)
        if not match:
            return None
        observed = int(match.group(1))
        return float(observed) if 400 <= observed <= 800 else None
    match = re.search(r"(?<!\d)(\d{2}(?:\.\d)?)(?!\d)", values[index])
    if match:
        try:
            observed = float(match.group(1))
            if 35 <= observed <= 80:
                return round(observed, 1)
        except (TypeError, ValueError):
            pass
    return None
