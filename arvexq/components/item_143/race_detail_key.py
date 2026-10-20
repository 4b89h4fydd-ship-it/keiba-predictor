"""Existing version-tagged shared race detail cache key; no storage I/O."""
def race_detail_key(race_id: str, version: str = "v1") -> str:
    return f"race-detail:{version}:{race_id}"
