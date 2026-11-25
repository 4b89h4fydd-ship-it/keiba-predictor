"""Enrich already-computed racing forecasts with read-only evidence.

This must execute AFTER prediction computation. Evidence annotations never
replace pre-race marks, dynamic odds, seals, or the frozen morning race list.
"""
from __future__ import annotations
from typing import Any

from arvexq.prediction.sectional_profile import profile
from arvexq.prediction.bias_provenance import provenance
from arvexq.prediction.observed_evidence import RUN_KEYS, attach_model_evidence

# Bumped whenever the evidence computation changes, so the analyze stage
# can tell a detail decorated by older logic apart from a current one and
# re-analyze it once (scripts/arvexq_prefetch._analysis_current).
# v2: past-run margins are first completed from the system's own stored
# result records (arvexq.prediction.margin_completion), so details whose
# evidence was attached under v1 can hold margins that are now computable.
# v3: a horse with no past runs gains a "trial" factors item when the
# day's v8 extras provenance carries its official ability-trial pass
# record (trialSpd2Supplements), so a debutant whose only verified
# evidence is its trial is not rendered evidence-empty.
RESEARCH_EVIDENCE_VERSION = "arvexq-race-intelligence-v3"


def career_coverage(horse: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    """Compact, read-only acquisition/completeness state shared with the UI."""
    from arvexq.career_missing import build_career_analysis
    a = build_career_analysis(horse, detail)
    ev = a.get("acquisition_evidence") or {}
    return {
        "version": "arvexq-career-coverage-ui-v1",
        "state": a.get("career_state"), "acquisition": a.get("acquisition_status"),
        "fields": a.get("field_completeness"), "dataLimitation": a.get("data_limitation"),
        "eligibleRuns": a.get("eligible_dated_runs"), "analyzedRuns": a.get("analyzed_runs"),
        "reportedStarts": ev.get("reportedStarts"), "reportedStartsSource": ev.get("reportedStartsSource"),
        "reason": ev.get("reason"), "missingFields": a.get("missing_fields") or [],
        "unusableRecords": a.get("unusable_dated_records"),
    }


# ---------------------------------------------------------------------------
# Official ability-trial evidence for horses with no past runs.
#
# A first starter has no past runs, so the observed mineta/margin factors
# stay unavailable and the horse renders as evidence-empty ("unevaluated")
# even when it holds a verified official ability-trial pass. The nightly
# extras chain already matches those passes and records them, with full
# grounds, in the day's v8 extras provenance block
# (``trialSpd2Supplements``: supplemented entries, plus matched entries
# that only lacked a conversion par). attach_evidence reads that block
# for the detail's own race and surfaces the pass as a dedicated
# ``trial`` factors item. The item is a factual record (date / track /
# distance / raw time / pass), never a converted ability score: the raw
# trial time is NOT turned into spd2 or any rating here, and the item is
# kept apart from the 60/40 model items (no weight, distinct key/label).
# ---------------------------------------------------------------------------

_TRIAL_CACHE: dict[str, dict[str, dict[int, dict[str, Any]]]] = {}


def _trial_info_from_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(entry, dict) or not entry.get("trial_date"):
        return None
    try:
        time_seconds = float(entry.get("trial_time_seconds"))
        distance = int(entry.get("trial_distance"))
    except (TypeError, ValueError):
        return None
    return {
        "date": str(entry.get("trial_date")),
        "track": entry.get("trial_track"),
        "distance": distance,
        "timeSeconds": time_seconds,
        "passed": True,  # the supplement only ever records pass rows
        "source": entry.get("trial_source"),
        "sourceRef": entry.get("trial_source_ref"),
    }


def trial_records_from_extras_payload(
    payload: dict[str, Any], race_id: str
) -> dict[int, dict[str, Any]]:
    """{horseNumber: trial info} for one race from an extras payload.

    Reads ``provenance[<date>].trialSpd2Supplements`` (a flat
    ``provenance.trialSpd2Supplements`` is also accepted). Both the
    supplemented horses and the matched-but-unconverted ones carry the
    full trial grounds; both are official pass records.
    """
    out: dict[int, dict[str, Any]] = {}
    if not isinstance(payload, dict):
        return out
    prov = payload.get("provenance") or {}
    block = None
    dated = prov.get(str(payload.get("date") or ""))
    if isinstance(dated, dict):
        block = dated.get("trialSpd2Supplements")
    if not isinstance(block, dict):
        block = prov.get("trialSpd2Supplements")
    if not isinstance(block, dict):
        return out
    entries = list(block.get("horses") or []) + list(block.get("notSupplemented") or [])
    for entry in entries:
        if not isinstance(entry, dict) or str(entry.get("race") or "") != str(race_id):
            continue
        info = _trial_info_from_entry(entry)
        if info is None:
            continue
        try:
            out[int(entry.get("number"))] = info
        except (TypeError, ValueError):
            continue
    return out


def _extras_path_for(date: str) -> Any:
    import os
    from pathlib import Path

    override = os.environ.get("ARVEXQ_V8_EXTRAS_DIR")
    if override:
        return Path(override) / f"{date}.json"
    # arvexq/prediction/race_intelligence.py -> repo root is parents[2].
    return Path(__file__).resolve().parents[2] / "rewrite" / "data" / "v8_extras" / f"{date}.json"


def _trial_records_for(detail: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Trial records for this detail's race, or {} when none are on hand.

    Sources, in order: records a lane already stamped onto the detail
    (``trialEvidenceRecords``, a list of supplement-style entries), then
    the day's v8 extras file in the repository. Any failure returns {}
    (evidence decoration must never block delivery).
    """
    stamped = detail.get("trialEvidenceRecords")
    if isinstance(stamped, list):
        out: dict[int, dict[str, Any]] = {}
        for entry in stamped:
            info = _trial_info_from_entry(entry)
            if info is None:
                continue
            try:
                out[int(entry.get("number"))] = info
            except (TypeError, ValueError):
                continue
        return out
    date = str(detail.get("date") or "")
    race_id = str(detail.get("id") or "")
    if not date or not race_id:
        return {}
    try:
        path = _extras_path_for(date)
        key = f"{date}|{path}"
        cached = _TRIAL_CACHE.get(key)
        if cached is None:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
            cached = {}
            prov = payload.get("provenance") or {}
            dated = prov.get(str(payload.get("date") or "")) or {}
            block = dated.get("trialSpd2Supplements") or prov.get("trialSpd2Supplements") or {}
            entries = list(block.get("horses") or []) + list(block.get("notSupplemented") or [])
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                info = _trial_info_from_entry(entry)
                if info is None:
                    continue
                try:
                    cached.setdefault(str(entry.get("race") or ""), {})[int(entry.get("number"))] = info
                except (TypeError, ValueError):
                    continue
            _TRIAL_CACHE[key] = cached
        return dict(cached.get(race_id) or {})
    except Exception:
        return {}


def _has_past_runs(horse: dict[str, Any]) -> bool:
    return any(isinstance(horse.get(k), list) and len(horse[k]) > 0 for k in RUN_KEYS)


def _trial_item(info: dict[str, Any]) -> dict[str, Any]:
    """The dedicated factors item for an official ability-trial pass.

    ``value`` is the raw measured trial time in seconds (the UI coverage
    counter only credits items whose value is a finite number); it is a
    recorded fact, not a converted score — ``valueKind`` says so, and the
    measurements spell the grounds out in the research card.
    """
    t = float(info["timeSeconds"])
    time_text = f"{t}秒" if t != int(t) else f"{int(t)}秒"
    return {
        "key": "trial",
        "label": "能試",
        "available": True,
        "value": t,
        "valueKind": "trial-time-seconds",
        "measurements": [
            {"key": "実施日", "value": str(info.get("date") or "")},
            {"key": "競馬場", "value": str(info.get("track") or "")},
            {"key": "距離", "value": f"{int(info['distance'])}m"},
            {"key": "タイム", "value": time_text},
            {"key": "結果", "value": "合格"},
        ],
        "trial": {
            "date": info.get("date"),
            "track": info.get("track"),
            "distance": info.get("distance"),
            "timeSeconds": t,
            "passed": True,
            "source": info.get("source"),
            "sourceRef": info.get("sourceRef"),
        },
    }


def attach_evidence(detail: dict[str, Any], trial_records: dict[int, dict[str, Any]] | None = None) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return detail
    if trial_records is None:
        try:
            trial_records = _trial_records_for(detail)
        except Exception:
            trial_records = {}
    # Compute the observed mineta/margin evidence from past runs first; the
    # factors card below only reads it. This is evidence decoration after
    # prediction computation and never feeds marks or probabilities.
    try:
        attach_model_evidence(detail)
    except Exception:
        pass  # evidence decoration must never block delivery
    detail["biasProvenance"] = provenance(detail)
    count = 0
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        if not horse.get("horseNumber"):
            continue
        try:
            horse["careerCoverage"] = career_coverage(horse, detail)
        except Exception as exc:  # evidence decoration must never block delivery
            horse["careerCoverage"] = {"version": "arvexq-career-coverage-ui-v1", "state": "acquisition-unverified",
                                       "acquisition": "unverified", "reason": f"coverage-error:{type(exc).__name__}"}
        from arvexq.prediction.observed_model import model_version
        evidence = (horse.get("integratedEvaluation") or {}).get("narModelEvidence") or {}
        items = [
            {"key": "mineta", "weight": .60, "value": evidence.get("mineta"),
             "available": evidence.get("mineta") is not None},
            {"key": "margin", "weight": .40, "value": evidence.get("margin"),
             "available": evidence.get("margin") is not None}
        ]
        # A debutant's official ability-trial pass is real evidence even
        # though it is not a past run: surface it as its own item so the
        # horse is not rendered evidence-empty. Horses with past runs
        # keep the past-run factors only (a trial is not race history).
        try:
            number = int(horse.get("horseNumber") or 0)
        except (TypeError, ValueError):
            number = 0
        trial_info = trial_records.get(number) if number else None
        if trial_info is not None and not _has_past_runs(horse):
            items.append(_trial_item(trial_info))
        horse["researchEvidence"] = {
            "factors": {
                "version": model_version(detail),
                "items": items,
                "calibrated": False,
                "note": "Observed 60/40 relative model scores are not verified hit probabilities.",
            },
            "sectionals": profile(horse, detail),
            "status": "jra-observed-official-proofs" if str(detail.get("circuit") or "") in ("中央", "JRA", "central") else "nar-observed-only",
        }
        count += 1
    detail["researchEvidenceVersion"] = RESEARCH_EVIDENCE_VERSION
    detail["researchEvidenceHorses"] = count
    return detail
