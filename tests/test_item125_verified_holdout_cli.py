"""Item 125 CLI fails closed when its deliberately removed research evaluator is absent.

No prediction model is revived, and existing append-only storage is untouched.
"""
import json
from pathlib import Path
import subprocess
import sys

from arvexq.components.item_125.preoff_evidence_store import open_store

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "scripts.arvexq_verified_holdout", *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_existing_cli_help_works_without_retired_evaluator():
    result = run_cli("--help")
    assert result.returncode == 0, result.stderr
    assert "--store" in result.stdout
    assert "--results" in result.stdout
    assert "--report" in result.stdout


def test_nonexistent_store_is_never_created(tmp_path):
    store = tmp_path / "not-created.sqlite"
    results = tmp_path / "official-results.json"
    results.write_text("[]", encoding="utf-8")
    outcome = run_cli("--store", store, "--results", results)
    assert outcome.returncode == 2
    assert "existing archived pre-off evidence database required" in outcome.stderr
    assert not store.exists()


def test_missing_evaluator_fails_closed_before_touching_existing_store(tmp_path):
    store = tmp_path / "preoff.sqlite"
    results = tmp_path / "official-results.json"
    output = tmp_path / "research-report.json"
    results.write_text(json.dumps([]), encoding="utf-8")
    with open_store(store) as db:
        db.execute("SELECT count(*) FROM forecast_preoff_evidence").fetchone()
    raw_before = store.read_bytes()
    first = run_cli("--store", store, "--results", results, "--report", output)
    second = run_cli("--store", store, "--results", results, "--report", output)
    for proc in (first, second):
        assert proc.returncode == 2
        assert "verified holdout evaluator unavailable" in proc.stderr
        assert "no capture database opened or modified" in proc.stderr
        assert "ModuleNotFoundError" not in proc.stderr
        assert not proc.stdout
    assert store.read_bytes() == raw_before
    assert not output.exists()
    with open_store(store) as db:
        assert db.execute("SELECT count(*) FROM forecast_preoff_evidence").fetchone()[0] == 0
