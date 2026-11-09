"""NAR official body-weight change extraction; never infer from prior weigh-ins."""
import re

# A career result string ("1-1-4-15") is a hyphenated tuple, never a
# weight change; a bare one must not be read as its leading number.
_RESULT_STRING = re.compile(r"^\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}$")
_COMBINED_RESULT = re.compile(
    r"^\s*([+\-]?\d{1,3})\s+(\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})(?:\s|$)")


def from_separate_column(values, index):
    if not 0 <= index < len(values):
        return None
    if _RESULT_STRING.match(values[index].strip()):
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


def leading_token_before_result(values, index):
    """Read the change published as the leading token of a cell that
    continues with a career result string ("+3 1-1-4-15"). A bare
    result string has no whitespace-separated leading token, so it
    never matches here."""
    if not 0 <= index < len(values):
        return None
    match = _COMBINED_RESULT.match(values[index])
    if not match:
        return None
    observed = int(match.group(1))
    return observed if -99 <= observed <= 99 else None
