"""NAR official body weight; retain published inline and fallback observations."""
import re

from arvexq.ingest.nar_fields.body_weight_change import (
    from_separate_column, from_next_cell, leading_token_before_result,
)

# DebaTableSmall publishes weight and change in one cell without
# parentheses ("482 3" / "482 -3"); the bracketed and standalone paths
# below all pass that shape by.
_PAIR_CELL = re.compile(r"^\s*(\d{3})\s*(?:kg)?\s+([+\-]?\d{1,3})\s*$", re.I)
_TRAILING_PAIR = re.compile(
    r"(?<!\d)(\d{3})\s*(?:kg)?\s+([+\-]?\d{1,3})\s*$", re.I)


def _valid_pair(weight, change):
    return 250 <= weight <= 800 and -99 <= change <= 99


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
    if change is None:
        pair = _TRAILING_PAIR.search(value)
        if pair and int(pair.group(1)) == weight:
            observed = int(pair.group(2))
            if -99 <= observed <= 99:
                change = observed
    return weight, change


def extract(values, row_text, weight_index, change_index):
    weight = change = None
    if 0 <= weight_index < len(values):
        weight, change = parse_weight_cell(values[weight_index])
        if weight and change is None:
            change = from_separate_column(values, change_index)
        if weight and change is None:
            change = leading_token_before_result(values, weight_index + 1)

    if not weight:
        match = re.search(r"(?<!\d)(\d{3})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]", row_text, re.I)
        if match:
            observed = int(match.group(1))
            if 250 <= observed <= 800:
                weight, change = observed, int(match.group(2))

    if not weight:
        # Unbracketed pair-cell fallback: also the only path that works
        # when the header row is one combined cell and the column
        # indices above do not resolve to the weight cell at all.
        for value in values[:24]:
            pair = _PAIR_CELL.match(value)
            if not pair:
                continue
            observed, observed_change = int(pair.group(1)), int(pair.group(2))
            if _valid_pair(observed, observed_change):
                weight, change = observed, observed_change
                break

    if not weight:
        for index, value in enumerate(values[:24]):
            if not re.fullmatch(r"\d{3}", value):
                continue
            observed = int(value)
            if not 250 <= observed <= 800:
                continue
            weight = observed
            change = from_next_cell(values, index)
            if change is None:
                change = leading_token_before_result(values, index + 1)
            break
    return weight, change
