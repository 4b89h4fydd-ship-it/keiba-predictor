"""#041: read-only provenance ownership and JRA/NAR evidence isolation.

These tests exercise the existing source adapter only; they do not attest that
a provider is authoritative, reconcile source conflicts or contact production.
"""
from copy import deepcopy
import importlib

import pytest

from arvexq.components.item_041.source_provenance import observed_provenance


def test_legacy_path_is_the_exact_owned_component_module():
    alias = importlib.import_module("arvexq.ingest.source_provenance")
    owned = importlib.import_module("arvexq.components.item_041.source_provenance")
    assert alias is owned
    assert alias.observed_provenance is observed_provenance


@pytest.mark.parametrize(
    "race,runner,expected",
    [
        (
            {"circuit": "中央", "source": "JRA公式",
             "sourceUrl": "https://jra.example/observed",
             "sourceObservedAt": "2026-10-19T10:00:00+09:00"},
            {"name": "同名馬", "source": "JRA観測馬ソース",
             "sourceUrl": "https://jra.example/runner",
             "sourceObservedAt": "2026-10-19T10:00:01+09:00"},
            {"raceSource": "JRA公式",
             "raceSourceUrl": "https://jra.example/observed",
             "raceObservedAt": "2026-10-19T10:00:00+09:00",
             "runnerSource": "JRA観測馬ソース",
             "runnerSourceUrl": "https://jra.example/runner",
             "runnerObservedAt": "2026-10-19T10:00:01+09:00"},
        ),
        (
            {"circuit": "地方", "source": "NAR公式",
             "sourceUrl": "https://nar.example/observed",
             "sourceObservedAt": "2026-10-19T10:15:00+09:00"},
            {"name": "同名馬", "source": "NAR観測馬ソース",
             "sourceUrl": "https://nar.example/runner"},
            {"raceSource": "NAR公式",
             "raceSourceUrl": "https://nar.example/observed",
             "raceObservedAt": "2026-10-19T10:15:00+09:00",
             "runnerSource": "NAR観測馬ソース",
             "runnerSourceUrl": "https://nar.example/runner"},
        ),
    ],
)
def test_observed_circuit_facts_keep_only_their_own_metadata(race, runner, expected):
    before = deepcopy((race, runner))
    assert observed_provenance(race, runner) == expected
    assert (race, runner) == before


def test_missing_and_invalid_source_facts_remain_absent_not_inferred():
    race = {"circuit": "中央", "source": " ", "sourceUrl": None,
            "sourceObservedAt": 1792380000}
    runner = {"name": "同名馬", "source": {"provider": "external"},
              "sourceUrl": ["no URL observed"], "sourceObservedAt": ""}
    before = deepcopy((race, runner))
    assert observed_provenance(race, runner) == {}
    assert (race, runner) == before


def test_non_dict_records_and_long_fields_do_not_mutate_or_fabricate():
    source = {"source": "   " + "S" * 300 + "   ", "sourceUrl": 7}
    original = deepcopy(source)
    assert observed_provenance(source, []) == {"raceSource": "S" * 240}
    assert observed_provenance(None, None) == {}
    assert observed_provenance(source, {}) == {"raceSource": "S" * 240}
    assert source == original
