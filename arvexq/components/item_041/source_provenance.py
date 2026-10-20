"""Read-only collection of observed provider provenance for race-entry anomalies.

Never invent source labels, assert authority, or mutate original records.
The input records remain owned by JRA/NAR ingestion and D1 transport.
"""


def observed_provenance(detail: dict, runner: dict) -> dict:
    """Return a strictly bounded set of actually present source metadata fields."""
    result = {}
    for label, record, field in (
        ("raceSource", detail, "source"),
        ("raceSourceUrl", detail, "sourceUrl"),
        ("runnerSource", runner, "source"),
        ("runnerSourceUrl", runner, "sourceUrl"),
        ("raceObservedAt", detail, "sourceObservedAt"),
        ("runnerObservedAt", runner, "sourceObservedAt"),
    ):
        value = record.get(field) if isinstance(record, dict) else None
        if isinstance(value, str) and value.strip():
            result[label] = value.strip()[:240]
    return result
