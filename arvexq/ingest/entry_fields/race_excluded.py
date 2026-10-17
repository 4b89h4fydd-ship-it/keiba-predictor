"""Identify an observed race exclusion from an already normalized status."""

def from_status(status: str) -> bool:
    return status in ("除外", "競走除外")
