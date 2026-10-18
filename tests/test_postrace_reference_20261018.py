import json
import tempfile
from pathlib import Path
from datetime import date

from arvexq.ingest.full_snapshot_codec import pack_raw
from scripts.arvexq_postrace_reference_20261018 import produce, _asof_input

DAY = "2026-10-18"


def _horse(no, finishes):
    return {"horseNumber": no, "name": "horse" + str(no),
            "recentRaces": [
                {"date": "2026-10-%02d" % d, "finish": f}
                for d, f in zip((17, 10, 1), finishes)
            ]}


def _detail(race_id="nar-2026-10-18-test-01"):
    return {"id": race_id, "date": DAY, "startTime": "17:20", "horses": [
        _horse(1, [1, 2, 3]),
        _horse(2, [3, 1, 2]),
        _horse(3, [2, 3, 1]),
    ], "result": {"status": "確定", "finishers": [
        {"horseNumber": 3, "finish": 1}
    ]}, "preRacePrediction": {"horses": [
        {"horseNumber": 3, "mark": "◎"}
    ]}}


def _create(static, details):
    archive = static / "saved-snapshots"
    archive.mkdir()
    index = {"date": DAY, "races": {}}
    for record in details:
        packed = pack_raw(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        digest = packed["arvexqFullPayload"]["sha256"]
        filename = digest + ".json"
        (archive / filename).write_text(json.dumps(packed["arvexqFullPayload"]))
        index["races"][record["id"]] = {
            "file": filename, "sha256": digest,
            "bytes": packed["arvexqFullPayload"]["bytes"],
            "horses": len(record["horses"]),
            "prediction": False, "bet": False,
        }
    (archive / (DAY + ".json")).write_text(json.dumps(index))


def test_postrace_reference_uses_same_model_and_separates_historic_accuracy():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        original = _detail()
        bad = _detail("nar-2026-10-18-test-02")
        bad["horses"][2]["recentRaces"] = []
        _create(root, [original, bad])
        result = produce(root, root / "out")
        assert result["raceCount"] == 2
        assert result["referenceCount"] == 1
        assert result["canCountAsHit"] is False
        assert result["isHistoricPrediction"] is False
        row = result["races"][original["id"]]
        assert row["status"] == "reference"
        assert row["retrospective"] is True
        assert row["recommendedBets"] == []
        assert row["recommendationStatus"] == "no_verified_preoff_ticket"
        assert {x["mark"] for x in row["marks"]} == {"◎", "○", "▲"}
        assert result["races"][bad["id"]]["marks"] == []
        assert original["result"]["finishers"][0]["horseNumber"] == 3


def test_postrace_reference_excludes_same_day_future_and_unknown_history():
    before = _detail()
    facts, removed = _asof_input(before, date.fromisoformat(DAY))
    assert removed == 0
    assert all(len(h["recentRaces"]) == 3 for h in facts["horses"])
    before["horses"][0]["recentRaces"] += [
        {"date": "2026-10-18", "finish": 1},
        {"date": "2026-10-19", "finish": 1},
        {"finish": 1},
    ]
    sanitized, removed = _asof_input(before, date.fromisoformat(DAY))
    assert removed == 3
    assert sanitized["horses"][0]["recentRaces"] == facts["horses"][0]["recentRaces"]
    assert "result" not in sanitized and "preRacePrediction" not in sanitized


def test_reject_wrong_day_to_prevent_accidental_live_use():
    with tempfile.TemporaryDirectory() as temp:
        try:
            produce(Path(temp), Path(temp), "2026-10-19")
            assert False, "A reference for a different date must be rejected"
        except ValueError:
            pass
