from __future__ import annotations

import asyncio
import copy
from typing import Any

from arvexq.components.item_041.registry import DataBankRegistry, registry
from arvexq.components.item_041.orchestrator import FetchResult, fetch_domain
from arvexq.components.item_057.full_career import merge_career, audit_career, date_key

# Identity-verified career sources provide both observed runs and race-date
# start-count evidence. Track count-source outages separately for audit parity.
START_COUNT_SOURCES = frozenset({"netkeiba_verified_career"})


def _validated_early_timing(data: Any) -> dict[str, Any] | None:
    """Accept observed horse-specific timing only, not inferred race leader splits."""
    if not isinstance(data, dict):
        return None
    kind = str(data.get("sourceKind") or "")
    reference = str(data.get("sourceRef") or "").strip()
    if kind not in {"individual_sensor", "video_estimate"} or not reference:
        return None
    clean: dict[str, Any] = {"sourceKind": kind, "sourceRef": reference[:400]}
    intervals = {
        "first200mSeconds": (7.0, 25.0),
        "gateReactionSeconds": (0.05, 3.0),
        "acceleration0to100Mps2": (0.1, 10.0),
    }
    for key, (minimum, maximum) in intervals.items():
        val = data.get(key)
        if val is None or val == "":
            continue
        try:
            value = float(val)
        except (TypeError, ValueError):
            continue
        if minimum <= value <= maximum:
            clean[key] = value
    if not any(key in clean for key in intervals):
        return None
    return clean


def _present(value: Any) -> bool:
    return value not in (None, "", [], {}, "不明")


def _run_key(run: dict[str, Any]) -> tuple[str, str, int, int]:
    date = str(run.get("date") or run.get("raceDate") or "")
    track = str(run.get("track") or "")
    try:
        distance = int(float(run.get("distance") or 0))
    except (TypeError, ValueError):
        distance = 0
    try:
        race_no = int(float(run.get("raceNumber") or run.get("raceNo") or 0))
    except (TypeError, ValueError):
        race_no = 0
    return date, track, distance, race_no


def _merge_runs(existing: Any, incoming: Any, *, cutoff: str = "", limit: int = 5) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    order: list[tuple[str, str, int, int]] = []
    for raw in [*(existing or []), *(incoming or [])]:
        if not isinstance(raw, dict):
            continue
        date = str(raw.get("date") or raw.get("raceDate") or "")
        # Never supplement a pre-race model with the target race or future data.
        if cutoff and date and date >= cutoff:
            continue
        key = _run_key(raw)
        if key not in merged:
            merged[key] = copy.deepcopy(raw)
            order.append(key)
            continue
        row = merged[key]
        for field, value in raw.items():
            if field == "cornerPositions":
                # Five runs with incomplete first-turn positions are NOT five
                # usable pace samples. Fill missing positions from a fallback
                # source without erasing already known official positions.
                if isinstance(value, list) and value:
                    old_positions = row.get(field) if isinstance(row.get(field), list) else []
                    max_count = max(len(value), len(old_positions))
                    positions = []
                    for idx in range(max_count):
                        old = old_positions[idx] if idx < len(old_positions) else None
                        new = value[idx] if idx < len(value) else None
                        try:
                            valid_old = float(old) > 0
                        except (TypeError, ValueError):
                            valid_old = False
                        try:
                            valid_new = float(new) > 0
                        except (TypeError, ValueError):
                            valid_new = False
                        positions.append(old if valid_old else (new if valid_new else old))
                    if positions != old_positions:
                        row[field] = positions
            elif not _present(row.get(field)) and _present(value):
                row[field] = copy.deepcopy(value)
    rows = [merged[k] for k in order]
    rows.sort(key=lambda r: str(r.get("date") or r.get("raceDate") or ""), reverse=True)
    return rows[: max(1, int(limit or 5))]


def _history_count(horse: dict[str, Any]) -> int:
    runs = horse.get("allPastRuns") or horse.get("recentRaces") or []
    return len([r for r in runs if isinstance(r, dict)])


