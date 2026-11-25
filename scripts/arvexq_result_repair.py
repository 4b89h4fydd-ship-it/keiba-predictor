#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARVEXQ result repair lane.

Repairs every started race whose result or payout is incomplete. Rich D1 race
payloads are seeded locally and preserved; only authoritative result/live fields
are upgraded. Pending races are oldest-first with no arbitrary race-count cap.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from arvexq.results import (
    JST,
    TERMINAL_NO_PAYOUT,
    merge_detail,
    merge_result,
    payout_combination_violations,
    result_state,
    row_date,
    start_minutes,
    started,
)

# Transitional compatibility for history/validation callers while result-domain
# helpers now live in arvexq.results. New code should import the domain module.
_merge_detail = merge_detail
_merge_result = merge_result
_result_state = result_state
_row_date = row_date
_start_minutes = start_minutes
_started = started


def _read_json(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: str, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


_MARK_ORDER = ("◎", "○", "▲", "△", "☆")

# Forecast-publication statuses whose stored marks the heal may
# align: the publish lane's own "ready" and the delivery
# projection's "unified-reference-ready" — the same source
# vocabulary FORECAST_CARRYOVER_SOURCE_STATUSES accepts in
# scripts/arvexq_static_api_build.py.  A detail that passed through
# the projection (arvexq/forecast/publication.py) keeps its sealed
# blocks under the renamed status; keying the heal on "ready" only
# left exactly those details unhealed (collection-circuit audit
# S7, 2026-11-25).
_HEAL_SOURCE_STATUSES = ("ready", "unified-reference-ready")


def _marks_map(entries: Any, *keys: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(entries, list):
        return out
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        label = next((entry.get(k) for k in keys if entry.get(k)), None)
        if label:
            out[str(label)] = entry.get("horseNumber")
    return out


def _heal_marks_consistency(detail: dict[str, Any] | None) -> bool:
    """Align predictionMarks to the authoritative unifiedForecast marks.

    The unified product is the receipt-verified publication (the
    publish marker chain and the read-back verification both key on
    it); the entry list renders predictionMarks. The blend-upgrade
    reissues of 2026-11-07/08 left stored details whose
    predictionMarks still named the first publication's horses
    beside the reissue's unifiedForecast — two different ◎ for one
    race. Only the marks assignment is aligned (the marks list, the
    prediction block's copy of it, its ordered candidate list, and
    the horses' predMark): probabilities, tickets, the unified
    product itself and the sealed pre-off archive are untouched.
    Returns True when the detail was changed.
    """
    if not isinstance(detail, dict):
        return False
    if detail.get("predictionStatus") not in _HEAL_SOURCE_STATUSES:
        return False
    uf_entries = (detail.get("unifiedForecast") or {}).get("marks")
    uf_map = _marks_map(uf_entries, "markSymbol", "mark")
    if len(uf_map) != 5:
        return False
    pm_map = _marks_map(detail.get("predictionMarks"), "mark")
    if pm_map == uf_map:
        return False
    uf_by_label: dict[str, dict[str, Any]] = {}
    for entry in uf_entries or []:
        if not isinstance(entry, dict):
            continue
        label = entry.get("markSymbol") or entry.get("mark")
        if label:
            uf_by_label[str(label)] = entry
    new_pm: list[dict[str, Any]] = []
    for label in _MARK_ORDER:
        src = uf_by_label[label]
        entry: dict[str, Any] = {
            "horseNumber": src.get("horseNumber"),
            "mark": label,
            "winProbability": src.get("winProbability"),
        }
        if src.get("attention"):
            entry["attention"] = True
        new_pm.append(entry)
    # Attention-only overlay entries (empty mark) keep their carrier.
    marked_numbers = set(uf_map.values())
    for entry in detail.get("predictionMarks") or []:
        if (isinstance(entry, dict) and not entry.get("mark")
                and entry.get("attention")
                and entry.get("horseNumber") not in marked_numbers):
            new_pm.append(copy.deepcopy(entry))
    detail["predictionMarks"] = new_pm
    prediction = detail.get("prediction")
    if isinstance(prediction, dict):
        prediction["predictionMarks"] = copy.deepcopy(new_pm)
        value = ((prediction.get("stages") or {}).get("marks") or {}).get("value")
        if isinstance(value, dict) and "orderedWinCandidates" in value:
            value["orderedWinCandidates"] = [uf_map[label] for label in _MARK_ORDER]
    number_to_mark = {number: label for label, number in uf_map.items()}
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        if horse.get("horseNumber") in number_to_mark:
            horse["predMark"] = number_to_mark[horse["horseNumber"]]
        else:
            horse.pop("predMark", None)
    return True


def _seed_base(rid: str, detail: dict[str, Any] | None) -> None:
    if not isinstance(detail, dict) or not detail.get("id"):
        return
    try:
        app._store_fast_snapshot(copy.deepcopy(detail))
    except Exception as exc:
        print("RESULT_BASE_SEED_ERROR", rid, type(exc).__name__, exc)


_ENV_UNKNOWN = (None, "", "不明")


def _nar_environment_probe(probe: dict[str, Any]) -> dict[str, Any]:
    """Adapt app._nar_fetch_environment to the probe-dict shape the
    JRA fetcher takes, so one backfill pass can serve both circuits."""
    return app._nar_fetch_environment(
        str(probe.get("track") or ""), str(probe.get("date") or ""),
        int(probe.get("raceNumber") or 0)) or {}


def _fill_missing_environment(
    by_id: dict[str, Any],
    summary_by_id: dict[str, Any],
    race_ids: list[str],
    fetch_env: Any,
    limit: int = 12,
    fetch_env_nar: Any = None,
) -> list[str]:
    """Backfill weather/going on races whose stored detail still
    carries the list builder's placeholder.

    Summary rows are born with weather/condition "不明" (the list
    builders hardcode them), and the values only ever landed when a
    best-effort live refresh or an official-result merge happened to
    run for that race: on 2026-11-07/08, 44 of 72 JRA races (all of
    Kyoto/Tokyo) kept the placeholder permanently, while Fukushima —
    refreshed successfully — had none. This pass is the steady call.
    It is deliberately independent of the result-repair scope: it
    covers every race in the day bundle — not yet started races too
    (JRA publishes the going in the morning and NAR publishes through
    keiba.go.jp before the off) and NAR races as well as JRA, which
    previously had no backfill at all. Only values the fetcher
    actually observed are written; existing values are never
    overwritten. Attempts are capped per run (the lane runs every
    few minutes, so a day's backlog drains over consecutive runs
    instead of bursting the source sites).
    """
    filled: list[str] = []
    attempts = 0
    for rid in race_ids:
        if attempts >= max(0, int(limit)):
            break
        if str(rid).startswith("nar-"):
            fetcher = fetch_env_nar
        elif str(rid).startswith("jra-"):
            fetcher = fetch_env
        else:
            continue
        if fetcher is None:
            continue
        detail = by_id.get(rid)
        if not isinstance(detail, dict):
            continue
        missing = [k for k in ("weather", "condition")
                   if detail.get(k) in _ENV_UNKNOWN]
        if not missing:
            continue
        attempts += 1
        row = summary_by_id.get(rid) or {}
        probe = {
            "date": detail.get("date") or row.get("date") or "",
            "track": detail.get("track") or row.get("track") or "",
            "raceNumber": detail.get("raceNumber")
            or row.get("raceNumber") or row.get("raceNo") or 0,
            "surface": detail.get("surface") or row.get("surface") or "",
            "jraCname": detail.get("jraCname") or "",
        }
        try:
            env = fetcher(probe) or {}
        except Exception as exc:
            print("RESULT_ENV_FILL_ERROR", rid, type(exc).__name__, exc)
            continue
        changed = False
        for key in missing:
            value = env.get(key)
            if value not in _ENV_UNKNOWN:
                detail[key] = value
                if isinstance(summary_by_id.get(rid), dict):
                    summary_by_id[rid][key] = value
                changed = True
        if changed:
            detail["environmentMeta"] = {
                "source": env.get("source") or (
                    "NAR公式" if str(rid).startswith("nar-")
                    else "JRA公式優先"),
                "updatedAtEpoch": int(time.time()),
                "filledBy": "result-repair-env-backfill",
            }
            filled.append(rid)
            print("RESULT_ENV_FILLED", rid,
                  detail.get("weather"), detail.get("condition"))
    return filled


def _official_refresh_from_bundle(rid: str, base: dict[str, Any] | None) -> dict[str, Any] | None:
    """Rebuild a fresh detail for a race the fast refresher cannot reach.

    The fast refresher reads locally stored full details; a historical
    race whose stored detail was compacted to a summary has none, so the
    refresher returns nothing and the race stays unrepairable forever
    (the 2026-11-09 payout-duplicate census: 345 races sat in exactly
    this state). The official result fetchers only need the race
    identity — date / track / race number, the stored JRA result token,
    and, for NAR, a name->number map that the stored finishers already
    provide — all of which the bundle detail still carries. The result
    is merged into a copy of the bundle detail exactly as the fast path
    merges it into the locally stored one; forecasts are untouched
    (the protect seam restores them from the stored publication).
    """
    if not isinstance(base, dict) or not base.get("id"):
        return None
    fresh = copy.deepcopy(base)
    if rid.startswith("nar-"):
        minimal = {
            "id": rid,
            "date": base.get("date"),
            "track": base.get("track"),
            "raceNumber": base.get("raceNumber"),
            "horses": [
                {"name": f.get("name"), "horseNumber": f.get("horseNumber")}
                for f in (base.get("result") or {}).get("finishers") or []
                if isinstance(f, dict) and f.get("name") and f.get("horseNumber")
            ],
        }
        official = None
        try:
            official = app._nar_official_result_fast(minimal)
        except Exception as exc:
            print("NAR official result after bundle refresh failed", rid, exc)
        if official:
            # Dual-source rule in the repair lane too: netkeiba fills
            # the fields the official block leaves empty.
            official = app._dual_source_result(fresh, official)
            fresh["result"] = official
            if official.get("weather") not in (None, "", "不明"):
                fresh["weather"] = official["weather"]
            if official.get("condition") not in (None, "", "不明"):
                fresh["condition"] = official["condition"]
            fresh = app._merge_result_fields(fresh, official)
        elif app._race_should_have_result(fresh) and not app._result_block_complete(fresh):
            # Mirror the fast path: netkeiba carries the race when
            # the official table cannot be read from the bundle.
            try:
                nk = app._netkeiba_current_result(fresh)
                if nk:
                    fresh["result"] = nk
                    fresh = app._merge_result_fields(fresh, nk)
            except Exception as exc:
                print("NAR result fallback after bundle refresh failed", rid, exc)
        if fresh.get("result") == base.get("result"):
            return None
        if app._result_has_podium(fresh):
            try:
                fresh = app._attach_nar_payouts(fresh)
            except Exception as exc:
                print("NAR payout attach after bundle refresh failed", rid, exc)
        return fresh
    # netkeiba first, mirroring app._refresh_result_fast: publish its
    # flash/confirmed block immediately; the official parse below
    # overwrites once final and never downgrades it.
    nk_attempted = False
    if app._race_should_have_result(fresh) and not app._result_block_complete(fresh):
        nk_attempted = True
        try:
            nk = app._netkeiba_current_result(fresh)
            if nk:
                fresh["result"] = nk
                fresh = app._merge_result_fields(fresh, nk)
        except Exception as exc:
            print("JRA result netkeiba-first after bundle refresh failed", rid, exc)
    # JRA: reuse the stored result token when it still names this race;
    # otherwise re-derive it from the race card, as the fast path does.
    result_cname = str(base.get("resultCname") or "")
    if result_cname and not app._jra_result_cname_matches_detail(result_cname, base):
        result_cname = ""
    if not result_cname:
        cname = app._jra_find_cname(str(base.get("date") or ""),
                                    str(base.get("track") or ""),
                                    int(base.get("raceNumber") or 0))
        if cname:
            result_cname = app._jra_result_cname_from_card(cname)
    parsed = None
    if result_cname:
        parsed = app._jra_parse_result(result_cname, fresh)
        if parsed:
            if app._official_result_would_downgrade(fresh, parsed):
                parsed = {**parsed, "result": None}
            fresh = app._merge_official_result(fresh, parsed)
            if app._race_should_have_result(fresh):
                fresh["result"] = app._dual_source_result(fresh, fresh.get("result"))
    if not parsed and app._race_should_have_result(fresh):
        # The official token route is unavailable, but a stored
        # result whose gaps are parser staleness — last-3F, corner
        # positions or race laps a pre-fix parse never recorded
        # (the 2026-11-15 Kyoto results) — can still be healed:
        # fill from a fresh netkeiba parse, never overwriting a
        # stored value. The fast lane deliberately does not do
        # this (its gate is fetch-free for complete results); the
        # repair lane is where historical staleness belongs.
        stored = fresh.get("result") or {}
        if stored.get("finishers") and any(
                g in ("last3FSeconds", "cornerPositions", "raceLapTimes")
                for g in app._result_gaps(stored)):
            try:
                nk = app._netkeiba_current_result(fresh)
                if nk:
                    merged = app._merge_result_sources(stored, nk)
                    if merged and merged is not stored:
                        fresh["result"] = merged
                        fresh = app._merge_result_fields(fresh, merged)
            except Exception as exc:
                print("JRA stored result dual-source heal (bundle) failed", rid, exc)
    stored_payouts = ((fresh.get("result") or {}).get("payouts")) or []
    payout_broken = not stored_payouts or bool(payout_combination_violations(fresh))
    if (not app._result_has_podium(fresh)
            or not app._result_covers_card(fresh)
            or payout_broken) and app._race_should_have_result(fresh) and not nk_attempted:
        try:
            nk = app._netkeiba_current_result(fresh)
            if nk:
                # A shape-broken payout block must be superseded
                # wholesale (the merge only fills empty fields and
                # would preserve the corruption); every other gap is
                # filled into the stored block, dual-source style.
                stored = fresh.get("result") or {}
                if stored.get("finishers") and not payout_broken:
                    merged = app._merge_result_sources(stored, nk)
                    fresh["result"] = merged or nk
                else:
                    fresh["result"] = nk
                fresh = app._merge_result_fields(fresh, fresh["result"])
        except Exception as exc:
            print("JRA result fallback after bundle refresh failed", rid, exc)
    if fresh.get("result") == base.get("result"):
        return None
    return fresh


def repair(bundle_path: str, payload_path: str, report_path: str, workers: int = 6,
           light: bool = False, light_window_min: int = 60) -> int:
    """Repair started races with incomplete results.

    Light mode is the fast lane for races that have just run: only
    races started within ``light_window_min`` minutes are refreshed,
    through the netkeiba-only app._refresh_result_light, in a single
    pass — no marks heal, no environment backfill, no standing
    audits. The full (heavy) mode remains responsible for official
    overwrites, payout completion and verification of every race.
    """
    bundle = _read_json(bundle_path)
    # The D1 calendar can retain retired Banei summary IDs without detail
    # records. Do not reacquire, publish, or verify those retired races. Leave
    # the archived D1 originals and any upstream bundle bytes untouched.
    def active(row: Any) -> bool:
        if not isinstance(row, dict) or not row.get("id"):
            return False
        rid = str(row["id"])
        return (str(row.get("track") or "") not in ("帯広", "帯広ば")
                and "-帯広-" not in rid and "-帯広ば-" not in rid)

    rows = [r for r in (bundle.get("races") or []) if active(r)]
    base_details = [d for d in (bundle.get("details") or []) if active(d)]
    by_id: dict[str, dict[str, Any]] = {str(d["id"]): d for d in base_details}
    summary_by_id = {str(r["id"]): r for r in rows}

    now = datetime.now(JST)
    started_ids = [str(r["id"]) for r in rows if started(r, now)]

    # Marks-consistency heal candidates, taken from the bundle
    # details BEFORE any result refresh replaces them: the refresh
    # path returns a display-compacted detail whose projection status
    # ("unified-reference-ready" / "disabled") and rebuilt blocks no
    # longer carry the stored publication's shape, so healing after
    # the refresh misses exactly the races the refresh touched. The
    # healed bundle copy is the stored publication itself (marker
    # verbatim), which the protect seam accepts as the same
    # publication re-sent; a fresher result obtained by the refresh
    # is transplanted into it at payload assembly below.
    healed_by_id: dict[str, dict[str, Any]] = {}
    if not light:
        for rid in started_ids:
            candidate = copy.deepcopy(by_id.get(rid) or {})
            if candidate.get("id") and _heal_marks_consistency(candidate):
                healed_by_id[rid] = candidate

    def just_started(rid: str) -> bool:
        row = summary_by_id.get(rid) or {}
        if row_date(row) != now.strftime("%Y-%m-%d"):
            return False
        sm = start_minutes(row)
        if sm >= 9999:
            return False
        return 0 <= (now.hour * 60 + now.minute) - sm <= max(1, int(light_window_min))

    pending = []
    for rid in started_ids:
        if light and not just_started(rid):
            continue
        result_ok, payout_ok, _ = result_state(by_id.get(rid))
        if not result_ok or not payout_ok:
            pending.append(rid)

    pending.sort(key=lambda rid: (row_date(summary_by_id[rid]), start_minutes(summary_by_id[rid]), rid))
    errors: dict[str, str] = {}
    repaired: set[str] = set()
    published: set[str] = set()  # publish observed result/payout improvements even when still incomplete

    for rid in pending:
        _seed_base(rid, by_id.get(rid))

    def refresh_one(rid: str) -> tuple[str, dict[str, Any] | None, str]:
        if light:
            # Light lane: netkeiba only, via the dedicated light
            # refresher. No bundle rebuild fallback — races the light
            # refresher cannot reach belong to the heavy lane.
            try:
                fresh = app._refresh_result_light(rid)
            except Exception as exc:
                return rid, None, f"{type(exc).__name__}: {exc}"
            if not isinstance(fresh, dict) or not fresh.get("id"):
                return rid, None, "light result refresher returned no usable detail"
            return rid, fresh, ""
        try:
            fresh = app._refresh_result_fast(rid)
            if isinstance(fresh, dict) and fresh.get("id"):
                return rid, fresh, ""
        except Exception:
            pass
        # The fast refresher needs a locally stored full detail, which
        # compacted historical races no longer have; rebuild the
        # official result from the bundle detail instead.
        try:
            fresh = _official_refresh_from_bundle(rid, by_id.get(rid))
        except Exception as exc:
            return rid, None, f"{type(exc).__name__}: {exc}"
        if not isinstance(fresh, dict) or not fresh.get("id"):
            return rid, None, "result refresher returned no usable detail"
        return rid, fresh, ""

    for attempt in ((1,) if light else (1, 2)):
        todo = []
        for rid in pending:
            result_ok, payout_ok, _ = result_state(by_id.get(rid))
            if not result_ok or not payout_ok:
                todo.append(rid)
        if not todo:
            break

        print(f"RESULT_REPAIR pass={attempt} pending={len(todo)}")
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(todo)))) as pool:
            futures = {pool.submit(refresh_one, rid): rid for rid in todo}
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    _, fresh, error = fut.result()
                except Exception as exc:
                    fresh, error = None, f"{type(exc).__name__}: {exc}"
                if error:
                    errors[rid] = error
                    print("RESULT_REPAIR_ERROR", rid, error)
                    continue
                before_result = (by_id.get(rid) or {}).get("result") or {}
                merged = merge_detail(by_id.get(rid), fresh)
                by_id[rid] = merged
                _seed_base(rid, merged)
                next_result = merged.get("result") or {}
                # Persist a genuine official advancement immediately: 速報,
                # confirmed placings, or payout updates must not wait for ALL
                # payout types to become available. No fresh-result guesses.
                if next_result != before_result and (
                    next_result.get("finishers") or next_result.get("payouts")
                    or next_result.get("status") in TERMINAL_NO_PAYOUT
                ):
                    published.add(rid)
                result_ok, payout_ok, _ = result_state(merged)
                if result_ok and payout_ok:
                    repaired.add(rid)
                    errors.pop(rid, None)
        if attempt == 1 and not light:
            unresolved_now = [rid for rid in todo if not all(result_state(by_id.get(rid))[:2])]
            if unresolved_now:
                time.sleep(float(os.getenv("ARVEXQ_RESULT_RETRY_SLEEP_SEC", "2")))

    # Environment backfill: races whose result/payout are already
    # complete are never refreshed above, so a stored placeholder
    # ("不明" weather/going from the list builder) would otherwise
    # survive forever. The pass is separate from the result scope: it
    # covers every race in the day bundle (not yet started included)
    # and both circuits (JRA official-first, NAR via keiba.go.jp).
    # Fill the ones the fetchers can observe now and publish them
    # with this run's payload. Light mode skips the pass entirely.
    environment_filled = [] if light else _fill_missing_environment(
        by_id, summary_by_id, [str(r["id"]) for r in rows],
        app._jra_fetch_environment,
        int(os.getenv("ARVEXQ_RESULT_ENV_FILL_LIMIT", "12")),
        fetch_env_nar=_nar_environment_probe)
    for rid in environment_filled:
        published.add(rid)

    # Marks-consistency heal: the candidates were healed from the
    # bundle copies above; register them for publication (the payload
    # assembly swaps their entries in, with any fresher refreshed
    # result transplanted).
    marks_healed: set[str] = set(healed_by_id)
    for rid in sorted(marks_healed):
        published.add(rid)
        print("MARKS_HEALED", rid)

    summaries = []
    for row in rows:
        z = copy.deepcopy(row)
        rid = str(z.get("id") or "")
        detail = by_id.get(rid)
        result = (detail or {}).get("result") or z.get("result") or {}
        status = str(result.get("status") or "")
        result_ok, _, _ = result_state(detail)
        if status in TERMINAL_NO_PAYOUT:
            z["raceStatus"] = status
        elif result_ok:
            z["raceStatus"] = "確定"
        elif result.get("finishers"):
            z["raceStatus"] = "速報"
        summaries.append(z)

    unresolved = []
    payout_missing = []
    for rid in started_ids:
        detail = by_id.get(rid)
        result_ok, payout_ok, status = result_state(detail)
        row = summary_by_id[rid]
        item = {
            "race_id": rid,
            "circuit": row.get("circuit") or "",
            "track": row.get("track") or "",
            "race_no": row.get("raceNumber") or row.get("raceNo") or "",
            "start_time": row.get("startTime") or "",
            "status": status,
            "error": errors.get(rid, ""),
        }
        if not result_ok:
            item["error"] = item["error"] or "result still incomplete"
            unresolved.append(item)
        elif not payout_ok:
            item["error"] = item["error"] or "payout still incomplete"
            payout_missing.append(item)

    # === standing audit check: payout_combination_shape (begin) ===
    # Nightly shape audit over every started race's stored payouts,
    # run after the repair passes: each payout row's combination must
    # match its bet type's arity/range and not repeat within the type
    # (see arvexq.results.state.payout_combination_violations). Races
    # still violating here could not be healed by this run's refresh
    # (e.g. no official result token); they are also payout-incomplete
    # via result_state, so they appear in payout_missing above and the
    # run reports incomplete. Keep this block intact and named when
    # the audit is restructured into named checks.
    combination_violations: list[dict[str, Any]] = []
    if not light:
        for rid in started_ids:
            combination_violations.extend(payout_combination_violations(by_id.get(rid)))
    # === standing audit check: payout_combination_shape (end) ===

    # === standing audit: named checks (begin) ===
    # The same independent named checks the workflow's final verify
    # step runs (arvexq.results.audit), applied here to the post-repair
    # bundle state so the repair report itself names every failure by
    # check and race instead of only result_missing / payout_missing.
    # save_read_back is not judged here (nothing has been saved yet);
    # the workflow audit judges it against the D1 read-back.
    from arvexq.results.audit import audit_detail, summarise

    audit_failures: list[dict[str, Any]] = []
    if not light:
        for rid in started_ids:
            row = summary_by_id[rid]
            audit_failures.extend(audit_detail(
                by_id.get(rid),
                expected_race_id=rid,
                expected_identity={
                    "date": row.get("date") or "",
                    "track": row.get("track") or "",
                    "raceNumber": row.get("raceNumber") or row.get("raceNo") or "",
                },
                now=now, retry_state="in_repair_report"))
    audit_by_check = summarise(audit_failures) if not light else {}
    # === standing audit: named checks (end) ===

    payload_by_id: dict[str, dict[str, Any]] = {
        str(by_id[rid]["id"]): by_id[rid]
        for rid in sorted(published | repaired)
        if isinstance(by_id.get(rid), dict) and by_id[rid].get("id")
    }
    for rid, entry in healed_by_id.items():
        merged = by_id.get(rid) or {}
        merged_result = merged.get("result")
        if isinstance(merged_result, dict) and merged_result != entry.get("result"):
            entry["result"] = copy.deepcopy(merged_result)
            for key in ("resultCname", "fieldSize"):
                if merged.get(key) not in (None, "", 0):
                    entry[key] = merged[key]
        payload_by_id[rid] = entry
    # Compact-tombstone shaping: for races whose stored detail is a
    # nightly-compact tombstone, the seed step recorded the pristine
    # pre-seed stub in a bundle sidecar. The protect layer admits
    # only a result-only write over such a stub, so the payload entry
    # becomes the stub itself with the refreshed result/payout fields
    # overlaid — by construction nothing else can differ. The protect
    # predicate is re-checked here (and again, authoritatively, by
    # protect_detail at sync time); a sidecar entry that does not
    # satisfy it is left unshaped on the normal path.
    tombstone_shaped: list[str] = []
    sidecar = Path(str(bundle_path) + ".tombstone-stubs.json")
    if sidecar.exists():
        from scripts.arvexq_protect_sync import _compact_tombstone_stub
        stubs = (json.loads(sidecar.read_text(encoding="utf-8"))
                 or {}).get("stubs") or {}
        for rid in sorted(stubs):
            entry = payload_by_id.get(rid)
            stub = stubs[rid]
            if not isinstance(entry, dict) or not isinstance(stub, dict):
                continue
            if not _compact_tombstone_stub(stub):
                continue
            shaped = copy.deepcopy(stub)
            for key in ("result", "resultCname", "payouts"):
                if key in entry:
                    shaped[key] = copy.deepcopy(entry[key])
            payload_by_id[rid] = shaped
            tombstone_shaped.append(rid)
    detail_payload = list(payload_by_id.values())
    payload = {
        "summaries": summaries,
        "details": detail_payload,
        "meta": {
            "source": "github-actions-result-repair-v6-domain-split",
            "light_mode": bool(light),
            "light_window_min": int(light_window_min) if light else 0,
            "sync_date": bundle.get("date") or "",
            "started_race_count": len(started_ids),
            "result_pending_before": len(pending),
            "result_repaired_count": len(repaired),
            "marks_healed_count": len(marks_healed),
            "environment_filled_count": len(environment_filled),
            "result_published_count": len(published | repaired),
            "result_missing_count": len(unresolved),
            "payout_missing_count": len(payout_missing),
            "payout_combination_violation_count": len(combination_violations),
            "audit_failure_count": len(audit_failures),
            "audit_failures_by_check": {
                name: bucket["failure_count"]
                for name, bucket in audit_by_check.items()
            },
            "result_detail_write_count": len(detail_payload),
            "tombstone_shaped_count": len(tombstone_shaped),
            "result_repair_complete": not unresolved and not payout_missing,
            "result_repair_at": int(now.timestamp()),
        },
    }
    report = {
        "date": bundle.get("date") or "",
        "light_mode": bool(light),
        "started": len(started_ids),
        "pending_before": len(pending),
        "repaired": sorted(repaired),
        "marks_healed": sorted(marks_healed),
        "environment_filled": sorted(environment_filled),
        "published": sorted(published | repaired),
        "result_missing": unresolved,
        "payout_missing": payout_missing,
        "payout_combination_violations": combination_violations,
        "audit_failures": audit_failures,
        "audit_by_check": audit_by_check,
        "tombstone_shaped": tombstone_shaped,
        "detail_write_count": len(detail_payload),
    }
    _write_json(payload_path, payload)
    _write_json(report_path, report)

    print(
        "RESULT_REPAIR_AUDIT",
        f"started={len(started_ids)}",
        f"pending_before={len(pending)}",
        f"repaired={len(repaired)}",
        f"published={len(published | repaired)}",
        f"detail_write_count={len(detail_payload)}",
        f"result_missing={len(unresolved)}",
        f"payout_missing={len(payout_missing)}",
    )
    for item in unresolved:
        print("RESULT_MISSING", json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    for item in payout_missing:
        print("PAYOUT_MISSING", json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    for item in combination_violations:
        print("PAYOUT_COMBINATION_VIOLATION", json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    for item in audit_failures:
        print("RESULT_AUDIT_FAILURE", json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="bundle.json")
    parser.add_argument("--payload", default="result-repair-payload.json")
    parser.add_argument("--report", default="result-repair-report.json")
    parser.add_argument("--workers", type=int, default=int(os.getenv("ARVEXQ_RESULT_WORKERS", "6")))
    parser.add_argument("--light", action="store_true",
                        help="light lane: only races started within the window, netkeiba-only refresh, single pass")
    parser.add_argument("--light-window-min", type=int,
                        default=int(os.getenv("ARVEXQ_RESULT_LIGHT_WINDOW_MIN", "60")))
    args = parser.parse_args()
    return repair(args.bundle, args.payload, args.report, args.workers,
                  light=bool(args.light), light_window_min=int(args.light_window_min))


if __name__ == "__main__":
    raise SystemExit(main())
