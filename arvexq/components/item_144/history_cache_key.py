"""Preserve legacy history cache key identity; cache storage remains shared."""
def horse_history_key(horse_key: str, version: str = "v1") -> str:
    return f"horse-history:{version}:{horse_key}"
