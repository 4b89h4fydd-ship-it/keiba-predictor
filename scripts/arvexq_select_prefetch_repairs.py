#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select only D1 race details that actually need full-prefetch repair.

Full Prefetch may build >100 MB for a full day. Rewriting every rich race on
each run overloads the Worker/D1 write path. Existing rich race details are
left in place; missing/thin details are republished from the freshly prepared
payload. Summaries remain cheap and are always refreshed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.pipeline.persisted_inputs import _career_rows, _history_observations_retained


def read(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def meaningful(v: Any) -> bool:
    return v not in (None, "", [], {})


def named_roster(detail: Any) -> dict[int, str]:
    """Valid named runners keyed by the canonical horse number."""
    result: dict[int, str] = {}
    if not isinstance(detail, dict):
        return result
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        try:
            number = int(horse.get("horseNumber") or 0)
        except (TypeError, ValueError):
            continue
        name = str(horse.get("name") or "").strip()
        if number > 0 and name:
            result[number] = name
    return result


def rich(detail: Any) -> bool:
    if not isinstance(detail, dict) or not detail.get("id"):
        return False
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    roster = named_roster(detail)
    if len(roster) < 2 or len(roster) != len(horses):
        return False
    pm = detail.get("preparedMeta") if isinstance(detail.get("preparedMeta"), dict) else {}
    return bool(pm.get("diagnosisReady")) or any(
        meaningful(detail.get(k))
        for k in ("preRacePrediction", "aiEvaluation", "pace", "pacePrediction", "volatility")
    )


def repair_reason(prepared: Any, existing: Any, *, facts_only: bool = False) -> str:
    """A rich-but-truncated D1 card also needs repair; never drop known runners."""
    if not isinstance(prepared, dict) or not prepared.get("id"):
        return ""
    if existing is None:
        return "missing"
    if not isinstance(existing, dict) or str(existing.get("id") or "") != str(prepared["id"]):
        return "race_id_mismatch"
    new = named_roster(prepared)
    old = named_roster(existing)
    if len(new) > len(old) and set(old).issubset(new):
        return "roster_incomplete"
    # The initial D1 facts phase is collection-only: model version, marks,
    # diagnosis hash and old prediction status are not factual differences.
    # They are handled by the independent post-readback analysis phase below.
    # A race with full saved facts must not be rewritten 40 times solely due
    # to stale/crossing pre-off opinions: repeated large writes can hit 1102.
    if facts_only:
        old_rows = [h for h in existing.get("horses") or [] if isinstance(h, dict)]
        if len(old) < 2 or len(old) != len(old_rows):
            return "roster_incomplete"
        expected_size = prepared.get("fieldSize")
        if type(expected_size) is int and expected_size > len(old):
            return "roster_incomplete"
        for h in prepared.get("horses") or []:
            if not isinstance(h, dict):
                continue
            no = int(h.get("horseNumber") or 0)
            old_h = next((v for v in old_rows if int(v.get("horseNumber") or 0) == no), {})
            try:
                actual_runs = _career_rows(old_h, str(existing.get("date") or ""))
                observed_runs = _career_rows(h, str(prepared.get("date") or ""))
            except (ValueError, TypeError, KeyError, RuntimeError):
                return "career_archive_invalid"
            if (len(observed_runs) > len(actual_runs)
                    or not _history_observations_retained(observed_runs, actual_runs)):
                return "career_history_missing_observations"
        return ""
    # A rich old card is not equivalent to the current learned forecast.
    # Never skip replacement solely because the retired analysis was ready.
    new_version = str(prepared.get("predictionModelVersion") or "")
    old_version = str(existing.get("predictionModelVersion") or "")
    if new_version.startswith("arvexq-learned-whole-career"):
        if new_version != old_version:
            return "replacement_model_changed"
        new_marks = {int(h.get("horseNumber") or 0): str((h.get("integratedEvaluation") or {}).get("mark") or "")
                     for h in prepared.get("horses") or [] if isinstance(h, dict)}
        old_marks = {int(h.get("horseNumber") or 0): str((h.get("integratedEvaluation") or {}).get("mark") or "")
                     for h in existing.get("horses") or [] if isinstance(h, dict)}
        if new_marks != old_marks:
            return "replacement_marks_changed"
    if prepared.get("legacyPresentationDisabled") and (
        existing.get("predictionStatus") != "new-model-unavailable"
        or existing.get("recommendedBetPlan") != prepared.get("recommendedBetPlan")
    ):
        return "retired_forecast_still_published"
    if not rich(existing):
        return "thin"
    # Facts are saved first. A later valid analysis must be published even
    # when the earlier fact snapshot already had a complete runner list.
    new_pm = prepared.get("preparedMeta") if isinstance(prepared.get("preparedMeta"), dict) else {}
    old_pm = existing.get("preparedMeta") if isinstance(existing.get("preparedMeta"), dict) else {}
    if new_pm.get("diagnosisReady") and (
        not old_pm.get("diagnosisReady")
        or (new_pm.get("analysisInputHash") and
            new_pm.get("analysisInputHash") != old_pm.get("analysisInputHash"))
        or (prepared.get("predictionModelVersion") and
            prepared.get("predictionModelVersion") != existing.get("predictionModelVersion"))
    ):
        return "persisted_prediction_changed"
    old_horses = {int(h.get("horseNumber") or 0): h for h in existing.get("horses") or [] if isinstance(h, dict)}
    for horse in prepared.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        old_h = old_horses.get(int(horse.get("horseNumber") or 0), {})
        try:
            new_runs = _career_rows(horse, str(prepared.get("date") or ""))
            old_runs = _career_rows(old_h, str(existing.get("date") or ""))
        except (ValueError, TypeError, KeyError, RuntimeError):
            return "career_archive_invalid"
        if len(new_runs) > len(old_runs) or not _history_observations_retained(new_runs, old_runs):
            return "career_history_missing_observations"
    return ""


def retain_frozen_mass_context(prepared: dict[str, Any], existing: Any) -> dict[str, Any] | None:
    """Keep exact previously frozen evidence on a history-only repair.

    The canonical collector does not create predictions. Reuse a historical
    forecast only when its original frozen matrix is the same matrix already
    present in the proposed repair; otherwise leave the D1 original untouched.
    """
    snapshot = prepared.get("massFeatureSnapshot")
    if not isinstance(snapshot, dict) or isinstance(prepared.get("preRacePrediction"), dict):
        return prepared
    if not isinstance(existing, dict):
        return None
    original_prediction = existing.get("preRacePrediction")
    old_snapshot = existing.get("massFeatureSnapshot")
    old_archive = existing.get("massFeatureArchive")
    matching_hash = str(snapshot.get("featureHash") or "")
    old_hash = (old_snapshot.get("featureHash") if isinstance(old_snapshot, dict)
                else old_archive.get("featureHash") if isinstance(old_archive, dict) else None)
    if (not isinstance(original_prediction, dict) or not matching_hash
            or matching_hash != old_hash
            or str(prepared.get("id")) != str(existing.get("id"))
            or str(prepared.get("date")) != str(existing.get("date"))
            or str(snapshot.get("raceId")) != str(prepared.get("id"))
            or str(snapshot.get("date")) != str(prepared.get("date"))):
        return None
    # The prediction is a byte-for-byte saved original for transport integrity,
    # not a freshly published model output.
    return {**prepared, "preRacePrediction": original_prediction}


MORNING_FIELDS = ("morningPickVersion", "morningPickFixedAt", "morningPickScope",
                  "morningSelected", "morningSelectedScore", "morningSpecial")


def _morning_from(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    for field in ("volatility", "environmentMeta"):
        node = row.get(field) if isinstance(row.get(field), dict) else {}
        manifest = node.get("morningPicks")
        if isinstance(manifest, dict) and manifest.get("version") == "v1" and manifest.get("fixedAt"):
            return manifest
    if row.get("morningPickVersion") == "v1" and row.get("morningPickFixedAt"):
        return {
            "version": "v1",
            "fixedAt": row["morningPickFixedAt"],
            "scope": row.get("morningPickScope"),
            "selected": bool(row.get("morningSelected")),
            "selectedScore": row.get("morningSelectedScore") or 0,
            "special": bool(row.get("morningSpecial")),
        }
    return None


def keep_original_morning_picks(fresh: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    """First server-published manifest wins; later odds/detail updates cannot change it."""
    row = dict(fresh)
    manifest = _morning_from(prior) or _morning_from(row)
    if manifest:
        fields = {
            "morningPickVersion": "v1",
            "morningPickFixedAt": manifest["fixedAt"],
            "morningPickScope": manifest.get("scope"),
            "morningSelected": manifest.get("selected") is True,
            "morningSelectedScore": manifest.get("selectedScore") or 0,
            "morningSpecial": manifest.get("special") is True,
        }
        row.update(fields)
        for field in ("volatility", "environmentMeta"):
            row[field] = {**(row.get(field) if isinstance(row.get(field), dict) else {}),
                          "morningPicks": manifest}
    return row


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prepared", required=True)
    p.add_argument("--current", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--facts-only", action="store_true", help="Repair only official roster/history facts; predictions are a later phase")
    args = p.parse_args()

    prepared = read(args.prepared)
    current = read(args.current)
    current_summaries = {
        str(r.get("id")): r for r in (current.get("races") or [])
        if isinstance(r, dict) and r.get("id")
    }
    prepared["summaries"] = [
        keep_original_morning_picks(r, current_summaries.get(str(r.get("id") or "")))
        for r in (prepared.get("summaries") or []) if isinstance(r, dict)
    ]
    current_by_id = {
        str(d.get("id")): d
        for d in (current.get("details") or [])
        if isinstance(d, dict) and d.get("id")
    }
    wanted = [
        keep_original_morning_picks(
            d, current_by_id.get(str(d.get("id"))) or current_summaries.get(str(d.get("id")))
        )
        for d in (prepared.get("details") or [])
        if isinstance(d, dict) and d.get("id")
    ]

    selected: list[dict[str, Any]] = []
    reasons: list[dict[str, str]] = []
    for detail in wanted:
        rid = str(detail.get("id") or "")
        old = current_by_id.get(rid)
        new_roster = named_roster(detail)
        old_roster = named_roster(old)
        # Even a rich cached race must not be downgraded when the new source
        # loses a horse or supplies conflicting race numbers.
        if old_roster and not set(old_roster).issubset(new_roster):
            reasons.append({"race_id": rid, "reason": "source_roster_missing_known_horses"})
            continue
        reason = repair_reason(detail, old, facts_only=args.facts_only)
        if reason:
            if len(new_roster) < 2:
                reasons.append({"race_id": rid, "reason": "source_missing_named_runners"})
                continue
            preserved = retain_frozen_mass_context(detail, old)
            if preserved is None:
                reasons.append({"race_id": rid, "reason": "frozen_mass_context_not_verified"})
                continue
            selected.append(preserved)
            reasons.append({"race_id": rid, "reason": reason})

    meta = dict(prepared.get("meta") or {})
    meta.update({
        "source": "github-actions-full-prefetch-repair-only-v1",
        "prepared_detail_count": len(wanted),
        "existing_detail_count": len(current_by_id),
        "repair_detail_count": len(selected),
    })
    out = {
        "summaries": prepared.get("summaries") or [],
        "details": selected,
        "meta": meta,
    }
    report = {
        "prepared": len(wanted),
        "existing": len(current_by_id),
        "existing_rich": sum(1 for d in current_by_id.values() if rich(d)),
        "repair_count": len(selected),
        "repairs": reasons,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "PREFETCH_REPAIR_SELECTION",
        f"prepared={report['prepared']}",
        f"existing={report['existing']}",
        f"existing_rich={report['existing_rich']}",
        f"repair_count={report['repair_count']}",
    )
    for item in reasons[:30]:
        print("PREFETCH_REPAIR", item["race_id"], item["reason"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
