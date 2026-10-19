"""Compatibility and ownership checks for migrated single-responsibility modules.

The old public import must be an alias to the canonical component object,
not a duplicate implementation or a changed API entry point.
"""
import importlib
import sys

import pytest


MIGRATED = [
    [
        12,
        "arvexq/ingest/race_fields/title.py",
        "title"
    ],
    [
        13,
        "arvexq/ingest/race_fields/grade_class.py",
        "grade_class"
    ],
    [
        14,
        "arvexq/ingest/race_fields/start_time.py",
        "start_time"
    ],
    [
        15,
        "arvexq/ingest/race_fields/surface.py",
        "surface"
    ],
    [
        16,
        "arvexq/ingest/race_fields/distance.py",
        "distance"
    ],
    [
        17,
        "arvexq/ingest/race_fields/course.py",
        "course"
    ],
    [
        18,
        "arvexq/ingest/race_fields/field_size.py",
        "field_size"
    ],
    [
        19,
        "arvexq/ingest/race_fields/prize.py",
        "prize"
    ],
    [
        23,
        "arvexq/ingest/race_identity.py",
        "race_identity"
    ],
    [
        24,
        "arvexq/ingest/race_summary_merge.py",
        "race_summary_merge"
    ],
    [
        36,
        "arvexq/ingest/runner_cancellation.py",
        "runner_cancellation"
    ],
    [
        37,
        "arvexq/ingest/runner_exclusion.py",
        "runner_exclusion"
    ],
    [
        39,
        "arvexq/ingest/runner_identity_compare.py",
        "runner_identity_compare"
    ],
    [
        41,
        "arvexq/ingest/source_provenance.py",
        "source_provenance"
    ],
    [
        56,
        "arvexq/ingest/circuit_transfer.py",
        "circuit_transfer"
    ],
    [
        56,
        "arvexq/ingest/transfer_history.py",
        "transfer_history"
    ],
    [
        59,
        "arvexq/ingest/entry_fields/win_odds.py",
        "win_odds"
    ],
    [
        60,
        "arvexq/ingest/place_odds.py",
        "place_odds"
    ],
    [
        61,
        "arvexq/ingest/entry_fields/popularity.py",
        "popularity"
    ],
    [
        62,
        "arvexq/ingest/odds_capture_time.py",
        "odds_capture_time"
    ],
    [
        69,
        "arvexq/ingest/odds_fields/missing.py",
        "missing"
    ],
    [
        73,
        "arvexq/ingest/result_status/confirmed.py",
        "confirmed"
    ],
    [
        111,
        "arvexq/forecast/inputs.py",
        "inputs"
    ],
    [
        126,
        "arvexq/forecast/publication.py",
        "publication"
    ]
]


@pytest.mark.parametrize(("item_id", "old_module", "basename"), MIGRATED)
def test_previous_import_is_identical_to_owned_module(item_id, old_module, basename):
    owned_name = f"arvexq.components.item_{item_id:03d}.{basename}"
    previous = importlib.import_module(old_module)
    canonical = importlib.import_module(owned_name)
    assert previous is canonical
    assert sys.modules[old_module] is canonical
    assert canonical.__name__ == owned_name


def test_relative_dependency_rewrites_preserve_old_import_contract():
    for name in ("surface", "distance", "course", "title"):
        assert importlib.import_module("arvexq.ingest.race_fields." + name) is importlib.import_module(
            "arvexq.components.item_" + {"surface": "015", "distance": "016", "course": "017", "title": "012"}[name] + "." + name
        )
    surface = importlib.import_module("arvexq.ingest.race_fields.surface")
    distance = importlib.import_module("arvexq.ingest.race_fields.distance")
    sample = "コース：1200メートル（芝・右）"
    assert surface.extract(sample) == "芝"
    assert distance.extract(sample) == 1200


def test_forecast_boxes_do_not_activate_new_predictions():
    inputs = importlib.import_module("arvexq.ingest.place_odds")
    assert inputs.place_odds(None) is None
    assert inputs.place_odds("1.2～1.5") == {"placeOddsLow": 1.2, "placeOddsHigh": 1.5}