def _first_corner_coverage(horse: dict[str, Any], cutoff: str = "", limit: int = 5) -> int:
    """Count *historically valid* first-turn observations, not merely run rows."""
    runs = _merge_runs(
        horse.get("recentRaces") or [],
        horse.get("allPastRuns") or [],
        cutoff=cutoff,
        limit=limit,
    )
    good = 0
    for row in runs:
        corners = row.get("cornerPositions")
        if not isinstance(corners, list) or not corners:
            continue
        try:
            first = int(corners[0])
            field = int(row.get("fieldSize") or 0)
        except (ValueError, TypeError):
            continue
        if first > 0 and (field <= 0 or first <= field):
            good += 1
    return good


def _needs_history(horse: dict[str, Any], *, cutoff: str, limit: int) -> bool:
    # Requery even with five run rows if those rows lack useful early-pace data.
    # An additional source might be able to supply the missing corner places.
    runs = _merge_runs(
        horse.get("recentRaces") or [],
        horse.get("allPastRuns") or [],
        cutoff=cutoff,
        limit=limit,
    )
    return len(runs) < limit or _first_corner_coverage(horse, cutoff, limit) < min(3, len(runs))


def _needs_jra_margins(horse: dict[str, Any], cutoff: str) -> bool:
    """Zero seconds is valid winning evidence, not a missing value."""
    runs = merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), cutoff)[:5]
    return any(all(row.get(k) in (None, "") for k in
                   ("marginSeconds", "timeBehindWinner")) for row in runs)


def _needs_nar_margins(horse: dict[str, Any], cutoff: str) -> bool:
    """Seek *existing official result evidence* when no prior time margin was observed.

    One true measured margin suffices to make the NAR 60/40 score eligible for
    that horse. Never substitute finishing place, popularity, or neutral scores.
    A zero-second winner margin counts as valid evidence.
    """
    runs = merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), cutoff)[:5]
    if not runs:
        return False
    def measured(row: dict[str, Any]) -> bool:
        for key in ("marginSeconds", "timeBehindWinner"):
            value = row.get(key)
            try:
                if value not in (None, "") and 0 <= float(value) <= 30:
                    return True
            except (TypeError, ValueError, OverflowError):
                continue
        return False
    return not any(measured(run) for run in runs)


def _observed_sectional_rank_count(horse: dict[str, Any], cutoff: str = "", limit: int = 5) -> int:
    """Count actual prior-run sectional positions, not fabricated pace scores."""
    runs = _merge_runs(
        horse.get("recentRaces") or [],
        horse.get("allPastRuns") or [],
        cutoff=cutoff,
        limit=limit,
    )
    seen = 0
    for row in runs:
        value = next((row[k] for k in ("last3fRank", "last3FRank", "last600Rank", "上がり順位")
                      if row.get(k) not in (None, "", 0)), None)
        try:
            field = int(row.get("fieldSize") or 0)
            rank = float(value)
            if field > 1 and 1 <= rank <= field and rank.is_integer():
                seen += 1
        except (TypeError, ValueError):
            pass
    return seen


def _measured_horse_first3f_count(horse: dict[str, Any], cutoff: str = "", limit: int = 5) -> int:
    """Observed individual early-3F time only; never race-level pace figures."""
    runs = _merge_runs(
        horse.get("recentRaces") or [],
        horse.get("allPastRuns") or [],
        cutoff=cutoff,
        limit=limit,
    )
    valid = 0
    for row in runs:
        try:
            secs = float(row.get("horseFirst3FSeconds") or 0)
        except (TypeError, ValueError):
            secs = 0
        if 15 <= secs <= 90:
            valid += 1
    return valid


def _horse_early_timing_count(horse: dict[str, Any], cutoff: str = "", limit: int = 5) -> int:
    """Count dated, sourced horse-specific timing records, not race leader laps."""
    runs = _merge_runs(
        horse.get("recentRaces") or [], horse.get("allPastRuns") or [],
        cutoff=cutoff, limit=limit,
    )
    return sum(_validated_early_timing(row.get("earlyTiming")) is not None for row in runs)


