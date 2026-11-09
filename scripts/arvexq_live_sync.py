#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARVEXQ lightweight live-sync lane.

FULL PREFETCH owns stable card/analysis data. RESULT REPAIR owns long-tail
result misses. LIVE SYNC reads the rich D1 detail as its merge base and changes
volatile fields only. Prediction is recomputed only before post time and only
when an analysis-relevant live input (body weight/scratch/weather/going) changed.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from arvexq.pipeline.fingerprints import analysis_input_hash
from arvexq.ingest.official_changes import collect_nar_changes
from arvexq.ingest.official_course_feeds import fetch_course_events
from arvexq.prediction.official_course_revision import pre_off_change, official_event
from arvexq.prediction.user_approved_model_revision import enabled as user_revision_enabled, update_marks as user_update_marks
from arvexq.infra.live_delta_guard import requires_full_write
from arvexq.prediction.prerace_archive import post_at

JST = timezone(timedelta(hours=9))
D1_BASE = os.getenv("CLOUDFLARE_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
LIVE_HORSE_FIELDS = (
    "winOdds", "popularity", "bodyWeight", "bodyWeightChange",
    "status", "scratched", "oddsSource", "oddsForecast",
    "placeOddsLow", "placeOddsHigh",
)
ANALYSIS_FIELDS = (
    "preparedMeta", "preRacePrediction", "predictionAudit", "aiEvaluation",
    "analysisMode", "pace", "pacePrediction", "volatility",
)


def read_json(path: str, fallback: Any) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return fallback


def start_min(row: dict[str, Any]) -> int:
    st = str(row.get("startTime") or row.get("scheduledStartTime") or "")
    try:
        h, m = st.split(":", 1)
        return int(h) * 60 + int(m[:2])
    except Exception:
        return 9999


def snapshot(rid: str) -> dict[str, Any] | None:
    d = (
        app._prepared_get_fresh(rid)
        or app._racedb_get_fast(rid)
        or app._fast_local_race_detail(rid)
    )
    if not isinstance(d, dict):
        return None
    try:
        compact = app._compact_display_snapshot(d)
        return compact if isinstance(compact, dict) else d
    except Exception:
        return d


def fetch_d1_detail(rid: str) -> dict[str, Any] | None:
    url = f"{D1_BASE}/api/race/{urllib.parse.quote(rid, safe='')}?t={int(time.time())}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ARVEXQ-LiveSync/1"})
        with urllib.request.urlopen(req, timeout=8) as res:
            body = json.loads(res.read().decode("utf-8"))
        detail = body.get("detail") if isinstance(body, dict) else None
        # Race binding: the detail is fetched BY rid, but the caller
        # stores it under rid and merges it as that race's base. Accept
        # it only when the payload's own id is the requested race —
        # anything else falls into the audited missing-base path
        # instead of blending another race's content into this one.
        return detail if isinstance(detail, dict) and str(detail.get("id") or "") == rid else None
    except Exception as exc:
        print("D1_BASE_FETCH_ERROR", rid, type(exc).__name__, exc)
        return None


def _merge_horses(base: list[Any], fresh: list[Any]) -> list[dict[str, Any]]:
    base_rows = [copy.deepcopy(h) for h in base if isinstance(h, dict)]
    by_no = {
        int(h.get("horseNumber") or 0): h
        for h in base_rows
        if int(h.get("horseNumber") or 0) > 0
    }
    for raw in fresh:
        if not isinstance(raw, dict):
            continue
        no = int(raw.get("horseNumber") or 0)
        if no <= 0:
            continue
        row = by_no.get(no)
        if row is None:
            row = {"horseNumber": no}
            for key in ("frameNumber", "name"):
                if raw.get(key) not in (None, ""):
                    row[key] = copy.deepcopy(raw[key])
            base_rows.append(row)
            by_no[no] = row
        for key in LIVE_HORSE_FIELDS:
            if key in raw and raw.get(key) not in (None, ""):
                if key == "scratched" and row.get("scratched") is True and raw[key] is False:
                    continue  # Older provider updates must not revive a withdrawn horse.
                if key == "status" and (row.get("scratched") is True) and (
                    str(row.get("status") or "") in {"出走取消", "競走除外", "取消", "除外", "欠場"}
                ) and str(raw[key]) not in {"出走取消", "競走除外", "取消", "除外", "欠場"}:
                    continue
                row[key] = copy.deepcopy(raw[key])
    return base_rows


