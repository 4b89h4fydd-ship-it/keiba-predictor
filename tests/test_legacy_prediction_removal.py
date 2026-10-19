"""Regression checks: removed legacy generators must never silently return."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_retired_forecast_engine_deleted():
    assert not (ROOT / "arvexq/forecast/engine.py").exists()


def test_old_winner_training_code_deleted():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    for obsolete in (
        "_build_prerace_prediction", "_winner_learning_profile",
        "_learning_probability", "_learning_metric", "_learning_races",
        "_learning_paired_top1", "V312_CIRCUIT_METHODS",
        "WINNER_LEARNING_VERSION",
    ):
        assert obsolete not in source, obsolete


def test_legacy_forecast_generation_no_longer_called():
    source = (ROOT / "arvexq/components/item_127/implementation.py").read_text(encoding="utf-8")
    assert "_build_prerace_prediction" not in source
    # An immutable historical pre-off original remains useful for auditing.
    assert "def _prediction_audit_from_lock" in source
    assert "def _attach_prerace_audit" in source
