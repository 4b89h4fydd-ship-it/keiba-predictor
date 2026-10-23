"""NAR official body-weight change extraction; never infer from prior weigh-ins."""
import re


def from_separate_column(values, index):
    if not 0 <= index < len(values):
        return None
    match = re.search(r"([+\-]?\d{1,3})", values[index])
    if match:
        observed = int(match.group(1))
        if -99 <= observed <= 99:
            return observed
    return None


def from_next_cell(values, index):
    if index + 1 >= len(values):
        return None
    match = re.fullmatch(r"\s*([+\-]?\d{1,2})\s*", values[index + 1])
    return int(match.group(1)) if match else None
