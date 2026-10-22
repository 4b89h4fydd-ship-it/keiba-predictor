"""End-to-end item125 CLI reports on synthetic, independently labelled preoff fixtures.

Never use these fixtures to claim actual accuracy, genuine external timestamps,
production adoption, or performance of the six approved prediction systems.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

from arvexq.components.item_125.preoff_capture import capture_preoff_features
from arvexq.components.item_125.preoff_evidence_store import append_capture, open_store

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def _fixtures(db_path):
    results = []
    receipts = []
    with open_store(db_path) as db:
        for prefix, circuit, track, surface in [
            ("jra", "中央", "東京", "芝"),
            ("nar", "地方", "佐賀", "ダ"),
        ]:
            date = "2026-08-01"
            race_id = f"{prefix}-{date}-{track}-01"
            race = {
                "id": race_id, "date": date, "startTime": "12:00",
                "circuit": circuit, "track": track, "surface": surface,
                "distance": 1600, "condition": "良",
                "horses": [
                    {
                        "horseNumber": n, "age": 3, "carriedWeight": 55,
                        "recentRaces": [
                            {
                                "date": "2026-07-20", "finish": n,
                                "fieldSize": 10, "track": track,
                                "surface": surface, "distance": 1600,
                            }
                        ],
                    }
                    for n in range(1, 5)
                ],
            }
            snapshot, receipt = capture_preoff_features(
                race, [1, 2, 3, 4],
                now=datetime(2026, 8, 1, 11, 30, tzinfo=JST),
            )
            capture_id = append_capture(db, snapshot, receipt, clock=receipt["capturedAtEpoch"] + 2)
            assert append_capture(db, snapshot, receipt, clock=receipt["capturedAtEpoch"] + 3) == capture_id
            receipts.append(receipt)
            results.append({
                "raceId": race_id, "status": "確定",
                "confirmedAtEpoch": receipt["postAtEpoch"] + 600,
                "finishers": [{"horseNumber": n, "finish": n} for n in range(1, 5)],
            })
        assert db.execute("SELECT COUNT(*) FROM forecast_preoff_evidence").fetchone()[0] == 2
    return results, receipts


def _run_cli(store, official, report):
    return subprocess.run(
        [
            sys.executable, "-m", "scripts.arvexq_verified_holdout",
            "--store", str(store), "--results", str(official),
            "--report", str(report),
        ],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=90,
    )


def test_cli_generates_separate_circuit_json_report_without_mutating_evidence(tmp_path):
    store = tmp_path / "append-only-research.sqlite"
    results, _receipts = _fixtures(store)
    official = tmp_path / "independent-final-results.json"
    output = tmp_path / "verified-holdout-report.json"
    official.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    before = store.read_bytes()

    first = _run_cli(store, official, output)
    assert first.returncode == 0, first.stderr
    assert output.is_file()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report == json.loads(first.stdout)
    assert report["audit"]["archived_races"] == 2
    assert report["audit"]["verified_labelled_races"] == 2
    assert set(report["byCircuitAndFamily"]) == {"中央/flat", "地方/flat"}
    for circuit in ("中央/flat", "地方/flat"):
        assert report["byCircuitAndFamily"][circuit]["eligible"] is False
        assert report["byCircuitAndFamily"][circuit]["races"] == 1
    assert report["claim80PercentAchieved"] is False
    assert report["status"] == "offline-research-only-no-mark-or-ticket-results"
    assert store.read_bytes() == before

    repeated = _run_cli(store, official, output)
    assert repeated.returncode == 0, repeated.stderr
    assert repeated.stdout == first.stdout
    assert store.read_bytes() == before
    with open_store(store) as db:
        assert db.execute("SELECT COUNT(*) FROM forecast_preoff_evidence").fetchone()[0] == 2


def test_cli_excludes_future_information_and_does_not_publish_fake_accuracy(tmp_path):
    store = tmp_path / "research.sqlite"
    results, receipts = _fixtures(store)
    # A final result supposedly published before post time must fail the join.
    results[1]["confirmedAtEpoch"] = receipts[1]["postAtEpoch"] - 1
    official = tmp_path / "final-results.json"
    report = tmp_path / "report.json"
    official.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    before = store.read_bytes()
    outcome = _run_cli(store, official, report)
    assert outcome.returncode == 0, outcome.stderr
    parsed = json.loads(report.read_text(encoding="utf-8"))
    assert parsed["audit"]["verified_labelled_races"] == 1
    assert parsed["audit"]["invalid_or_inconsistent_snapshot_or_result"] == 1
    assert set(parsed["byCircuitAndFamily"]) == {"中央/flat"}
    assert parsed["claim80PercentAchieved"] is False
    assert store.read_bytes() == before


def test_cli_rejects_duplicate_independent_labels_without_writing_report(tmp_path):
    store = tmp_path / "research.sqlite"
    results, _ = _fixtures(store)
    official = tmp_path / "duplicate-results.json"
    report = tmp_path / "report.json"
    official.write_text(json.dumps([results[0], results[0]]), encoding="utf-8")
    before = store.read_bytes()
    outcome = _run_cli(store, official, report)
    assert outcome.returncode != 0
    assert "duplicate raceId" in outcome.stderr
    assert not report.exists()
    assert store.read_bytes() == before


def test_offline_research_modules_are_not_imported_by_live_forecast_entrypoints():
    for path in (
        "app.py", "workers/api.mjs", "workers/web.mjs",
        "arvexq/prediction/observed_model.py", "arvexq/ui/static/app.js",
    ):
        source = (ROOT / path).read_text(encoding="utf-8")
        for retired in (
            "verified_holdout", "top_three_joint_research",
            "conditional_positions_research",
        ):
            assert retired not in source, (path, retired)
