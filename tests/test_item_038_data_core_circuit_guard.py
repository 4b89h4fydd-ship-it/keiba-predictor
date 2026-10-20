"""#038: existing data-core refresh cannot treat unknown race IDs as NAR.

Read-only contracts call the actual app-installed component and its existing
HTTP route wrapper; the existing JRA/NAR acquisition paths are not replaced.
"""
from unittest.mock import patch

import pytest


@pytest.mark.parametrize("race_id", [
    "unrecognized-race", "unknown-2026-10-20-東京-01",
    "race-2026-10-20-大井-01", "unknown-nar-2026-10-20-大井-01",
])
def test_unknown_id_does_not_start_refresh_or_touch_persistence(race_id):
    import app

    with patch.object(app, "_data_core_snapshot", side_effect=AssertionError("read routed")), \
         patch.object(app, "_hydrate_fast_card_now", side_effect=AssertionError("collector routed")), \
         patch.object(app, "_data_core_record_run", side_effect=AssertionError("write routed")), \
         patch.object(app, "_data_core_running", set()) as running:
        result = app._data_core_refresh_race(race_id, True)
        assert running == set()
    assert result == {"raceId": race_id, "ok": False,
                      "error": "unsupported race id circuit"}


@pytest.mark.parametrize("race_id", [
    "jra-2026-10-20-東京-01",
    "nar-2026-10-20-大井-01",
])
def test_existing_jra_nar_ids_still_reach_the_original_scheduler(race_id):
    import app

    # Already-running branch proves the unchanged scheduler identity without
    # starting network reads, a thread, or a write in this fixture.
    with patch.object(app, "_data_core_running", {race_id}), \
         patch.object(app, "_data_core_snapshot", return_value={"id": race_id}) as snap, \
         patch.object(app, "_data_core_health", return_value={"card": {"status": "ready"}}):
        result = app._data_core_refresh_race(race_id, False)
    assert result["raceId"] == race_id
    assert result["ok"] is True and result["running"] is True
    snap.assert_called_once_with(race_id)


def test_existing_refresh_endpoint_refuses_unidentified_circuit():
    import app

    with patch.object(app, "_data_core_snapshot", side_effect=AssertionError("read routed")):
        assert app.data_core_refresh("unrecognized-race", force=1) == {
            "raceId": "unrecognized-race",
            "ok": False,
            "error": "unsupported race id circuit",
        }


def test_empty_race_id_retains_original_error():
    import app

    assert app._data_core_refresh_race("", True) == {
        "raceId": "", "ok": False, "error": "empty race id",
    }
