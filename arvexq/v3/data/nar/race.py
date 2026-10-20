"""NAR race observed-only reader.

Uses the existing collected race detail. No external fetch, mutation,
model calculation, marks, or betting logic.
"""
from __future__ import annotations

from arvexq.v3.data.observed_fields import race as _read


def read(detail: dict):
    return _read(detail, "nar")