def _needs_pedigree(horse: dict[str, Any]) -> bool:
    p = horse.get("pedigree") if isinstance(horse.get("pedigree"), dict) else {}
    return not (
        _present(p.get("sire"))
        or _present(horse.get("sire"))
        or _present(p.get("dam"))
        or _present(horse.get("dam"))
    )


def _needs_connections(horse: dict[str, Any]) -> bool:
    return not (
        isinstance(horse.get("jockeyStats"), dict)
        and horse.get("jockeyStats")
        and isinstance(horse.get("trainerStats"), dict)
        and horse.get("trainerStats")
    )


def _payload_dict(data: Any, domain: str) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    if domain == "horse_history" and isinstance(data, list):
        return {"recentRaces": data}
    return {}


def _apply_career_stats(horse: dict[str, Any], stats: Any, source: str, cutoff: str) -> bool:
    """Keep race-date-bound start-count evidence; disagreement is not evidence."""
    end = date_key(cutoff)
    if not isinstance(stats, dict) or stats.get("asOfRaceDate") != end or not isinstance(stats.get("starts"), int):
        return False
    incoming = copy.deepcopy(stats)
    incoming.setdefault("source", source)
    prev = horse.get("careerStartEvidence") if isinstance(horse.get("careerStartEvidence"), dict) else None
    if prev is None or prev.get("asOfRaceDate") != end or prev.get("source") == incoming["source"]:
        new = incoming
    elif prev.get("conflict"):
        return False
    elif (prev.get("starts"), prev.get("startDates")) == (incoming["starts"], incoming.get("startDates")):
        return False
    else:
        new = {"asOfRaceDate": end, "conflict": True,
               "sources": sorted({str(prev.get("source")), str(incoming["source"])}),
               "reportedStarts": sorted({prev.get("starts"), incoming["starts"]})}
    if new == prev:
        return False
    # Separate key: careerStats is a prediction-hash input, this is not.
    horse["careerStartEvidence"] = new
    return True


def _apply_payload(
    horse: dict[str, Any],
    data: Any,
    *,
    domain: str,
    source: str,
    cutoff: str,
    history_limit: int,
) -> bool:
    payload = _payload_dict(data, domain)
    if not payload:
        return False
    changed = False

    if domain == "horse_history" and history_limit > 5:
        incoming = [*(payload.get("recentRaces") or []), *(payload.get("allPastRuns") or []), *(payload.get("history") or [])]
        previous = [*(horse.get("allPastRuns") or []), *(horse.get("recentRaces") or [])]
        all_runs = merge_career(previous, incoming, cutoff)
        if all_runs and all_runs != horse.get("allPastRuns"):
            horse["allPastRuns"] = all_runs
            changed = True
        if all_runs and all_runs[:5] != horse.get("recentRaces"):
            horse["recentRaces"] = all_runs[:5]
            changed = True

    for key in (() if domain == "horse_history" and history_limit > 5 else ("recentRaces", "allPastRuns")):
        incoming = payload.get(key)
        if isinstance(incoming, list) and incoming:
            base = horse.get(key) or horse.get("recentRaces") or []
            merged = _merge_runs(base, incoming, cutoff=cutoff, limit=history_limit if key == "recentRaces" else max(history_limit, len(base) + len(incoming)))
            if merged and merged != horse.get(key):
                horse[key] = merged
                changed = True

    # Some adapters return the history list under a generic key.
    if domain == "horse_history" and history_limit <= 5 and isinstance(payload.get("history"), list):
        merged = _merge_runs(horse.get("recentRaces") or [], payload["history"], cutoff=cutoff, limit=history_limit)
        if merged and merged != horse.get("recentRaces"):
            horse["recentRaces"] = merged
            changed = True

    if domain == "horse_history":
        changed = _apply_career_stats(horse, payload.get("careerStartEvidence"), source, cutoff) or changed

    for key in (
        "pedigree", "sire", "dam", "damsire",
        "jockeyStats", "trainerStats", "jockeyProfile", "trainerProfile",
        "prizeMoneyAtRace", "representativeRun", "jumpStats", "obstacleStats",
    ):
        value = payload.get(key)
        if not _present(horse.get(key)) and _present(value):
            horse[key] = copy.deepcopy(value)
            changed = True

    if changed:
        sources = horse.setdefault("_supplementalSources", [])
        if source not in sources:
            sources.append(source)
        horse["_sourceCount"] = max(int(horse.get("_sourceCount") or 1), 1 + len(sources))
    return changed


