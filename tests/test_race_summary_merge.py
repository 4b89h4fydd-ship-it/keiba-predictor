"""Race discovery and summary refresh contracts preserve factual cached data."""
from stage4_source_support import implementation_source
import ast
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from arvexq.ingest.race_summary_merge import (
    choose_card_identifiers, index_summaries, merge_refreshed_summaries,
)


def test_same_number_at_different_venues_stays_distinct_and_cache_is_not_mutated():
    rows = [{"track": "東京", "raceNumber": 1, "title": "old"},
            {"track": "京都", "raceNumber": 1, "title": "京都"},
            {"track": "東京", "raceNumber": 1, "title": "東京"}]
    before = deepcopy(rows)
    indexed = index_summaries(rows)
    assert len(indexed) == 2 and indexed[("東京", 1)]["title"] == "東京"
    indexed[("東京", 1)]["title"] = "local edit"
    assert rows == before


def test_refresh_keeps_results_and_ignores_missing_schedule_observations():
    old = {("東京", 1): {"track": "東京", "raceNumber": 1, "distance": 1600,
                          "fieldSize": 12, "horses": [{"horseNumber": 1}],
                          "result": {"status": "確定", "finishers": [{"horseNumber": 1}]}}}
    fresh = [{"track": "東京", "raceNumber": 1, "distance": 0, "fieldSize": None,
              "startTime": "13:05", "horses": [{"horseNumber": 99}], "result": {}}]
    before = deepcopy((old, fresh))
    merged = merge_refreshed_summaries(old, fresh, lambda value: value)
    row = merged[("東京", 1)]
    assert row["distance"] == 1600 and row["fieldSize"] == 12
    assert row["startTime"] == "13:05" and row["horses"] == []
    assert row["result"] == old[("東京", 1)]["result"]
    assert (old, fresh) == before


def test_refresh_retains_existing_source_order_and_normalizer_fallback():
    fresh = [{"track": "東京", "raceNumber": 1, "source": "official"},
             {"track": "東京", "raceNumber": 1, "source": "existing fallback"},
             {"track": "", "raceNumber": 2}, {"track": "京都", "raceNumber": 0}]
    merged = merge_refreshed_summaries({}, fresh, lambda _value: None)
    assert list(merged) == [("東京", 1)]
    assert merged[("東京", 1)]["source"] == "existing fallback"


def test_discovery_prefers_observed_detailed_variant_without_inventing_a_card():
    ids = ["pw01dde10-a", "pw01dde01-b", "pw01dde10-c", "other-race", "unknown"]
    track = lambda value: "京都" if value == "other-race" else ("" if value == "unknown" else "東京")
    selected = choose_card_identifiers(ids, track, lambda _value: 1)
    assert selected == {("東京", 1): "pw01dde01-b", ("京都", 1): "other-race"}


def test_actual_summary_caller_uses_merge_and_retains_saved_result(tmp_path):
    db_path = tmp_path / "central.sqlite"
    result = {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
    cached = {"date": "2026-10-18", "track": "東京", "raceNumber": 1,
              "distance": 1600, "title": "cached", "horses": [{"horseNumber": 1}], "result": result}
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE central_races(date TEXT,track TEXT,race_no INTEGER,payload TEXT)")
        conn.execute("INSERT INTO central_races VALUES(?,?,?,?)",
                     (cached["date"], cached["track"], 1, json.dumps(cached)))
    saved, calls = [], []
    class Store:
        conn = SimpleNamespace(close=lambda: None)
        def upsert(self, rows):
            saved.extend(deepcopy(rows))
    def connect(path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    def merge(*args):
        calls.append(True)
        return merge_refreshed_summaries(*args)
    namespace = {"CENTRAL_DB_PATH": db_path, "_new_conn": connect, "json": json,
                 "JRA_BAD_TITLE_RE": re.compile("never matches"), "_clean": lambda x: str(x).strip(),
                 "_int": int, "_index_race_summaries": index_summaries,
                 "_merge_race_summaries": merge, "CentralStore": Store,
                 "_jra_program_summaries": lambda _: [{**cached, "title": "fresh", "startTime": "13:00"}],
                 "_netkeiba_race_summaries": lambda _: [{**cached, "startTime": "13:05", "distance": 0}]}
    source = ast.parse(implementation_source())
    functions = [node for node in source.body if isinstance(node, ast.FunctionDef)
                 and node.name in ("central_race_summaries", "normalize_central_race")]
    exec(compile(ast.Module(body=functions, type_ignores=[]), "app.py", "exec"), namespace)
    rows = namespace["central_race_summaries"]("2026-10-18", allow_network=True, force=True)
    assert calls == [True] and len(rows) == 1
    assert rows[0]["result"] == result and rows[0]["horses"] == []
    assert rows[0]["distance"] == 1600 and rows[0]["startTime"] == "13:05"
    assert saved == rows


def test_actual_official_discovery_deduplicates_before_runner_fetch():
    ids = ["pw01dde10-20261018-T1", "pw01dde01-20261018-T1",
           "pw01dde10-20261018-T2", "pw01dde10-20261018-K1"]
    calls = []
    track = lambda value: "京都" if value.endswith("K1") else "東京"
    number = lambda value: 2 if value.endswith("T2") else 1
    def choose(*args):
        calls.append(True)
        return choose_card_identifiers(*args)
    namespace = {"re": re, "os": os, "ThreadPoolExecutor": ThreadPoolExecutor,
                 "JRA_CNAME_RE": re.compile(r"pw01dde(?:01|10)-[A-Za-z0-9-]+"),
                 "_jra_request": lambda *_args: " ".join(ids),
                 "_jra_track_from_cname": track, "_jra_race_no_from_cname": number,
                 "_choose_race_cards": choose,
                 "_jra_parse_race": lambda value, **_kwargs: {
                     "id": value, "track": track(value), "raceNumber": number(value)}}
    source = ast.parse(implementation_source())
    function = next(node for node in source.body
                    if isinstance(node, ast.FunctionDef) and node.name == "fetch_jra_official")
    exec(compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"), namespace)
    rows = namespace["fetch_jra_official"]("2026-10-18")
    assert calls == [True]
    assert {row["id"] for row in rows} == set(ids[1:])
