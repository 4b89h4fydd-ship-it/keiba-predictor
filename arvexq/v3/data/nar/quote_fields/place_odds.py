"""NAR place_odds observed only, never estimated."""
from arvexq.v3.data.quote_facts import read_field as _read


def read(detail: dict) -> list[dict]:
    return _read(detail, "nar", "place_odds")
