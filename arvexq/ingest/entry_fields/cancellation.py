"""Classify a runner's explicit cancellation without interpreting other fields.

Input: normalized observed status (str). Output: bool. No inference from odds.
"""
def from_status(status: str) -> bool:
    return status in ("出走取消", "競走取消", "取消")
