"""NAR missing: standalone, read-only factual odds reader."""
from arvexq.v3.data.odds_facts import missing_status as _read


def read(detail: dict):
    return _read(detail, "nar")
