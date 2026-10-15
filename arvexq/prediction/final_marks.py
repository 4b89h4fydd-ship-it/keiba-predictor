"""Single live pre-off marks authority for central and local racing.

The retired TRUE RUN / PURE / SECTIONAL scorer and archived v207-v317
ranking logic must never run. Immutable pre-off original forecasts are handled
separately by the archive module, not recalculated here.
"""
from __future__ import annotations
from arvexq.prediction.observed_model import apply_observed_marks

CORE_MARKS = ("◎", "○", "▲", "△")
LOWER_MARKS = ("☆", "注")


def apply_core_marks(detail):
    return apply_observed_marks(detail)
