"""Validate existing static racecards against saved-snapshot *manifests*.

This is not an API, website scraping, a full-snapshot hash verification, an
official race completeness audit, or proof of past-race history coverage.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import re
from typing import Any

from arvexq.v3.data.quality import normalize_circuit

BASIC_FIELDS = ("horseNumber", "frameNumber", "name", "sex", "age",
                "jockey", "carriedWeight")
DIGEST = re.compile(r"^[a-f0-9]{64}$")


def audit_pair(card: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(card, dict) or not isinstance(manifest, dict):
        raise ValueError("two existing JSON objects required")
    day = card.get("date")
    try:
        if date.fromisoformat(str(day)).isoformat() != day:
            raise ValueError("non-canonical day")
    except (ValueError, TypeError):
        raise ValueError("invalid archive date") from None
    if (card.get("version") != "arvexq-static-entry-v1"
            or manifest.get("version") != "arvexq-saved-snapshots-v1"
            or manifest.get("date") != day):
        raise ValueError("unknown archive schema or date mismatch")
    races = card.get("races")
    snapshots = manifest.get("races")
    if not isinstance(races, list) or not isinstance(snapshots, dict):
        raise ValueError("archive race collections missing")
    expected = card.get("raceCount")
    if not isinstance(expected, int) or isinstance(expected, bool) or expected != len(races):
        raise ValueError("declared archive race count mismatch")

    circuit_counts = {name: Counter() for name in ("jra", "nar")}
    venue_counts: dict[str, Counter] = {}
    missing_fields: dict[str, Counter] = {name: Counter() for name in ("jra", "nar")}
    missing_examples: list[dict[str, Any]] = []
    problems: list[dict[str, Any]] = []
    race_ids: set[str] = set()

    def problem(code: str, rid: str = "") -> None:
        problems.append({"code": code, "raceId": rid})

    for row in races:
        if not isinstance(row, dict):
            problem("invalid-race-row")
            continue
        rid = str(row.get("id") or "")
        circuit = normalize_circuit(row.get("circuit"))
        track = str(row.get("track") or "").strip()
        if not rid or rid in race_ids:
            problem("missing-or-duplicate-race-id", rid)
            continue
        race_ids.add(rid)
        if circuit not in circuit_counts or not rid.startswith(circuit + "-"):
            problem("race-circuit-mismatch", rid)
            continue
        if row.get("date") != day:
            problem("race-date-mismatch", rid)
        if not track or not rid.startswith(f"{circuit}-{day}-{track}-"):
            problem("race-track-id-mismatch", rid)
        horses = row.get("horses")
        if not isinstance(horses, list):
            problem("invalid-runner-list", rid)
            continue
        n = len(horses)
        stats = circuit_counts[circuit]
        stats["races"] += 1
        stats["runnerRows"] += n
        venue_key = f"{circuit}:{track}"
        venue_counts.setdefault(venue_key, Counter())["races"] += 1
        venue_counts[venue_key]["runnerRows"] += n
        field_size = row.get("fieldSize")
        if not isinstance(field_size, int) or isinstance(field_size, bool) or field_size != n:
            problem("card-fieldsize-mismatch", rid)

        snap = snapshots.get(rid)
        if not isinstance(snap, dict):
            problem("missing-saved-manifest-race", rid)
        else:
            digest = snap.get("sha256")
            if not isinstance(digest, str) or not DIGEST.fullmatch(digest) or snap.get("file") != digest + ".json":
                problem("invalid-snapshot-filename", rid)
            if (not isinstance(snap.get("horses"), int)
                    or isinstance(snap.get("horses"), bool)
                    or snap["horses"] != n):
                problem("snapshot-manifest-runner-count-mismatch", rid)
            if (not isinstance(snap.get("bytes"), int)
                    or isinstance(snap.get("bytes"), bool)
                    or snap["bytes"] <= 0):
                problem("invalid-snapshot-size-metadata", rid)
        seen: set[int] = set()
        for h in horses:
            if not isinstance(h, dict):
                problem("invalid-runner-row", rid)
                continue
            raw_no = h.get("horseNumber")
            if not isinstance(raw_no, int) or isinstance(raw_no, bool) or raw_no <= 0 or raw_no in seen:
                problem("invalid-or-duplicate-runner-number", rid)
            else:
                seen.add(raw_no)
            for field in BASIC_FIELDS:
                value = h.get(field)
                if value is None or value == "" or isinstance(value, str) and value.strip() in ("", "-", "不明"):
                    missing_fields[circuit][field] += 1
                    stats["missingFieldCells"] += 1
                    if len(missing_examples) < 200:
                        missing_examples.append({"date": day, "raceId": rid,
                                                 "horseNumber": raw_no, "field": field})

    for rid in sorted(set(snapshots) - race_ids):
        problem("orphan-snapshot-manifest-entry", rid)
    by_circuit = {}
    for name in ("jra", "nar"):
        c = circuit_counts[name]
        by_circuit[name] = {"races": c["races"], "runnerRows": c["runnerRows"],
                            "missingFieldCells": c["missingFieldCells"],
                            "missingByField": dict(sorted(missing_fields[name].items()))}
    return {
        "schema": "arvexq-v3-static-archive-audit-1",
        "date": day,
        "scope": "saved-racecard-vs-snapshot-manifest",
        "declaredRaces": expected,
        "observedRaceRows": len(races),
        "snapshotManifestRaces": len(snapshots),
        "circuits": by_circuit,
        "venues": {k: dict(v) for k, v in sorted(venue_counts.items())},
        "missingExamples": missing_examples,
        "problems": problems,
        "integrity": "manifest-consistent" if not problems else "manifest-mismatch",
        "snapshotPayloadHashesVerified": False,
        "officialAllRacesVerified": False,
        "pastRunsCoverageVerified": False,
        "predictionStatus": "not-implemented",
    }


def summarize(days: list[dict[str, Any]]) -> dict[str, Any]:
    if not days:
        raise ValueError("at least one day required")
    circuit = {name: {"races": 0, "runnerRows": 0,
                      "missingFieldCells": 0, "missingByField": Counter()}
               for name in ("jra", "nar")}
    for report in days:
        for name in circuit:
            row = report["circuits"][name]
            for field in ("races", "runnerRows", "missingFieldCells"):
                circuit[name][field] += row[field]
            circuit[name]["missingByField"].update(row["missingByField"])
    for row in circuit.values():
        row["missingByField"] = dict(sorted(row["missingByField"].items()))
    return {
        "schema": "arvexq-v3-static-week-audit-1",
        "start": days[0]["date"], "end": days[-1]["date"],
        "dateCount": len(days),
        "racecards": sum(x["observedRaceRows"] for x in days),
        "manifestEntries": sum(x["snapshotManifestRaces"] for x in days),
        "circuits": circuit,
        "structuralProblems": sum(len(x["problems"]) for x in days),
        "dates": days,
        "provenance": "repository saved racecard and snapshot manifest",
        "proofLimits": {
            "fullOriginalDigestVerification": "not-performed",
            "officialTotalRosterComparison": "not-performed",
            "fullPastRunsCoverage": "not-measured",
            "liveApiStatus": "not-tested-by-this-report",
        },
        "predictionStatus": "not-implemented",
    }
