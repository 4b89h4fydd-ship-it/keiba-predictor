"""NAR timestamp: standalone, read-only factual odds reader."""
from arvexq.v3.data.odds_facts import market_field as _read


def read(detail: dict):
    return _read(detail, "nar", "timestamp")
