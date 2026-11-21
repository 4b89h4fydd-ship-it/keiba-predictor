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


def extract_from_texts(texts) -> tuple:
    """(weight, change) scanning several cell texts in order.

    Added 2026-11-21 (audit B8): the card parser read the weight
    from the horse's info cell only, so a layout carrying it in a
    dedicated cell (or the profile cell) silently dropped every
    weight. Two passes mirror extract()'s own precedence — first
    any text carrying the full "NNNkg (±n)" form, then any text
    with a bare "NNNkg". The patterns cannot match the carried
    weight (a two-digit decimal like 55.0kg, never followed by a
    parenthesised change), and a text with no kilogram value
    contributes nothing. Returns (0, None) when no text carries
    a weight."""
    usable = [t for t in (texts or []) if isinstance(t, str) and t]
    for text in usable:
        full = re.search(r"(\d{3})\s*kg\s*[（(]\s*([+\-]?\d+)\s*[）)]",
                         text)
        if full:
            try:
                return int(full.group(1)), int(full.group(2))
            except (ValueError, TypeError):
                continue
    for text in usable:
        weight = extract(text)
        if weight:
            return weight, None
    return 0, None
