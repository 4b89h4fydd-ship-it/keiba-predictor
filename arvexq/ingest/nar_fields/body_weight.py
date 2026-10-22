"""NAR official body weight; retain published inline and fallback observations."""
import re

from arvexq.ingest.nar_fields.body_weight_change import (
    from_separate_column, from_next_cell,
)


def parse_weight_cell(value):
    match = re.search(
        r"(?<!\d)(\d{3})(?:\s*(?:kg)?)?(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?(?!\d)",
        value, re.I,
    )
    if not match:
        return None, None
    weight = int(match.group(1))
    if not 250 <= weight <= 800:
        return None, None
    change = int(match.group(2)) if match.group(2) is not None else None
    return weight, change


def extract(values, row_text, weight_index, change_index):
    weight = change = None
    if 0 <= weight_index < len(values):
        weight, change = parse_weight_cell(values[weight_index])
        if weight and change is None:
            change = from_separate_column(values, change_index)

    if not weight:
        match = re.search(r"(?<!\d)(\d{3})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]", row_text, re.I)
        if match:
            observed = int(match.group(1))
            if 250 <= observed <= 800:
                weight, change = observed, int(match.group(2))

    if not weight:
        for index, value in enumerate(values[:24]):
            if not re.fullmatch(r"\d{3}", value):
                continue
            observed = int(value)
            if not 250 <= observed <= 800:
                continue
            weight = observed
            change = from_next_cell(values, index)
            break
    return weight, change
