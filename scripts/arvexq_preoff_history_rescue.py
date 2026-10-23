#!/usr/bin/env python3
"""Bounded isolated official-source historical rescue for upcoming D1 races.

Only called BEFORE scheduled post by the existing pre-race sealer. Returns
observed prior-run facts; it never creates marks, opinions or bets.
"""
from __future__ import annotations

import copy
import json
import sys
from datetime import datetime

from arvexq.prediction.prerace_archive import JST, post_at


def active_identity(detail):
    return {int(h["horseNumber"]): str(h.get("name") or "").strip()
            for h in detail.get("horses") or []
            if isinstance(h, dict) and type(h.get("horseNumber")) is int
            and not h.get("scratched") and not h.get("withdrawn")
            and not any(s in str(h.get("status") or "") for s in ("取消", "除外", "欠場"))}


def accept_observed_rescue(original, candidate, *, now):
    """Fail closed on identity/roster drift, future runs and stale acquisition."""
    if not isinstance(original, dict) or not isinstance(candidate, dict):
        raise ValueError("full source and candidate are required")
    if original.get("id") != candidate.get("id") or original.get("date") != candidate.get("date"):
        raise ValueError("race/date mismatch")
    post = post_at(original)
    if post is None or now.astimezone(JST) >= post:
        raise ValueError("post-off rescue is forbidden")
    if post_at(candidate) != post:
        raise ValueError("scheduled post changed")
    a, b = active_identity(original), active_identity(candidate)
    if not a or a != b:
        raise ValueError("horse number/name/active-roster mismatch")
    date = str(original["date"])
    candidate_horses = {int(h["horseNumber"]): h for h in candidate.get("horses") or []
                        if isinstance(h, dict) and type(h.get("horseNumber")) is int}
    out = copy.deepcopy(original)
    improved = 0
    for horse in out.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        number = horse.get("horseNumber")
        other = candidate_horses.get(number, {})
        existing = horse.get("allPastRuns") or horse.get("recentRaces") or []
        new = other.get("allPastRuns") or other.get("recentRaces") or []
        if not isinstance(new, list):
            raise ValueError("invalid candidate historical field")
        dated = []
        for run in new:
            if not isinstance(run, dict):
                raise ValueError("invalid historical run")
            day = str(run.get("date") or run.get("raceDate") or "")[:10]
            # A historical result without an actual identifiable date is NOT evidence.
            if not day or day >= date or len(day) != 10:
                continue
            dated.append(copy.deepcopy(run))
        if len(dated) > len(existing):
            horse["allPastRuns"] = dated
            horse["recentRaces"] = dated[:5]
            improved += 1
    if not improved:
        raise ValueError("providers returned no additional dated career evidence")
    return out


def main():
    original = json.load(sys.stdin)
    if not isinstance(original, dict):
        raise SystemExit("invalid race")
    now = datetime.now(JST)
    if post_at(original) is None or now >= post_at(original):
        raise SystemExit("post-off provider lookup prohibited")
    # Use the existing production registry bridge and registered providers.
    # The removed authorized_feeds module is not part of this repository.
    import app
    from arvexq.databanks.legacy_bridge import register_legacy_sources
    from arvexq.ingest.fallback_enrichment import enrich_race_missing_sync
    register_legacy_sources(vars(app))
    candidate = enrich_race_missing_sync(original, history_limit=100,
                                          max_parallel_horses=4)
    accepted = accept_observed_rescue(original, candidate, now=datetime.now(JST))
    json.dump(accepted, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
