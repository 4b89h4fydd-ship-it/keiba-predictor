"""#057: existing history harvest must never cross the JRA/NAR circuit boundary.

Uses the original app-installed worker, not a substitute collector. All data
stores and the background-thread launcher are fakes; no live DB/API is touched.
"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class ImmediateThread:
    """Run the unchanged scheduler's worker inline for deterministic checks."""

    def __init__(self, target, daemon):
        assert daemon is True
        self.target = target

    def start(self):
        self.target()


def _detail(circuit):
    return {
        "id": f"fixture-{circuit}",
        "date": "2026-10-20",
        "circuit": circuit,
        "horses": [
            {"name": "同名馬", "horseNumber": 1, "_jraHorseCname": "jra-fixture"}
        ],
    }


@pytest.mark.parametrize("circuit", [None, "", "UNKNOWN", "JRA", "NAR", "地方X", "中央X"])
def test_unknown_circuit_never_schedules_or_changes_source_state(circuit):
    import app

    detail = _detail(circuit)
    original = deepcopy(detail)
    race_db = MagicMock()
    thread_factory = MagicMock()
    with patch.dict("os.environ", {"RACEDB_FULL_HISTORY": "1"}), \
         patch.object(app, "RACEDB", race_db), \
         patch.object(app, "threading", SimpleNamespace(Thread=thread_factory)), \
         patch.object(app, "_full_history_running", set()):
        app._schedule_full_history_harvest(detail)
        assert not app._full_history_running

    thread_factory.assert_not_called()
    race_db.assert_not_called()
    assert detail == original


@pytest.mark.parametrize("circuit,expected_prefix", [
    ("地方", "fullhist:nar:"),
    ("中央", "fullhist:jra:"),
])
def test_valid_circuit_uses_only_its_existing_collector_and_store(circuit, expected_prefix):
    import app

    detail = _detail(circuit)
    original = deepcopy(detail)
    race_db = MagicMock()
    race_db._horse_key.return_value = "fixture-horse"
    race_db.source_updated.return_value = None
    race_db.upsert_past_runs.return_value = 1
    prepared = MagicMock()
    prepared.get.return_value = (None, None)
    nar_store = MagicMock()
    nar_store.recent_races.return_value = [{"date": "2026-09-01", "source": "NAR fixture"}]
    jra_fetch = MagicMock(return_value=[{"date": "2026-09-01", "source": "JRA fixture"}])

    with patch.dict("os.environ", {"RACEDB_FULL_HISTORY": "1"}), \
         patch.object(app, "RACEDB", race_db), \
         patch.object(app, "PREPARED_STORE", prepared), \
         patch.object(app, "NarStore", return_value=nar_store), \
         patch.object(app, "_jra_profile_runs", jra_fetch), \
         patch.object(app, "threading", SimpleNamespace(Thread=ImmediateThread)), \
         patch.object(app, "_full_history_running", set()):
        app._schedule_full_history_harvest(detail)
        assert not app._full_history_running

    assert race_db.mark_source.call_count == 1
    assert race_db.mark_source.call_args.args[0] == expected_prefix + "fixture-horse"
    assert race_db.upsert_past_runs.call_count == 1
    prepared.get.assert_called_once_with(detail["id"])

    if circuit == "地方":
        nar_store.recent_races.assert_called_once_with("同名馬", detail["date"], 100000)
        jra_fetch.assert_not_called()
    else:
        jra_fetch.assert_called_once_with("jra-fixture", detail["date"], 10000)
        nar_store.recent_races.assert_not_called()
    assert detail == original
