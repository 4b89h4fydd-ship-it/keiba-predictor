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
    if detail.get("predictionStatus") != "ready":
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


def repair(bundle_path: str, payload_path: str, report_path: str, workers: int = 6) -> int:
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
    for rid in started_ids:
        candidate = copy.deepcopy(by_id.get(rid) or {})
        if candidate.get("id") and _heal_marks_consistency(candidate):
            healed_by_id[rid] = candidate

    pending = []
    for rid in started_ids:
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
        try:
            fresh = app._refresh_result_fast(rid)
            if not isinstance(fresh, dict) or not fresh.get("id"):
                return rid, None, "result refresher returned no usable detail"
            return rid, fresh, ""
        except Exception as exc:
            return rid, None, f"{type(exc).__name__}: {exc}"

    for attempt in (1, 2):
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
        if attempt == 1:
            unresolved_now = [rid for rid in todo if not all(result_state(by_id.get(rid))[:2])]
            if unresolved_now:
                time.sleep(float(os.getenv("ARVEXQ_RESULT_RETRY_SLEEP_SEC", "2")))

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
    audit_by_check = summarise(audit_failures)
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
    detail_payload = list(payload_by_id.values())
    payload = {
        "summaries": summaries,
        "details": detail_payload,
        "meta": {
            "source": "github-actions-result-repair-v6-domain-split",
            "sync_date": bundle.get("date") or "",
            "started_race_count": len(started_ids),
            "result_pending_before": len(pending),
            "result_repaired_count": len(repaired),
            "marks_healed_count": len(marks_healed),
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
            "result_repair_complete": not unresolved and not payout_missing,
            "result_repair_at": int(now.timestamp()),
        },
    }
    report = {
        "date": bundle.get("date") or "",
        "started": len(started_ids),
        "pending_before": len(pending),
        "repaired": sorted(repaired),
        "marks_healed": sorted(marks_healed),
        "published": sorted(published | repaired),
        "result_missing": unresolved,
        "payout_missing": payout_missing,
        "payout_combination_violations": combination_violations,
        "audit_failures": audit_failures,
        "audit_by_check": audit_by_check,
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
    args = parser.parse_args()
    return repair(args.bundle, args.payload, args.report, args.workers)


if __name__ == "__main__":
    raise SystemExit(main())
