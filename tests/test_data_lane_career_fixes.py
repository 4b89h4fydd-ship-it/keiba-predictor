"""Regression tests for the 2026-11-27 data-lane career fixes.

Defect 1 (app.py): the full-history harvest was only scheduled after the
fast diagnosis had been computed and saved, so a first build diagnosed
against whatever RaceDB happened to hold. The NAR harvest is pure local
SQLite work, so it is now drained synchronously before the diagnosis via
``_harvest_nar_local_history``.

Defect 2 (fallback_enrichment): the NAR margins branch restricted the
horse_history pass to the three official NAR sources, which can only
supply NAR races. A horse whose career is entirely JRA was finalised
without the identity-verified career source ever being attempted.

Defect 3 (legacy_bridge): the netkeiba verified-career adapter returned
{} for limit <= 5, so light-lane callers could never receive a verified
career at all.
"""
from __future__ import annotations

import asyncio
import inspect
import time

import pytest

import app as app_module
from arvexq.databanks import legacy_bridge
from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities
from arvexq.ingest.fallback_enrichment import enrich_race_missing
from arvexq.ingest.full_career import date_key


# --- Defect 3: the verified-career adapter honours small-limit calls -------

def _adapter(monkeypatch, calls):
    def fake_verified(get, horse, race, limit):
        calls.append(limit)
        return {"recentRaces": [{"date": "2026-01-01"}],
                "allPastRuns": [{"date": "2026-01-01"}]}

    monkeypatch.setattr(legacy_bridge, "fetch_verified_career", fake_verified)
    fetch = legacy_bridge._netkeiba_verified_career_adapter(
        {"_netkeiba_get": lambda url, timeout, ttl: ""})
    assert fetch is not None
    return fetch


def test_verified_career_adapter_runs_for_limit_five(monkeypatch):
    calls: list[int] = []
    fetch = _adapter(monkeypatch, calls)
    out = fetch({"name": "テストホース"}, {"date": "2026-11-26"}, 5)
    assert out  # previously {} without any fetch attempt
    assert calls == [legacy_bridge._VERIFIED_CAREER_MIN_LIMIT]


def test_verified_career_adapter_floors_default_limit(monkeypatch):
    calls: list[int] = []
    fetch = _adapter(monkeypatch, calls)
    fetch({"name": "テストホース"}, {"date": "2026-11-26"})
    assert calls == [legacy_bridge._VERIFIED_CAREER_MIN_LIMIT]


def test_verified_career_adapter_passes_through_large_limit(monkeypatch):
    calls: list[int] = []
    fetch = _adapter(monkeypatch, calls)
    fetch({"name": "テストホース"}, {"date": "2026-11-26"}, 1000)
    assert calls == [1000]


# --- Defect 2: the NAR margins branch also tries the verified source -------

def _recording_fetcher(calls: list[str], name: str):
    def fetch(horse, race, limit):
        calls.append(name)
        return {}
    return fetch


def _fake_registry(calls: list[str]) -> DataBankRegistry:
    reg = DataBankRegistry()

    def add(name: str, circuit: str, priority: int) -> None:
        reg.register(DataSource(
            name=name, circuit=circuit, priority=priority,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": _recording_fetcher(calls, name)},
        ))

    add("nar_official_past_results", "NAR", 12)
    add("nar_official_csv", "NAR", 20)
    add("nar_official", "NAR", 30)
    add("netkeiba_verified_career", "both", 60)
    return reg


