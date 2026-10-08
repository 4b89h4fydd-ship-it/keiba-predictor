from __future__ import annotations

import asyncio
import copy
from typing import Any

from arvexq.databanks.registry import DataBankRegistry, registry
from arvexq.ingest.orchestrator import FetchResult, fetch_domain


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

    for key in ("recentRaces", "allPastRuns"):
        incoming = payload.get(key)
        if isinstance(incoming, list) and incoming:
            base = horse.get(key) or horse.get("recentRaces") or []
            merged = _merge_runs(base, incoming, cutoff=cutoff, limit=history_limit if key == "recentRaces" else max(history_limit, len(base) + len(incoming)))
            if merged and merged != horse.get(key):
                horse[key] = merged
                changed = True

    # Some adapters return the history list under a generic key.
    if domain == "horse_history" and isinstance(payload.get("history"), list):
        merged = _merge_runs(horse.get("recentRaces") or [], payload["history"], cutoff=cutoff, limit=history_limit)
        if merged and merged != horse.get("recentRaces"):
            horse["recentRaces"] = merged
            changed = True

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

    async def one(horse: dict[str, Any]) -> bool:
        changed = False
        async with sem:
            domains: list[tuple[str, set[str] | None]] = []
            if _needs_history(horse, cutoff=cutoff, limit=history_limit):
                domains.append(("horse_history", None))
            elif measured_feeds and _measured_horse_first3f_count(horse, cutoff, history_limit) < 2:
                # Full corner history still lacks measured per-horse early splits:
                # ask only the licensed split providers, not every official adapter.
                domains.append(("horse_history", measured_feeds))
            if _needs_pedigree(horse):
                domains.append(("pedigree", None))
            if _needs_connections(horse):
                domains.append(("jockey_trainer", None))

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
                    if not result.ok:
                        failures.append({"source": result.source, "domain": domain, "error": result.error or "failed"})
                        continue
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
        return changed

    flags = await asyncio.gather(*(one(h) for h in horses))
    changed_horses = sum(bool(x) for x in flags)

    pm = out.setdefault("preparedMeta", {})
    pm["supplementalSearch"] = {
        "version": "arvexq-multi-source-fallback-v1",
        "searchedHorses": len(horses),
        "changedHorses": changed_horses,
        "historyCompleteHorses": sum(_history_count(h) >= history_limit for h in horses),
        "measuredHorseFirst3FReadyHorses": sum(
            _measured_horse_first3f_count(h, cutoff, history_limit) >= 2
            for h in horses
        ),
        "measuredHorseFirst3FProviderCount": len(measured_feeds),
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