def apply_official_scratch_changes(
    detail: dict[str, Any] | None, changes: dict[int, str]
) -> tuple[dict[str, Any] | None, list[int]]:
    """Overlay explicit official withdrawals without discarding history or analysis.

    Non-scratch status information from slower odds providers is never allowed
    to re-enable an officially withdrawn runner.
    """
    if not isinstance(detail, dict) or not changes:
        return detail, []
    out = copy.deepcopy(detail)
    applied: list[int] = []
    for horse in out.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        no = int(horse.get("horseNumber") or 0)
        status = changes.get(no)
        if not status:
            continue
        if (horse.get("status") != status or horse.get("scratched") is not True
                or horse.get("winOdds") is not None or horse.get("popularity") is not None):
            applied.append(no)
        horse["status"] = status
        horse["scratched"] = True
        horse["withdrawn"] = True
        horse["winOdds"] = None
        horse["popularity"] = None
        horse["oddsForecast"] = False
        horse["scratchSource"] = "NAR公式変更情報"
    if applied:
        out["scratchUpdatedAtEpoch"] = int(time.time())
    return out, applied


def _merge_result(old: Any, new: Any) -> dict[str, Any]:
    old_r = copy.deepcopy(old) if isinstance(old, dict) else {}
    new_r = new if isinstance(new, dict) else {}
    if not new_r:
        return old_r
    old_final = str(old_r.get("status") or "") == "確定" and bool(old_r.get("finishers"))
    new_final = str(new_r.get("status") or "") == "確定" and bool(new_r.get("finishers"))
    if old_final and not new_final:
        return old_r
    out = old_r
    for key, value in new_r.items():
        if value not in (None, "", [], {}):
            out[key] = copy.deepcopy(value)
    return out


def merge_live(
    base: dict[str, Any] | None,
    fresh: dict[str, Any] | None,
    market: dict[str, Any] | None,
    prefer_fresh_analysis: bool = False,
) -> dict[str, Any] | None:
    if not isinstance(base, dict):
        base = {}
    if not isinstance(fresh, dict):
        fresh = {}
    if not isinstance(market, dict):
        market = {}
    if not base and not fresh:
        return None

    out = copy.deepcopy(base or fresh)
    for key in (
        "weather", "condition", "surface", "distance", "title",
        "startTime", "scheduledStartTime", "fieldSize",
        "oddsSource", "oddsType", "oddsUpdatedAt",
    ):
        value = fresh.get(key)
        if value not in (None, "", 0, "不明"):
            out[key] = copy.deepcopy(value)

    fresh_horses = [h for h in (fresh.get("horses") or []) if isinstance(h, dict)]
    market_horses = [h for h in (market.get("horses") or []) if isinstance(h, dict)]
    if out.get("horses") or fresh_horses or market_horses:
        horses = _merge_horses(out.get("horses") or [], fresh_horses)
        horses = _merge_horses(horses, market_horses)
        out["horses"] = horses

    official = official_event(fresh.get("officialCourseCondition"))
    if official and official["raceDate"] == str(out.get("date") or "") and official["track"] == str(out.get("track") or ""):
        out["officialCourseCondition"] = official
        out["condition"] = official["going"]

    if fresh.get("result"):
        out["result"] = _merge_result(out.get("result"), fresh.get("result"))

    if base:
        source = fresh if prefer_fresh_analysis else base
        for key in ANALYSIS_FIELDS:
            if key in source:
                out[key] = copy.deepcopy(source[key])
            elif key in base:
                out[key] = copy.deepcopy(base[key])

    pm = dict(out.get("preparedMeta") or {})
    pm["liveUpdatedAtEpoch"] = int(time.time())
    out["preparedMeta"] = pm
    return out


def detail_safe_for_replace(detail: dict[str, Any] | None) -> bool:
    if not isinstance(detail, dict) or not detail.get("id"):
        return False
    horses = [
        h for h in (detail.get("horses") or [])
        if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0
    ]
    if not horses:
        return False
    active = [
        h for h in horses
        if not h.get("scratched")
        and str(h.get("status") or "") not in {"取消", "除外", "競走除外", "競走取消"}
    ] or horses
    if any(not str(h.get("name") or "").strip() for h in active):
        return False
    pm = detail.get("preparedMeta") if isinstance(detail.get("preparedMeta"), dict) else {}
    return bool(pm.get("diagnosisReady") or detail.get("preRacePrediction") or detail.get("predictionAudit"))


