"""Exhaustive *saved-repository* blob + career sidecar validation.

Does not query an API, compare official entry lists, or generate predictions.
All 423 recorded race files are independently read and hash checked.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path
from typing import Any

from arvexq.v3.audit.archive import audit_pair
from arvexq.v3.audit.calendar_window import calendar_window
from arvexq.v3.audit.snapshot_digest import verify_one
from arvexq.v3.audit.runner_gaps import summarize_evidence
from arvexq.v3.data.quality import normalize_circuit


def verify_saved_week(archive_dir: Path, *, days: int = 7, end_date: str | None = None) -> dict[str, Any]:
    if isinstance(days, bool) or not isinstance(days, int) or days < 1 or days > 31:
        raise ValueError("days must be 1..31")
    sources = sorted(p for p in (archive_dir / "racecards").glob("????-??-??.json")
                      if (archive_dir / "saved-snapshots" / p.name).is_file())
    if end_date is not None:
        cutoff = date.fromisoformat(end_date).isoformat()
        sources = [p for p in sources if p.stem <= cutoff]
    if len(sources) < days:
        raise ValueError("not enough saved day archives")
    chosen = sources[-days:]
    # Do not silently exclude single-sided saved days inside the selected interval.
    selected_start, selected_end = chosen[0].stem, chosen[-1].stem
    card_days = {p.stem for p in (archive_dir / "racecards").glob("????-??-??.json")}
    manifest_days = {p.stem for p in (archive_dir / "saved-snapshots").glob("????-??-??.json")}
    if end_date is not None:
        card_days = {d for d in card_days if d <= cutoff}
        manifest_days = {d for d in manifest_days if d <= cutoff}
    unpaired = sorted(d for d in card_days ^ manifest_days
                      if selected_start <= d <= selected_end)
    counts = {c: Counter() for c in ("jra", "nar")}
    errors: list[dict[str, Any]] = [
        {"date": d, "code": "unpaired-saved-day",
         "filePresence": "racecard-only" if d in card_days else "manifest-only"}
        for d in unpaired
    ]
    sampled: list[dict[str, Any]] = []
    checked = 0
    structurally_consistent = 0
    no_prior_cases = []
    weight_cases = []
    for card_path in chosen:
        day = card_path.stem
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("invalid archive day")
        man_path = archive_dir / "saved-snapshots" / (day + ".json")
        card = json.loads(card_path.read_text(encoding="utf-8"))
        manifest = json.loads(man_path.read_text(encoding="utf-8"))
        structural = audit_pair(card, manifest)
        if structural["problems"]:
            errors.extend({"date": day, **x} for x in structural["problems"])
        else:
            structurally_consistent += 1
        for race in card["races"]:
            rid = race["id"]
            circuit = normalize_circuit(race.get("circuit"))
            if circuit not in counts:
                errors.append({"date": day, "raceId": rid, "code": "unknown-circuit"})
                continue
            counts[circuit]["expected"] += 1
            checked += 1
            try:
                result = verify_one(archive_dir / "saved-snapshots", rid,
                                    manifest["races"].get(rid), day=day,
                                    circuit=circuit, card_horses=race["horses"],
                                    verify_history=True)
            except (ValueError, OSError, KeyError, TypeError, MemoryError) as exc:
                counts[circuit]["failed"] += 1
                errors.append({"date": day, "raceId": rid,
                               "code": type(exc).__name__,
                               "reason": str(exc)[:150]})
                continue
            counts[circuit]["verified"] += 1
            counts[circuit]["runners"] += result["runnerRows"]
            h = result["historyAudit"]
            no_prior_cases.extend(h["noObservedPriorCases"])
            weight_cases.extend(h["missingCardWeightCases"])
            counts[circuit]["sidecarsVerified"] += h["careerSidecarsVerified"]
            counts[circuit]["priorRunsObserved"] += h["observedPriorRunRows"]
            counts[circuit]["runnersWithPriorRuns"] += h["runnersWithObservedPriorRuns"]
            counts[circuit]["nonPriorRows"] += h["sameOrFutureDirectRows"]
            counts[circuit]["invalidHistoryDates"] += h["invalidDirectDateRows"]
            if h["sameOrFutureDirectRows"] or h["invalidDirectDateRows"]:
                errors.append({"date": day, "raceId": rid,
                               "code": "bad-direct-history-date",
                               "sameOrFuture": h["sameOrFutureDirectRows"],
                               "invalid": h["invalidDirectDateRows"]})
            # Bounded list of verified proof samples, not unbounded copied horses.
            if len(sampled) < 10:
                sampled.append({"raceId": rid, "sha256": result["sha256"],
                                "historyRows": h["observedPriorRunRows"]})
    counts_out = {c: dict(counts[c]) for c in ("jra", "nar")}
    verified = sum(r.get("verified", 0) for r in counts_out.values())
    return {
        "schema": "arvexq-v3-full-saved-archive-audit-1",
        "calendarWindow": calendar_window([p.stem for p in chosen], archive_dir=archive_dir),
        "dateRange": [chosen[0].stem, chosen[-1].stem],
        "dateCount": days,
        "unpairedSavedDays": [{"date": d, "filePresence": "racecard-only" if d in card_days else "manifest-only"} for d in unpaired],
        "expectedRacecards": checked,
        "hashVerifiedRacecards": verified,
        "allIndexedSavedOriginalsVerified": verified == checked and not errors,
        "structurallyConsistentDays": structurally_consistent,
        "circuits": counts_out,
        "errors": errors,
        "sampleDigests": sampled,
        "runnerEvidenceTriage": summarize_evidence(no_prior_cases, weight_cases),
        "verifiedScope": "repository saved original gzip envelopes + embedded archived careers",
        "officialPublishedRacesVerified": False,
        "completeLifetimeHistoryVerified": False,
        "liveD1ReadbackVerified": False,
        "predictionStatus": "not-implemented",
    }
