"""#023 observed race-ID boundary: JRA/NAR isolation, no inferred identity.

Unit/connection contracts for the existing pure race identifier module.
This is not a live provider, D1 or UI readback.
"""
from copy import deepcopy
from decimal import Decimal
import importlib

import pytest

from arvexq.components.item_023.race_identity import (
    canonical_race_id, observed_detail_identity_error, same_race,
)
from arvexq.ingest.nar_csv import (
    canonical_race_id as csv_canonical_race_id,
    same_race as csv_same_race,
)


class OverflowNumber:
    def __int__(self):
        raise OverflowError("nonfinite external numeric value")


@pytest.mark.parametrize("circuit,short,expected", [
    ("中央", "jra", "jra-2026-10-20-東京-01"),
    ("地方", "nar", "nar-2026-10-20-東京-01"),
])
def test_observed_ids_canonicalize_without_mixing_circuits(circuit, short, expected):
    assert canonical_race_id(circuit, "2026-10-20", "東京", "01") == expected
    assert canonical_race_id(short, "2026/10/20", "東京", 1) == expected
    assert csv_canonical_race_id(circuit, "2026-10-20", "東京", 1) == expected


@pytest.mark.parametrize("circuit", ["中央", "地方"])
@pytest.mark.parametrize("nonfinite", [
    float("inf"), float("-inf"), float("nan"),
    Decimal("Infinity"), Decimal("-Infinity"), OverflowNumber(),
])
def test_nonfinite_race_number_refuses_identity_without_raising(circuit, nonfinite):
    assert canonical_race_id(circuit, "2026-10-20", "東京", nonfinite) is None
    actual = {"circuit": circuit, "date": "2026-10-20",
              "track": "東京", "raceNumber": nonfinite}
    expected = {"circuit": circuit, "date": "2026-10-20",
                "track": "東京", "raceNumber": 1}
    assert same_race(actual, expected) is False
    assert csv_same_race(actual, expected) is False
    assert observed_detail_identity_error({**actual, "id": "bad-race"}) is None


def test_cross_circuit_same_observed_date_track_and_number_never_match():
    central = {"circuit": "中央", "date": "2026-10-20",
               "track": "東京", "raceNumber": 1}
    local = {**central, "circuit": "地方"}
    before = deepcopy((central, local))
    assert not same_race(central, local)
    assert (central, local) == before


def test_legacy_import_is_same_owned_component_not_a_duplicate_implementation():
    alias = importlib.import_module("arvexq.ingest.race_identity")
    owner = importlib.import_module("arvexq.components.item_023.race_identity")
    assert alias is owner
    assert alias.canonical_race_id is canonical_race_id
    assert csv_canonical_race_id is canonical_race_id