def _nar_margins_horse(cutoff: str) -> dict:
    """Five runs with complete corners; the newest lacks a margin.

    The same-date audit is complete, so the full-search branch stays off
    and the horse lands exactly in the NAR margins branch.
    """
    runs = []
    for i, day in enumerate(
            ["2026-11-20", "2026-11-06", "2026-10-23", "2026-10-09", "2026-09-25"]):
        run = {
            "date": day, "track": "名古屋", "distance": 1500, "raceNumber": 7,
            "finish": 3, "fieldSize": 12, "cornerPositions": [3, 3, 3],
        }
        if i:
            run["timeBehindWinner"] = 0.4
        runs.append(run)
    return {
        "name": "テストホース", "horseNumber": 1,
        "recentRaces": runs, "allPastRuns": list(runs),
        "sire": "テストサイア", "dam": "テストダム",
        "jockeyStats": {"starts": 10}, "trainerStats": {"starts": 10},
        "_careerHistoryAudit": {
            "requestedAtRaceDate": date_key(cutoff),
            "complete": True,
            "failedProviders": [],
            "failedEvidenceProviders": [],
            "reportedStarts": 5,
            "evidenceAttempted": True,
            "fetchAttempted": True,
        },
    }


def test_nar_margins_branch_tries_verified_career():
    cutoff = "2026-11-26"
    calls: list[str] = []
    detail = {
        "id": "nar-2026-11-26-名古屋-07", "circuit": "地方", "date": cutoff,
        "horses": [_nar_margins_horse(cutoff)],
    }
    asyncio.run(enrich_race_missing(
        detail, bank_registry=_fake_registry(calls), history_limit=1000))
    assert "nar_official_past_results" in calls
    assert "netkeiba_verified_career" in calls


# --- Defect 1: the local NAR harvest drains before diagnosis ---------------

class _FakeNarStore:
    instances: list["_FakeNarStore"] = []

    def __init__(self):
        self.conn = _FakeConn()
        self.queries: list[tuple[str, str, int]] = []
        _FakeNarStore.instances.append(self)

    def recent_races(self, name, cutoff, limit):
        self.queries.append((name, cutoff, limit))
        if name == "ダメ馬":
            raise RuntimeError("store read failed")
        return [{"date": "2026-01-05", "track": "名古屋", "finish": 2},
                {"date": "2025-12-01", "track": "名古屋", "finish": 4}]


class _FakeConn:
    def close(self):
        pass


class _FakeRaceDB:
    def __init__(self):
        self.updated: dict[str, int] = {}
        self.upserts: list[tuple[str, int]] = []
        self.marks: list[tuple[str, str]] = []

    def _horse_key(self, horse):
        return str(horse.get("name") or "")

    def source_updated(self, key):
        return self.updated.get(key)

    def upsert_past_runs(self, horse, runs):
        self.upserts.append((str(horse.get("name") or ""), len(runs)))
        return len(runs)

    def mark_source(self, key, status, note):
        self.marks.append((key, status))
        if status == "done":
            self.updated[key] = int(time.time())


@pytest.fixture()
def fake_stores(monkeypatch):
    _FakeNarStore.instances = []
    racedb = _FakeRaceDB()
    monkeypatch.setattr(app_module, "NarStore", _FakeNarStore)
    monkeypatch.setattr(app_module, "RACEDB", racedb)
    return racedb


def test_local_nar_harvest_drains_store_and_isolates_failures(fake_stores):
    horses = [{"name": "全履歴馬"}, {"name": "ダメ馬"}, {"name": "二走馬"}]
    done, upserted = app_module._harvest_nar_local_history(horses, "2026-11-26", ttl=21600)
    assert done == 2  # the failing horse is isolated, the rest still drain
    assert upserted == 4
    assert ("fullhist:nar:ダメ馬", "error") in fake_stores.marks


def test_local_nar_harvest_skips_within_ttl(fake_stores):
    horses = [{"name": "全履歴馬"}]
    app_module._harvest_nar_local_history(horses, "2026-11-26", ttl=21600)
    done, upserted = app_module._harvest_nar_local_history(horses, "2026-11-26", ttl=21600)
    assert (done, upserted) == (0, 0)


def test_fast_diagnosis_syncs_local_career_before_metrics():
    src = inspect.getsource(app_module._build_fast_diagnosis_snapshot)
    assert src.index("_harvest_nar_local_history(") < src.index("_precompute_detail_metrics(detail)")
