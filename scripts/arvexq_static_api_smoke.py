"""Verify generated static API packs against the payload they came from.

Independent of the builder's internals: it recomputes the expected day
rows and race bodies straight from the source payload (official snapshot
or sync payload) and deep-compares them with the files on disk.

Usage:
  python scripts/arvexq_static_api_smoke.py \
      --source data/official-2026-11-21.json \
      --static-dir arvexq/ui/static/api-static --date 2026-11-21
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

BANEI = ("帯広", "帯広ば")


def expected_from_official(payload: dict):
    races, details = {}, {}
    for entry in payload.get("results") or []:
        resp = (entry or {}).get("detail") or {}
        s = resp.get("summary") or {}
        rid = s.get("race_id") or (entry or {}).get("id")
        if not rid or "帯広" in str(rid) or s.get("track") in BANEI:
            continue
        races[rid] = {
            "id": s.get("race_id"), "date": s.get("race_date"),
            "circuit": s.get("circuit"), "track": s.get("track"),
            "raceNumber": s.get("race_no"), "startTime": s.get("start_time"),
            "scheduledStartTime": s.get("start_time"), "title": s.get("title"),
            "surface": s.get("surface"), "distance": s.get("distance"),
            "weather": s.get("weather"), "condition": s.get("condition"),
            "volatility": {"label": s.get("volatility_label") or "",
                           "score": s.get("volatility_score")},
            "raceStatus": s.get("race_status") or "",
            "updatedAtEpoch": s.get("updated_at"),
        }
        d = copy.deepcopy(resp.get("detail") or {})
        d.pop("massFeatureSnapshot", None)
        details[rid] = {"detail": d, "odds": resp.get("odds") or [],
                        "analysis_ready": bool(resp.get("analysis_ready")),
                        "detail_updated_at": resp.get("detail_updated_at")}
    return races, details


def expected_from_sync(payload: dict):
    races, details = {}, {}
    for s in payload.get("summaries") or []:
        rid = s.get("id") or s.get("race_id")
        if not rid or "帯広" in str(rid) or s.get("track") in BANEI:
            continue
        vol = s.get("volatility") if isinstance(s.get("volatility"), dict) else {
            "label": s.get("volatility_label") or "", "score": s.get("volatility_score")}
        races[rid] = {
            "id": rid, "date": s.get("date") or s.get("race_date"),
            "circuit": s.get("circuit"), "track": s.get("track"),
            "raceNumber": s.get("raceNumber", s.get("race_no")),
            "startTime": s.get("startTime", s.get("start_time")),
            "scheduledStartTime": s.get("scheduledStartTime", s.get("startTime", s.get("start_time"))),
            "title": s.get("title"), "surface": s.get("surface"),
            "distance": s.get("distance"), "weather": s.get("weather"),
            "condition": s.get("condition"), "volatility": vol,
            "raceStatus": s.get("raceStatus", s.get("race_status")) or "",
            "updatedAtEpoch": s.get("updatedAtEpoch", s.get("updated_at")),
        }
    odds_by_id = {}
    for o in payload.get("odds_current") or payload.get("oddsCurrent") or []:
        odds_by_id.setdefault(str(o.get("race_id") or ""), []).append(o)
    for d in payload.get("details") or []:
        rid = str(d.get("id") or d.get("race_id") or "")
        if not rid or "帯広" in rid or d.get("track") in BANEI:
            continue
        dd = copy.deepcopy(d)
        dd.pop("massFeatureSnapshot", None)
        odds_rows = [{k: v for k, v in o.items() if k not in ("race_id", "raceId")}
                     if isinstance(o, dict) else o for o in odds_by_id.get(rid, [])]
        details[rid] = {"detail": dd, "odds": odds_rows,
                        "analysis_ready": bool((d.get("preparedMeta") or {}).get("diagnosisReady")),
                        "detail_updated_at": None}
    return races, details


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--static-dir", required=True)
    p.add_argument("--date", required=True)
    args = p.parse_args()

    payload = json.loads(Path(args.source).read_text(encoding="utf-8"))
    if isinstance(payload.get("results"), list):
        races, details = expected_from_official(payload)
    else:
        races, details = expected_from_sync(payload)
    root = Path(args.static_dir)
    failures = []

    day = json.loads((root / "day" / f"{args.date}.json").read_text(encoding="utf-8"))
    got_rows = {r["id"]: r for r in day.get("races") or []}
    if set(got_rows) != set(races):
        failures.append(f"day race id set mismatch: static={len(got_rows)} expected={len(races)} "
                        f"missing={sorted(set(races) - set(got_rows))[:5]} extra={sorted(set(got_rows) - set(races))[:5]}")
    for rid, want in races.items():
        got = got_rows.get(rid)
        if got is None:
            continue
        for k, v in want.items():
            if got.get(k) != v:
                failures.append(f"day row {rid} field {k}: static={got.get(k)!r} expected={v!r}")
                break
    if day.get("raceCount") != len(races):
        failures.append(f"day raceCount {day.get('raceCount')} != {len(races)}")

    full_path = root / "day-full" / f"{args.date}.json"
    if full_path.is_file():  # day-full is a local/audit artifact; optional in deployed packs
        full = json.loads(full_path.read_text(encoding="utf-8"))
        if full.get("detailCount") != len(details):
            failures.append(f"day-full detailCount {full.get('detailCount')} != {len(details)}")
        if {str(d.get('id')) for d in full.get("details") or []} != set(details):
            failures.append("day-full detail id set mismatch")

    checked_horses = 0
    for rid, want in details.items():
        body = json.loads((root / "race" / f"{rid}.json").read_text(encoding="utf-8"))
        if body.get("race_id") != rid:
            failures.append(f"race {rid}: race_id mismatch")
            continue
        if body.get("detail") != want["detail"]:
            failures.append(f"race {rid}: detail payload differs from source")
            continue
        if body.get("odds") != want["odds"]:
            failures.append(f"race {rid}: odds differ from source")
        if body.get("analysis_ready") != want["analysis_ready"]:
            failures.append(f"race {rid}: analysis_ready differs")
        s = body.get("summary") or {}
        if s.get("id") != rid or s.get("track") != want["detail"].get("track") \
                or s.get("raceNumber") != want["detail"].get("raceNumber"):
            failures.append(f"race {rid}: display summary mismatch")
        checked_horses += len(want["detail"].get("horses") or [])

    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    entry = (index.get("dates") or {}).get(args.date) or {}
    if entry.get("raceCount") != len(races) or entry.get("detailCount") != len(details):
        failures.append("index.json counts mismatch")

    if failures:
        print("STATIC_API_SMOKE_FAILED")
        for f in failures[:20]:
            print(" -", f)
        return 1
    print("STATIC_API_SMOKE_OK", args.date, "races", len(races),
          "details", len(details), "horses", checked_horses)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
