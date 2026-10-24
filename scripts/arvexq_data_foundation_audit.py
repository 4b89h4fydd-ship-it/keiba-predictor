#!/usr/bin/env python3
"""Read-only audit of EXISTING D1 bundle exports; no prediction or DB writes.

Full-payload and career envelopes must be recovered before measuring missingness.
Missing proof is unknown, never a zero-valued feature or a pre-off certificate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from arvexq.ingest.full_snapshot_codec import unpack_detail, pack_detail
from arvexq.ingest.career_transport import recover_horse
from arvexq.ingest.full_career import date_key, merge_career
from arvexq.ingest.pedigree_merge import ANCESTORS, present
from arvexq.ingest.circuit_boundary import normalized_circuit
from scripts.arvexq_fetch_d1_bundle import supported_race


def profile_bundle(bundle: dict) -> dict:
    raw_summaries = bundle.get("races") or []
    summaries = [r for r in raw_summaries if isinstance(r, dict) and supported_race(r)]
    excluded_ids = [str(r.get("id")) for r in raw_summaries if isinstance(r, dict) and not supported_race(r)]
    expected = {str(r["id"]): r for r in summaries if isinstance(r, dict) and r.get("id")}
    seen = set()
    segments = defaultdict(Counter)
    providers = Counter()
    errors = []
    duplicates = []
    for original in bundle.get("details") or []:
        if not supported_race(original):
            continue
        try:
            detail = unpack_detail(original)
            rid, day = str(detail.get("id") or ""), date_key(detail.get("date"))
            if not rid or not day or day != date_key(bundle.get("date")):
                raise ValueError("race identity/date mismatch")
            if rid not in expected:
                raise ValueError("detail is absent from day summary")
            if rid in seen:
                duplicates.append(rid)
                continue
            circuit = normalized_circuit(detail.get("circuit"))
            if circuit is None or circuit != normalized_circuit(expected[rid].get("circuit")):
                raise ValueError("unknown or conflicting circuit")
            horses = [recover_horse(h, day) for h in detail.get("horses", []) if isinstance(h, dict)]
            numbers = [str(h.get("horseNumber")) for h in horses]
            if any(no in ("None", "", "0") for no in numbers) or len(numbers) != len(set(numbers)):
                raise ValueError("missing/duplicate runner number")
            seen.add(rid)
            kind = "debut" if "新馬" in str(detail.get("title")) else "flat"
            if "障害" in str(detail.get("surface")) or "障害" in str(detail.get("title")):
                kind = "jumps"
            s = segments[(circuit, kind)]
            s["races"] += 1
            s["horses"] += len(horses)
            s["declaredRunners"] += int(detail.get("fieldSize") or len(horses))
            s["resultPresentRaces"] += bool((detail.get("result") or {}).get("finishers"))
            s["fusionInputPresentRaces"] += bool(detail.get("fusionInputs"))
            s["preoffEvidencePresentRaces"] += bool(detail.get("morningTicketEvidence"))
            s["specialBoxPresentRaces"] += bool(detail.get("specialRaceBox"))
            providers[str(detail.get("source") or "unknown")] += 1
            for h in horses:
                runs = merge_career(h.get("allPastRuns"), h.get("recentRaces"), day)
                s["historyPresentHorses"] += bool(runs)
                s["historyVerifiedCompleteHorses"] += (h.get("_careerHistoryAudit") or {}).get("complete") is True
                p = h.get("pedigree") if isinstance(h.get("pedigree"), dict) else {}
                for key in ANCESTORS:
                    s[key + "PresentHorses"] += present(p.get(key)) or present(h.get(key))
                s["pedigreeCompleteHorses"] += all(present(p.get(k)) or present(h.get(k)) for k in ANCESTORS)
                s["trainingPresentHorses"] += any(present(h.get(k)) for k in ("training", "workouts", "trainingRuns", "trainingData", "oikiri"))
                s["jumpStatsPresentHorses"] += bool(h.get("jumpStats") or h.get("obstacleStats"))
                s["videoTimingPresentHorses"] += any((r.get("earlyTiming") or {}).get("sourceKind") == "video_estimate" for r in runs)
                s["priorRuns"] += len(runs)
        except Exception as exc:
            errors.append({"raceId": original.get("id"), "error": f"{type(exc).__name__}: {exc}"})
    output = []
    for (circuit, kind), counts in sorted(segments.items()):
        row = {"circuit": circuit, "kind": kind, **dict(counts)}
        n = counts["horses"]
        row["missingRates"] = {key: (1 - counts[key] / n if n else None) for key in (
            "historyPresentHorses", "pedigreeCompleteHorses", "trainingPresentHorses",
            "jumpStatsPresentHorses", "videoTimingPresentHorses")}
        output.append(row)
    return {"date": bundle.get("date"), "expectedD1SummaryRaces": len(expected),
            "excludedRaceIds": excluded_ids,
            "duplicateSummaryCount": len(summaries) - len(expected),
            "decodedDetailRaces": len(seen), "missingDetailIds": sorted(set(expected) - seen),
            "duplicateDetailIds": duplicates, "errors": errors, "segments": output,
            "observedRaceSources": dict(providers),
            "limits": ["D1 summaries are not an independently verified official full-card denominator",
                       "Presence is not a historical pre-off timestamp or rights certificate",
                       "Training aliases are inspected fields, not proof all provider schemas were covered",
                       "Provider fetch success/latency requires actual attempt logs, not source labels"]}


def analytics_rows(bundle: dict):
    """Prepare new-day rows for the existing MotherDuck schema; never UPDATE."""
    audit = profile_bundle(bundle)
    if audit["errors"] or audit["duplicateDetailIds"] or audit["duplicateSummaryCount"] or audit["missingDetailIds"]:
        raise ValueError("incomplete/invalid D1 readback; refusing analytics import")
    for detail in bundle.get("details") or []:
        if not supported_race(detail):
            continue
        decoded = unpack_detail(detail)
        # Reuse the lossless envelope already used by all 401 MotherDuck rows.
        stored = pack_detail(detail)
        raw = json.dumps(stored, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        yield {"race_id": decoded["id"], "race_date": decoded["date"],
               "sha256": hashlib.sha256(raw.encode()).hexdigest(), "snapshot_json": json.loads(raw)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bundles", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--analytics-jsonl", help="Prepare an insert-only import file, WITHOUT writing MotherDuck")
    args = p.parse_args()
    reports, rows = [], []
    for file in args.bundles:
        bundle = json.loads(Path(file).read_text())
        reports.append(profile_bundle(bundle))
        if args.analytics_jsonl:
            rows.extend(analytics_rows(bundle))
    report = {"version": "arvexq-data-foundation-audit-v1", "acquiredAt": datetime.now(timezone.utc).isoformat(),
              "days": reports, "writes": 0}
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    if args.analytics_jsonl:
        ids = [r["race_id"] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate race IDs across input bundles")
        Path(args.analytics_jsonl).write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows))
    print(json.dumps({"days": len(reports), "decodedRaces": sum(r["decodedDetailRaces"] for r in reports),
                      "analyticsPrepared": len(rows), "writes": 0}))


if __name__ == "__main__":
    main()