async def enrich_race_missing(
    detail: dict[str, Any],
    *,
    bank_registry: DataBankRegistry = registry,
    history_limit: int = 5,
    max_parallel_horses: int = 4,
) -> dict[str, Any]:
    """Exhaust every registered provider for missing pre-race evidence.

    The fast UI path does not call this. It belongs to the prefetch/heavy lane.
    One provider failure is isolated; other providers continue and richer existing
    values are never overwritten by an empty/thinner response.
    """
    if not isinstance(detail, dict):
        return detail
    out = copy.deepcopy(detail)
    horses = [h for h in (out.get("horses") or []) if isinstance(h, dict)]
    if not horses:
        return out

    circuit = "JRA" if str(out.get("circuit") or "") in {"中央", "JRA"} else "NAR"
    cutoff = str(out.get("date") or "")
    sem = asyncio.Semaphore(max(1, int(max_parallel_horses or 1)))
    failures: list[dict[str, str]] = []
    changed_horses = 0
    measured_feeds = {
        src.name for src in bank_registry.providers("horse_history", circuit=circuit)
        if src.supplement_complete_history
    }

    evidence_registered = any(
        src.name in START_COUNT_SOURCES
        for src in bank_registry.providers("horse_history", circuit=circuit)
    )

    async def one(horse: dict[str, Any]) -> bool:
        changed = False
        async with sem:
            domains: list[tuple[str, set[str] | None]] = []
            previous_audit = horse.get("_careerHistoryAudit") or {}
            full_search = history_limit > 5 and (
                previous_audit.get("requestedAtRaceDate") != date_key(cutoff)
                # A successful HTTP fetch is not equivalent to a verified career.
                # If a source returned runs but no date-bound start count, or
                # only a partial lifetime, the next heavy prefetch must retry.
                or previous_audit.get("complete") is not True
                or bool(previous_audit.get("failedProviders"))
                or bool(previous_audit.get("failedEvidenceProviders"))
                or (evidence_registered and previous_audit.get("reportedStarts") is None
                    and not previous_audit.get("evidenceAttempted"))
                or not previous_audit.get("fetchAttempted", bool(previous_audit.get("providersAttempted")))
            )
            if full_search or _needs_history(horse, cutoff=cutoff, limit=min(5, history_limit)):
                domains.append(("horse_history", None))
            elif circuit == "JRA" and _needs_jra_margins(horse, cutoff) and bank_registry.get("jra_official_prior_results"):
                # Missing margins need the result adapter, not a redundant card/profile fetch.
                domains.append(("horse_history", {"jra_official_prior_results"} | measured_feeds))
            elif circuit == "NAR" and _needs_nar_margins(horse, cutoff) and bank_registry.get("nar_official_past_results"):
                # The original five runs can have positions yet no winner-time gap.
                # Use the ALREADY REGISTERED official NAR result adapter only;
                # never add a parallel scraper or fall back to legacy scores.
                domains.append(("horse_history", {"nar_official_past_results"}))
            elif measured_feeds and (
                _measured_horse_first3f_count(horse, cutoff, history_limit) < 2
                or _horse_early_timing_count(horse, cutoff, history_limit) < 2
                or (
                    _observed_sectional_rank_count(horse, cutoff, history_limit) < 2
                    and horse.get("_sectionalFetchAttemptedAt") != date_key(cutoff)
                )
            ):
                # Only licensed measured-history providers. Limit retry for missing
                # sectional rank to once per target race date; otherwise a feed
                # with no sectional observations would be refetched endlessly.
                domains.append(("horse_history", measured_feeds))
            if _needs_pedigree(horse):
                domains.append(("pedigree", None))
            if _needs_connections(horse):
                domains.append(("jockey_trainer", None))

            if any(domain == "horse_history" and only_sources == measured_feeds
                   for domain, only_sources in domains):
                horse["_sectionalFetchAttemptedAt"] = date_key(cutoff)
                changed = True

            history_sources: list[str] = []
            history_failed: list[str] = []
            evidence_failed: list[str] = []
            for domain, only_sources in domains:
                results = await fetch_domain(
                    domain,
                    horse,
                    out,
                    history_limit,
                    circuit=circuit,
                    bank_registry=bank_registry,
                    only_sources=only_sources,
                )
                for result in results:
                    if domain == "horse_history":
                        history_sources.append(result.source)
                    if not result.ok:
                        if domain == "horse_history":
                            (evidence_failed if result.source in START_COUNT_SOURCES
                             else history_failed).append(result.source)
                        failures.append({"source": result.source, "domain": domain, "error": result.error or "failed"})
                        continue
                    if domain == "horse_history" and isinstance(result.data, dict):
                        reported = result.data.get("historyFetchErrors")
                        if isinstance(reported, list) and reported:
                            history_failed.append(result.source)
                            failures.extend({"source": result.source, "domain": domain,
                                             "error": str(item)} for item in reported)
                    if result.data in (None, "", [], {}):
                        continue
                    changed = _apply_payload(
                        horse,
                        result.data,
                        domain=domain,
                        source=result.source,
                        cutoff=cutoff,
                        history_limit=history_limit,
                    ) or changed
            if history_limit > 5:
                audit = audit_career(horse, cutoff, history_limit, history_sources)
                audit["fetchAttempted"] = bool(history_sources)
                audit["evidenceAttempted"] = any(x in START_COUNT_SOURCES for x in history_sources)
                audit["failedProviders"] = sorted(set(history_failed))
                audit["failedEvidenceProviders"] = sorted(set(evidence_failed))
                if audit != horse.get("_careerHistoryAudit"):
                    horse["_careerHistoryAudit"] = audit
                    changed = True
        return changed

    flags = await asyncio.gather(*(one(h) for h in horses))
    changed_horses = sum(bool(x) for x in flags)

    pm = out.setdefault("preparedMeta", {})
    pm["supplementalSearch"] = {
        "version": "arvexq-multi-source-fallback-v1",
        "searchedHorses": len(horses),
        "changedHorses": changed_horses,
        "historyCompleteHorses": sum((h.get("_careerHistoryAudit") or {}).get("complete") is True for h in horses),
        "careerObservedHorses": sum(_history_count(h) > 0 for h in horses),
        "careerIncompleteHorses": sum(not (h.get("_careerHistoryAudit") or {}).get("complete") for h in horses),
        "measuredHorseFirst3FReadyHorses": sum(
            _measured_horse_first3f_count(h, cutoff, history_limit) >= 2
            for h in horses
        ),
        "measuredHorseFirst3FProviderCount": len(measured_feeds),
        "individualEarlyTimingReadyHorses": sum(
            _horse_early_timing_count(h, cutoff, history_limit) >= 2 for h in horses
        ),
        "individualEarlyTimingProviderCount": len(measured_feeds),
        "firstCornerEvidenceReadyHorses": sum(
            _first_corner_coverage(h, cutoff, history_limit) >= min(3, history_limit)
            for h in horses
        ),
        "firstCornerSamplesByHorse": {
            str(h.get("horseNumber") or index + 1): _first_corner_coverage(
                h, cutoff, history_limit
            )
            for index, h in enumerate(horses)
        },
        "providers": bank_registry.capability_map(),
        "failures": failures[:20],
    }
    return out


def enrich_race_missing_sync(
    detail: dict[str, Any],
    *,
    bank_registry: DataBankRegistry = registry,
    history_limit: int = 5,
    max_parallel_horses: int = 4,
) -> dict[str, Any]:
    return asyncio.run(
        enrich_race_missing(
            detail,
            bank_registry=bank_registry,
            history_limit=history_limit,
            max_parallel_horses=max_parallel_horses,
        )
    )
