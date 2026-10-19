"""Existing version-tagged observed horse history cache key; no storage I/O."""
def horse_history_key(horse_key: str, version: str = "v1") -> str:
    return f"horse-history:{version}:{horse_key}"