def horse_live_rows(detail: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rid = str(detail.get("id") or "")
    for h in detail.get("horses") or []:
        if not isinstance(h, dict):
            continue
        no = int(h.get("horseNumber") or 0)
        if not rid or no <= 0:
            continue
        out.append({
            "race_id": rid,
            "horse_no": no,
            "win_odds": h.get("winOdds"),
            "popularity": h.get("popularity"),
            "body_weight": h.get("bodyWeight"),
            "body_weight_change": h.get("bodyWeightChange"),
            "horse_status": h.get("status") or ("取消" if h.get("scratched") else ""),
            "updated_at": int(time.time()),
        })
    return out


def merge_summary(row: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, Any]:
    z = dict(row)
    if not detail:
        return z
    for key in ("weather", "condition", "surface", "distance", "title"):
        value = detail.get(key)
        if value not in (None, "", 0, "不明"):
            z[key] = value
    result = detail.get("result") or {}
    if str(result.get("status") or ""):
        z["raceStatus"] = result.get("status")
    return z


# Coverage-earliness window: official NAR place odds only stand
# ~60-100 min before post, while the publish lane's place-EV upgrade
# guard closes at post-60min, and the scheduled sync cadence can drop
# slots for hours at a time (2026-11-04: scheduled runs starved all
# morning; mid-card races reached full coverage only as their guard
# closed and several missed). Target every race posting within the
# next four hours so that any single landed run inside the stand-up
# window covers the race with time to spare; nearest posts are
# served first and the set is capped so one run stays well inside
# its job timeout.
SWEEP_AHEAD_MIN = 240
MAX_LIVE_TARGETS = 30

# Blend-repair window: a race first-published on the v9b lane WITHOUT
# its market blend (win odds incomplete at first publication) can only
# be upgraded by the publish lane once this sync has landed complete
# win odds into its stored detail, and the publish guard for that
# upgrade closes at post-60min. Window-based targeting alone leaves
# such a race unrepaired for hours when the one odds pass that covered
# its card missed it (2026-11-09: Morioka 4R/6R/7R/8R missed the
# ~02:12 netkeiba preview pass that covered the other 44 races, and
# no lane ever retried them — they were still blendApplied=false at
# the 08:12 morning verify, hours before post, with full forecast
# odds already standing upstream). Any stored v9b forecast still
# carrying blendApplied=false is therefore an explicit sync target
# on every run while its post is more than 60 minutes away, whatever
# the sweep window says. The D1 detail probes this costs are capped
# per run, nearest post first (nearest guard deadline first).
BLEND_REPAIR_MIN_LEAD_MIN = 60
MAX_BLEND_REPAIR_PROBES = 16


def blend_repair_targets(
    rows: list[dict[str, Any]],
    details_by_id: dict[str, dict[str, Any]],
    now_min: int,
) -> list[str]:
    """Ids of races whose stored v9b forecast still lacks its blend.

    A race qualifies only when its stored detail's rewritePublish
    marker is readable, sits on the v9b lane (abilityLane
    v9b-cal-market) with blendApplied exactly False, carries no
    blend-upgrade revision yet, and its post is still more than
    BLEND_REPAIR_MIN_LEAD_MIN away. Anything unreadable does not
    qualify (fail-closed: ordinary targeting still applies).
    """
    found: list[tuple[int, str]] = []
    for r in rows:
        rid = str(r.get("id") or "")
        if not rid:
            continue
        sm = start_min(r)
        if sm >= 9999 or sm - now_min <= BLEND_REPAIR_MIN_LEAD_MIN:
            continue
        detail = details_by_id.get(rid)
        if not isinstance(detail, dict):
            continue
        marker = (detail.get("preparedMeta") or {}).get("rewritePublish")
        if not isinstance(marker, dict):
            continue
        if marker.get("abilityLane") != "v9b-cal-market":
            continue
        if marker.get("blendApplied") is not False:
            continue
        revision = marker.get("revision")
        if isinstance(revision, dict) and (
            revision.get("kind") == "blend-upgrade"
            or revision.get("reason") == "blend-upgrade"
        ):
            continue
        found.append((sm, rid))
    found.sort()
    return [rid for _sm, rid in found]


# Env-repair targeting (2026-11-09, user instruction 「印かえていいよ」):
# the publish lane re-issues a 2026-11-09 NAR v9b forecast whose
# probabilities were computed while the surface builders served ""
# (fixed in main 2e01ec9e) — but only from a stored detail that
# already carries the real surface, and most stored details still
# carry the "" baked in before the fix, because only each venue's
# standing targets get their facts rebuilt. A stored race whose
# forecast qualifies for the env-repair re-issue and whose stored
# detail still lacks its surface is therefore an explicit sync
# target on every run while its post is far enough away for the
# rebuilt detail to reach the publish lane inside its own
# 30-minute guard (see _env_repair_upgrade_info in
# arvexq_rewrite_publish.py, whose qualification this mirrors).
# The date scope makes the targeting inert after 2026-11-09.
ENV_REPAIR_DATE = "2026-11-09"
ENV_REPAIR_FIX_LIVE_AT = datetime(2026, 11, 9, 10, 22, tzinfo=JST)
ENV_REPAIR_MIN_LEAD_MIN = 35
MAX_ENV_REPAIR_PROBES = 16


def _stamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed


def env_repair_targets(
    rows: list[dict[str, Any]],
    details_by_id: dict[str, dict[str, Any]],
    now_min: int,
) -> list[str]:
    """Ids of races whose stored detail must be rebuilt so the
    publish lane's env-repair re-issue can fire.

    A race qualifies only when it is a 2026-11-09 NAR race whose
    stored detail's rewritePublish marker sits on the v9b lane
    (abilityLane v9b-cal-market), carries no env-repair-upgrade
    revision yet, its probabilities were last computed before
    ENV_REPAIR_FIX_LIVE_AT (the latest forecast-recomputing
    revision — roster change / lane upgrade / blend upgrade —
    sets the time; surgical revisions keep the stored
    probabilities, so with one of those on top the time is the
    first publication), its post is still more than
    ENV_REPAIR_MIN_LEAD_MIN away, and its stored detail still
    serves an empty surface — the one thing this sync's rebuild
    supplies. Anything unreadable does not qualify (fail-closed:
    ordinary targeting still applies).
    """
    found: list[tuple[int, str]] = []
    for r in rows:
        rid = str(r.get("id") or "")
        if not rid.startswith("nar-"):
            continue
        if str(r.get("date") or "") not in ("", ENV_REPAIR_DATE):
            continue
        sm = start_min(r)
        if sm >= 9999 or sm - now_min <= ENV_REPAIR_MIN_LEAD_MIN:
            continue
        detail = details_by_id.get(rid)
        if not isinstance(detail, dict):
            continue
        if str(detail.get("date") or "") != ENV_REPAIR_DATE:
            continue
        surface = detail.get("surface")
        if isinstance(surface, str) and surface.strip():
            continue
        marker = (detail.get("preparedMeta") or {}).get("rewritePublish")
        if not isinstance(marker, dict):
            continue
        if marker.get("abilityLane") != "v9b-cal-market":
            continue
        revision = marker.get("revision")
        kind = None
        revised_at = None
        if isinstance(revision, dict):
            kind = revision.get("kind") or revision.get("reason")
            revised_at = revision.get("revisedAt")
        if kind == "env-repair-upgrade":
            continue
        if kind in ("blend-upgrade", "lane-upgrade",
                    "lane-upgrade-v9b-adoption", "roster-change"):
            computed_at = _stamp(revised_at)
        else:
            computed_at = _stamp(
                marker.get("firstPublishedAt")
                or marker.get("publishedAt"))
        if computed_at is None or computed_at >= ENV_REPAIR_FIX_LIVE_AT:
            continue
        found.append((sm, rid))
    found.sort()
    return [rid for _sm, rid in found]


def choose_targets(rows: list[dict[str, Any]], now_min: int) -> list[str]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault((str(r.get("circuit") or ""), str(r.get("track") or "")), []).append(r)

    ids: list[str] = []
    for group in groups.values():
        group.sort(key=start_min)
        live = [r for r in group if start_min(r) <= now_min < start_min(r) + 35]
        future = [r for r in group if start_min(r) >= now_min]
        for r in live[:1] + future[:1]:
            rid = str(r.get("id") or "")
            if rid and rid not in ids:
                ids.append(rid)

    upcoming = sorted(
        (r for r in rows if -15 <= start_min(r) - now_min <= SWEEP_AHEAD_MIN),
        key=start_min,
    )
    for r in upcoming:
        if len(ids) >= MAX_LIVE_TARGETS:
            break
        rid = str(r.get("id") or "")
        if rid and rid not in ids:
            ids.append(rid)
    return ids


def seed_prepared_base(rid: str, detail: dict[str, Any] | None) -> None:
    if not isinstance(detail, dict) or not detail.get("id"):
        return
    try:
        app._store_fast_snapshot(copy.deepcopy(detail))
    except Exception as exc:
        print("LIVE_BASE_SEED_ERROR", rid, type(exc).__name__, exc)


def refresh_environment(rows: list[dict[str, Any]], target_ids: set[str]) -> dict[str, dict[str, Any]]:
    groups: dict[tuple[str, str, str], None] = {}
    for row in rows:
        rid = str(row.get("id") or "")
        if rid not in target_ids:
            continue
        date = str(row.get("date") or "")
        circuit = str(row.get("circuit") or "")
        track = str(row.get("track") or "")
        if date and circuit and track:
            groups[(date, circuit, track)] = None

    states: dict[str, dict[str, Any]] = {}
    for date, circuit, track in groups:
        key = f"{date}|{circuit}|{track}"
        try:
            state = app._refresh_track_environment(date, circuit, track, True)
            states[key] = state if isinstance(state, dict) else {}
        except Exception as exc:
            states[key] = {"error": f"{type(exc).__name__}: {exc}", "changed": 0}
            print("LIVE_ENV_ERROR", key, states[key]["error"])
    return states


def apply_official_mark_revision(
    base: dict[str, Any] | None, incoming: dict[str, Any] | None,
    now: datetime,
) -> tuple[dict[str, Any] | None, str]:
    """Append revisions only for a verified, meaningful pre-off official change.

    Keep original marks, betting tickets, and the server seal untouched.
    A feed that merely reports a new weather/odds value cannot change marks.
    """
    if not isinstance(base, dict) or not isinstance(incoming, dict):
        return incoming, ""
    original = base.get("morningMarkSnapshot")
    if not isinstance(original, dict) or original.get("version") != "arvexq-morning-marks-v1":
        return incoming, ""
    if str(original.get("raceId") or "") != str(incoming.get("id") or ""):
        return incoming, ""
    previous = base.get("officialCourseCondition")
    current = incoming.get("officialCourseCondition")
    reason = pre_off_change(incoming, previous, current, now)
    if not reason:
        return incoming, ""
    official = official_event(current)
    if not official:
        return incoming, ""
    revisions = list(base.get("officialMarkRevisions") or [])
    if any((r.get("officialCourseCondition") or {}).get("publishedAt") == official["publishedAt"]
           for r in revisions if isinstance(r, dict)):
        return incoming, ""
    try:
        working = copy.deepcopy(incoming)
        working["morningMarkSnapshot"] = copy.deepcopy(original)
        working["officialCourseCondition"] = official
        # Do not use any result/finisher data or post-off recomputation.
        process = subprocess.run(
            ["node", "scripts/arvexq_capture_course_revised_marks.js"],
            input=json.dumps(working, ensure_ascii=False), text=True,
            capture_output=True, timeout=25,
            env={**os.environ, "TZ": "Asia/Tokyo"},
        )
        if process.returncode:
            return incoming, "official-change mark compute failed: " + process.stderr[-400:]
        predicted = json.loads(process.stdout)
        horses = predicted.get("horses")
        if not isinstance(horses, list) or len(horses) < 3:
            return incoming, "official-change forecast incomplete"
        previous_marks = revisions[-1].get("horses") if revisions else original.get("horses")
        if not isinstance(previous_marks, list):
            return incoming, "previous snapshot unavailable"
        old = {int(h["horseNumber"]): str(h.get("mark") or "") for h in previous_marks}
        new = {int(h["horseNumber"]): str(h.get("mark") or "") for h in horses}
        affected = sorted(no for no in new if new[no] != old.get(no, ""))
        if not affected:
            # Evidence changed, but no meaningful mark changes. Persist source
            # metadata only; never advertise a phantom revised prediction.
            incoming["officialCourseCondition"] = official
            return incoming, ""
        revision = {"version": "arvexq-official-mark-revision-v1",
                    "raceId": str(incoming["id"]), "raceDate": str(incoming["date"]),
                    "revisedAt": now.isoformat(timespec="seconds"),
                    "reason": reason, "officialCourseCondition": official,
                    "affectedHorseNumbers": affected, "horses": horses}
        revisions.append(revision)
        incoming["morningMarkSnapshot"] = copy.deepcopy(original)
        incoming["officialMarkRevisions"] = revisions
        incoming["officialCourseCondition"] = official
        return incoming, reason
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        return incoming, "official-change mark error: " + type(exc).__name__ + ": " + str(exc)


def pre_post_time_guard(row: dict[str, Any], now_min: int) -> bool:
    return start_min(row) < 9999 and now_min < start_min(row)


def refresh_one(
    rid: str,
    now_min: int,
    row_by_id: dict[str, dict[str, Any]],
    base: dict[str, Any] | None,
    official_condition: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any] | None, str, bool, bool]:
    errors: list[str] = []
    row = row_by_id.get(rid) or {}
    sm = start_min(row)
    pre_market = snapshot(rid) or base
    pre_market_hash = analysis_input_hash(pre_market) if isinstance(pre_market, dict) else ""

    market: dict[str, Any] | None = None
    try:
        body = app.odds_refresh(rid, 1)
        market = body if isinstance(body, dict) else None
    except Exception as exc:
        errors.append("market:" + str(exc))

    fresh = snapshot(rid) or pre_market
    candidate = merge_live(base, fresh, market, False)
    if candidate and official_condition and pre_post_time_guard(row, now_min):
        candidate["officialCourseCondition"] = copy.deepcopy(official_condition)
        candidate["condition"] = official_condition["going"]
    candidate_hash = analysis_input_hash(candidate) if isinstance(candidate, dict) else ""
    pre_post = sm < 9999 and now_min < sm
    official_updated = bool(pre_post and official_condition and
        official_condition != ((base or {}).get("officialCourseCondition") or {}))
    market_analysis_changed = bool(pre_post and ((pre_market_hash and candidate_hash and
        pre_market_hash != candidate_hash) or official_updated))

    # Environment updater already rebuilds diagnoses for changed weather/going.
    base_hash = analysis_input_hash(base) if isinstance(base, dict) else ""
    env_analysis_changed = bool(pre_post and base_hash and pre_market_hash and base_hash != pre_market_hash)

    if market_analysis_changed:
        try:
            app._build_fast_diagnosis_snapshot(rid, allow_network=False, deep_context=False)
            fresh = snapshot(rid) or fresh
        except Exception as exc:
            errors.append("analysis:" + str(exc))

    # All official result/payout source polling belongs to
    # scripts/arvexq_result_repair.py. Realtime Sync only merges market,
    # official scratches and pre-post environment/diagnosis deltas. Existing
    # result fields in its D1 base are preserved by merge_live(), not refetched.
    analysis_changed = bool(env_analysis_changed or market_analysis_changed)
    merged = merge_live(base, fresh or snapshot(rid), market, analysis_changed)
    if merged and pre_post and official_condition:
        merged["officialCourseCondition"] = copy.deepcopy(official_condition)
        merged["condition"] = official_condition["going"]
    if merged and pre_post:
        merged, official_status = apply_official_mark_revision(base, merged, datetime.now(JST))
        if official_status:
            print("OFFICIAL_COURSE_MARK_EVENT", rid, official_status)
            if "failed" in official_status or "error" in official_status:
                errors.append(official_status)
            else:
                analysis_changed = True
    if merged and pre_post and user_revision_enabled(datetime.now(JST)):
        before_original = copy.deepcopy((merged.get("morningMarkSnapshot") or {}))
        merged, model_status = user_update_marks(merged, now=datetime.now(JST))
        if model_status.startswith("changed:"):
            print("USER_APPROVED_MODEL_MARK_REVISION", rid, model_status)
            if merged.get("morningMarkSnapshot") != before_original:
                raise RuntimeError("user-approved revision mutated the morning original")
            analysis_changed = True
        elif model_status.startswith("compute-failed") or model_status == "invalid-preoff-revision":
            errors.append("user-model-revision:" + model_status)
            print("USER_APPROVED_MODEL_MARK_ERROR", rid, model_status)
    if merged and analysis_changed and pre_post:
        pm = dict(merged.get("preparedMeta") or {})
        pm["analysisInputHash"] = analysis_input_hash(merged)
        pm["analysisInputChangedAtEpoch"] = int(time.time())
        merged["preparedMeta"] = pm
    return rid, merged, "; ".join(errors), bool(base), analysis_changed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="bundle.json")
    p.add_argument("--out", default="live-payload.json")
    p.add_argument("--audit", default="live-audit.json")
    p.add_argument("--workers", type=int, default=10)
    args = p.parse_args()

    bundle = read_json(args.bundle, {})
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id") and str(r.get("track") or "") not in ("帯広", "帯広ば") and not any(f"-{name}-" in str(r.get("id")) for name in ("帯広", "帯広ば"))]
    if not rows:
        raise SystemExit("live sync: no races in bundle")
    bundled_by_id = {
        str(d.get("id") or ""): d
        for d in (bundle.get("details") or [])
        if isinstance(d, dict) and d.get("id")
    }

    now = datetime.now(JST)
    now_min = now.hour * 60 + now.minute
    row_by_id = {str(r["id"]): r for r in rows}
    targets = choose_targets(rows, now_min)
    # One explicit user approval applies only to still-unstarted races today.
    # New days use the updated morning model instead of rewriting old archives.
    if user_revision_enabled(now):
        pending_model_targets = [str(r["id"]) for r in rows
                                 if str(r.get("date") or "") == now.date().isoformat()
                                 and post_at(r) and now < post_at(r)]
        for rid in pending_model_targets:
            if rid not in targets:
                targets.append(rid)
        print("USER_APPROVED_MODEL_TARGETS", "eligible", len(pending_model_targets))
    # RaceList 変更情報 is venue-wide. Capture cancellations even when their
    # races are more than an hour away or have left the rolling live window.
    tracks = {str(r.get("track")): str(app.NAR_BABA_CODES.get(str(r.get("track")) or "") or "")
              for r in rows if r.get("circuit") == "地方" and r.get("track")}
    official_changes = collect_nar_changes(now.strftime("%Y-%m-%d"), tracks)
    valid_ids = set(row_by_id)
    try:
        official_conditions = fetch_course_events(now.date().isoformat(), rows, now=now)
    except Exception as exc:
        official_conditions = {}
        print("OFFICIAL_COURSE_FEED_UNAVAILABLE", type(exc).__name__, str(exc))
    for rid in official_conditions:
        if rid in valid_ids and rid not in targets:
            targets.append(rid)
    for rid in official_changes:
        if rid in valid_ids and rid not in targets:
            targets.append(rid)

    base_by_id: dict[str, dict[str, Any]] = dict(bundled_by_id)
    missing_for_d1 = [rid for rid in targets if rid not in base_by_id]
    if missing_for_d1:
        with ThreadPoolExecutor(max_workers=min(8, len(missing_for_d1))) as ex:
            futures = {ex.submit(fetch_d1_detail, rid): rid for rid in missing_for_d1}
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    detail = fut.result()
                except Exception:
                    detail = None
                if detail:
                    base_by_id[rid] = detail

    # Blend repair: probe the stored details of unstarted races that
    # ordinary targeting did not pick (nearest post first, capped)
    # and add any whose v9b forecast still lacks its market blend.
    # Their refreshed odds are what the publish lane's blend upgrade
    # consumes; without this, a race missed by an early odds pass is
    # never retried until the sweep window reaches it.
    probe_rows = sorted(
        (r for r in rows
         if str(r.get("id") or "") not in targets
         and str(r.get("id") or "") not in base_by_id
         and start_min(r) < 9999
         and start_min(r) - now_min > BLEND_REPAIR_MIN_LEAD_MIN),
        key=start_min,
    )[:MAX_BLEND_REPAIR_PROBES]
    if probe_rows:
        with ThreadPoolExecutor(max_workers=min(8, len(probe_rows))) as ex:
            futures = {
                ex.submit(fetch_d1_detail, str(r.get("id") or "")): str(r.get("id") or "")
                for r in probe_rows
            }
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    detail = fut.result()
                except Exception:
                    detail = None
                if detail:
                    base_by_id[rid] = detail
    repair = blend_repair_targets(rows, base_by_id, now_min)
    for rid in repair:
        if rid not in targets:
            targets.append(rid)
    if repair:
        print("BLEND_REPAIR_TARGETS", len(repair), ",".join(repair))

    # Env repair (2026-11-09 only): the same probe pattern for
    # races whose stored forecast qualifies for the publish lane's
    # env-repair re-issue but whose stored detail still serves an
    # empty surface. Their refreshed detail is what the publish
    # lane consumes; without this, a race ordinary targeting has
    # not reached keeps the "" baked into its stored detail until
    # it becomes its venue's next race — inside the publish
    # guard, too late to repair.
    env_probe_rows = sorted(
        (r for r in rows
         if str(r.get("id") or "") not in targets
         and str(r.get("id") or "") not in base_by_id
         and start_min(r) < 9999
         and start_min(r) - now_min > ENV_REPAIR_MIN_LEAD_MIN),
        key=start_min,
    )[:MAX_ENV_REPAIR_PROBES]
    if env_probe_rows:
        with ThreadPoolExecutor(max_workers=min(8, len(env_probe_rows))) as ex:
            futures = {
                ex.submit(fetch_d1_detail, str(r.get("id") or "")): str(r.get("id") or "")
                for r in env_probe_rows
            }
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    detail = fut.result()
                except Exception:
                    detail = None
                if detail:
                    base_by_id[rid] = detail
    env_repair = env_repair_targets(rows, base_by_id, now_min)
    for rid in env_repair:
        if rid not in targets:
            targets.append(rid)
    if env_repair:
        print("ENV_REPAIR_TARGETS", len(env_repair), ",".join(env_repair))

    # Seed the rich D1 payload into local RaceDB before any live collector runs.
    for rid in targets:
        seed_prepared_base(rid, base_by_id.get(rid))

    environment = refresh_environment(rows, set(targets))

    details: list[dict[str, Any]] = []
    odds_current: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    refreshed: dict[str, dict[str, Any]] = {}
    skipped_thin: list[str] = []
    skipped_odds_only: list[str] = []
    missing_base: list[str] = []
    reanalyzed: list[str] = []

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 12))) as ex:
        futs = {
            ex.submit(refresh_one, rid, now_min, row_by_id, base_by_id.get(rid), official_conditions.get(rid)): rid
            for rid in targets
        }
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                rid, d, err, had_base, analysis_changed = fut.result()
            except Exception as exc:
                d, err, had_base, analysis_changed = None, str(exc), False, False
            if err:
                errors[rid] = err
            if not had_base:
                missing_base.append(rid)
            if analysis_changed:
                reanalyzed.append(rid)
            if isinstance(d, dict) and d.get("id"):
                d, updated = apply_official_scratch_changes(d, official_changes.get(rid, {}))
                if updated:
                    print("OFFICIAL_SCRATCH_APPLIED", rid, ",".join(map(str, updated)))
                    # Mark analysis stale; the frontend re-evaluates with inactive
                    # runners excluded. Do not recompute or rewrite locked bets here.
                    pm = dict(d.get("preparedMeta") or {})
                    pm["analysisInputChangedAtEpoch"] = int(time.time())
                    d["preparedMeta"] = pm
                    if rid not in reanalyzed:
                        reanalyzed.append(rid)
                refreshed[rid] = d
                odds_current.extend(horse_live_rows(d))
                if detail_safe_for_replace(d):
                    if requires_full_write(base_by_id.get(rid), d):
                        details.append(d)
                    else:
                        # odds_current holds the live ticks; repeatedly replacing
                        # a multi-MB D1 detail with the same persistent data is
                        # wasteful and can exhaust the account database.
                        skipped_odds_only.append(rid)
                        print("LIVE_DETAIL_UNCHANGED_ODDS_ONLY", rid)
                else:
                    skipped_thin.append(rid)

    summaries = [merge_summary(r, refreshed.get(str(r.get("id") or ""))) for r in rows]
    payload = {
        "summaries": summaries,
        "details": details,
        "odds_current": odds_current,
        "meta": {
            "source": "github-actions-live-delta-v4-d1-hash",
            "sync_date": bundle.get("date") or now.strftime("%Y-%m-%d"),
            "live_delta": True,
            "full_card_lane": False,
            "target_count": len(targets),
            "detail_update_count": len(details),
            "unchanged_detail_not_rewritten_count": len(skipped_odds_only),
            "thin_detail_skipped_count": len(skipped_thin),
            "missing_d1_base_count": len(missing_base),
            "reanalyzed_count": len(reanalyzed),
            "environment_track_count": len(environment),
            "official_course_event_count": len(official_conditions),
            "user_model_revision_approval": "user-approved-past-five-from-2026-10-09-20-10-jst"
                if user_revision_enabled(now) else "",
            "odds_row_count": len(odds_current),
            "error_count": len(errors),
            "live_updated_at": int(time.time()),
        },
    }
    audit = {
        "date": payload["meta"]["sync_date"],
        "targets": targets,
        "updated": sorted(refreshed),
        "reanalyzed": sorted(reanalyzed),
        "environment": environment,
        "thin_detail_skipped": sorted(skipped_thin),
        "unchanged_detail_not_rewritten": sorted(skipped_odds_only),
        "missing_d1_base": sorted(missing_base),
        "errors": errors,
        "official_cancellations": {rid: {str(no): status for no, status in horses.items()}
                                   for rid, horses in official_changes.items() if rid in valid_ids},
        "targetCount": len(targets),
        "updatedCount": len(refreshed),
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "LIVE SYNC",
        "targets=", len(targets),
        "details=", len(details),
        "reanalyzed=", len(reanalyzed),
        "thinSkipped=", len(skipped_thin),
        "missingD1Base=", len(missing_base),
        "oddsRows=", len(odds_current),
        "errors=", len(errors),
    )
    for rid, err in errors.items():
        print("LIVE_SYNC_ERROR", rid, err)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
