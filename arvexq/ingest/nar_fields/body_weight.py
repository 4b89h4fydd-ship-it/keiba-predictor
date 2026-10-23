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


def extract(values, row_text, weight_index, change_index, *, banei=False):
    # Banei horses may weigh over 1,000 kg; read only the labelled body
    # weight column to avoid treating the separate 600 kg load as body mass.
    if banei:
        if not 0 <= weight_index < len(values):
            return None, None
        cell = str(values[weight_index]).strip()
        match = re.fullmatch(
            r"(\d{3,4})(?:\s*kg)?(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",
            cell, re.I,
        )
        if not match:
            return None, None
        value = int(match.group(1))
        if not 700 <= value <= 1500:
            return None, None
        change = int(match.group(2)) if match.group(2) is not None else from_separate_column(values, change_index)
        return value, change
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
