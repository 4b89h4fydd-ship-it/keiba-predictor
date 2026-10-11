#!/usr/bin/env python3
"""Read-only audit: per-horse career-history state and win-odds state.

GET only against the race API. Never writes to D1, the repo, or production.
Causes are reported only when a record supports them.
Exit codes: 0 audit ran (see auditComplete), 2 race list failed, 3 arvexq import
failed (audit program failure), 4 output consistency check failed.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import traceback
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

API_BASE = os.environ.get("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
OUT_DIR = os.environ.get("ARVEXQ_OUT_DIR", "audit_out")
TIMEOUT = 30
MAX_RETRIES = 2
MAX_WORKERS = min(4, max(1, int(os.environ.get("ARVEXQ_WORKERS", "3") or 3)))
JST = timezone(timedelta(hours=9))
SCRATCH_RE = re.compile(r"(?:出走取消|取消|競走除外|競走取消|除外|SCRATCHED)", re.I)

L_UNDECIDABLE = "判定不能"
L_ZERO = "出走歴0(証拠で確認)"
L_FULL = "履歴が完全に揃っている"
L_COUNT_OK_MISSING = "履歴件数は充足・項目欠損あり"
L_INSUFFICIENT = "履歴不足・取得未完了の証拠"
L_NO_PROOF = "取得証拠不足"

NO_AUDIT_REASONS = {"no-acquisition-evidence", "audit-not-bound-to-this-race-date", "race-date-unknown"}
KNOWN_STATES = {
    "race-date-unverified", "no-history", "history-present-but-unusable", "partially-acquired",
    "acquisition-unverified", "complete-no-starts", "complete-with-missing-fields", "complete",
}
CSV_FIELDS = [
    "race_id", "circuit", "track", "raceNumber", "horseNumber", "name",
    "history_class", "history_reason", "career_state_raw", "acquisition_status", "field_completeness",
    "eligible_dated_runs", "reportedStarts", "failedProviders", "provider_error_state",
    "pagination_state", "evidence_caveat",
    "odds_state", "real_odds_row_present", "real_win_odds", "real_popularity", "real_odds_updated_at_epoch",
    "horse_status", "forecast_odds", "odds_source_label",
]


def get_json(url, opener=None, sleep=time.sleep):
    opener = opener or urllib.request.urlopen
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"user-agent": "ARVEXQ-readonly-audit/1.0", "accept": "application/json"}, method="GET")
            with opener(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < MAX_RETRIES:
                sleep(1 + attempt)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def classify_history(analysis):
    state = analysis.get("career_state")
    acq = analysis.get("acquisition_status")
    ev = analysis.get("acquisition_evidence") or {}
    reason = ev.get("reason")
    failed = bool(ev.get("failedProviders"))
    if state not in KNOWN_STATES:
        return L_UNDECIDABLE, f"unexpected-career_state:{state}"
    if state == "race-date-unverified" or acq == "race-date-unverified":
        return L_UNDECIDABLE, "race-date-unverified"
    if acq == "partial":
        return L_INSUFFICIENT, reason or "partial"
    if acq == "unverified":
        if reason in NO_AUDIT_REASONS:
            return L_UNDECIDABLE, reason
        if failed:
            return L_INSUFFICIENT, f"{reason or 'unverified'}+failedProviders"
        return L_NO_PROOF, reason or "unverified"
    if acq == "complete":
        if state == "complete-no-starts":
            return L_ZERO, reason or "reported-starts-matched"
        if state == "complete":
            return L_FULL, reason or "reported-starts-matched"
        if state in ("complete-with-missing-fields", "history-present-but-unusable"):
            return L_COUNT_OK_MISSING, f"{state}:{','.join(analysis.get('missing_fields') or [])}"
    return L_UNDECIDABLE, f"unexpected-combination:{state}/{acq}"


def audit_field_states(horse):
    audit = horse.get("_careerHistoryAudit")
    if not isinstance(audit, dict):
        return "不明(取得監査なし)", "不明(取得監査なし)"
    if "failedProviders" not in audit:
        provider = "不明(欄なし)"
    else:
        provider = "あり" if audit.get("failedProviders") else "なし(欄あり)"
    if "paginationComplete" not in audit:
        pagination = "不明(欄なし)"
    elif audit["paginationComplete"] is True:
        pagination = "完了"
    elif audit["paginationComplete"] is False:
        pagination = "未完了"
    else:
        pagination = "不明(値が想定外)"
    return provider, pagination


def classify_odds(horse, live):
    status = str((live or {}).get("horse_status") or horse.get("status") or "").strip()
    scratched = horse.get("scratched") is True or bool(SCRATCH_RE.search(status))
    real = (live or {}).get("win_odds")
    if real is not None:
        state = "実オッズ取得済み"
    elif scratched:
        state = "未取得(出走取消・除外の記録あり)"
    else:
        state = "未取得・原因不明"
    return {
        "odds_state": state, "real_odds_row_present": live is not None, "real_win_odds": real,
        "real_popularity": (live or {}).get("popularity"), "real_odds_updated_at_epoch": (live or {}).get("updated_at"),
        "horse_status": status or None, "forecast_odds": horse.get("oddsForecast"), "odds_source_label": horse.get("oddsSource"),
    }


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def horse_row(race, detail, horse, live_by_no, analysis_fn):
    try:
        no = int(float(horse.get("horseNumber") or 0))
    except (TypeError, ValueError):
        no = 0
    row = {k: None for k in CSV_FIELDS}
    row.update({"race_id": str(race.get("id") or ""), "circuit": detail.get("circuit") or race.get("circuit"),
                "track": detail.get("track") or race.get("track"), "raceNumber": detail.get("raceNumber") or race.get("raceNumber"),
                "horseNumber": no or None, "name": horse.get("name")})
    provider, pagination = audit_field_states(horse)
    row["provider_error_state"], row["pagination_state"] = provider, pagination
    rdate = detail.get("date") or race.get("date")
    try:
        ca = analysis_fn(horse, {"date": rdate, "raceDate": rdate})
        cls, why = classify_history(ca)
        ev = ca.get("acquisition_evidence") or {}
        row.update({"history_class": cls, "history_reason": why, "career_state_raw": ca.get("career_state"),
                    "acquisition_status": ca.get("acquisition_status"), "field_completeness": ca.get("field_completeness"),
                    "eligible_dated_runs": ca.get("eligible_dated_runs"), "reportedStarts": ev.get("reportedStarts"),
                    "failedProviders": ";".join(map(str, ev.get("failedProviders") or []))})
    except Exception as exc:  # noqa: BLE001
        row.update({"history_class": L_UNDECIDABLE, "history_reason": f"analysis-exception:{type(exc).__name__}:{exc}"})
    if row["history_class"] in (L_FULL, L_ZERO, L_COUNT_OK_MISSING) and (provider.startswith("不明") or pagination.startswith("不明")):
        row["evidence_caveat"] = "failedProviders/paginationComplete欄が無い。エラーなし・取得完了とは解釈しない"
    row.update(classify_odds(horse, live_by_no.get(no)))
    return row


def run(date, fetch, analysis_fn, out_dir, fetched_at=None):
    fetched_at = fetched_at or datetime.now(JST).isoformat(timespec="seconds")
    os.makedirs(out_dir, exist_ok=True)
    summary = {"version": "arvexq-career-odds-audit-v2", "date": date, "apiBase": API_BASE, "fetchedAtJst": fetched_at,
               "readOnly": True, "maxWorkers": MAX_WORKERS, "timeoutSec": TIMEOUT, "maxRetries": MAX_RETRIES}
    try:
        day = fetch(f"{API_BASE}/api/day?" + urllib.parse.urlencode({"date": date, "details": "0"}))
        races = day.get("races") or []
    except Exception as exc:  # noqa: BLE001
        summary.update({"dayListError": str(exc), "auditComplete": False, "auditStatus": "監査不完全(レース一覧の取得失敗)"})
        write_json(os.path.join(out_dir, "summary.json"), summary)
        return 2
    api_missing = [str(x) for x in (day.get("missing") or [])]
    api_complete = day.get("complete")

    def fetch_race(race):
        rid = str(race.get("id") or "")
        try:
            payload = fetch(f"{API_BASE}/api/race/{urllib.parse.quote(rid, safe='')}")
            if not payload.get("ok") or not isinstance(payload.get("detail"), dict):
                raise RuntimeError(f"unusable-response ok={payload.get('ok')}")
            return race, payload, None
        except Exception as exc:  # noqa: BLE001
            return race, None, str(exc)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(fetch_race, races))
    rows, failed = [], []
    for race, payload, err in results:
        if payload is None:
            failed.append({"race_id": str(race.get("id") or ""), "circuit": race.get("circuit"), "track": race.get("track"),
                           "raceNumber": race.get("raceNumber"), "error": err})
            continue
        live_by_no = {}
        for o in payload.get("odds") or []:
            try:
                live_by_no[int(o.get("horse_no"))] = o
            except (TypeError, ValueError):
                pass
        for horse in payload["detail"].get("horses") or []:
            if isinstance(horse, dict):
                rows.append(horse_row(race, payload["detail"], horse, live_by_no, analysis_fn))

    reasons = []
    if not races:
        reasons.append("対象レース0件")
    if failed:
        reasons.append("詳細取得失敗あり")
    if api_complete is False:
        reasons.append("API complete=false")
    if api_missing:
        reasons.append("API missingあり")
    complete = not reasons
    summary.update({
        "targetRaces": len(races), "detailFetchSucceeded": len(races) - len(failed), "detailFetchFailed": len(failed),
        "failedRaces": failed, "horsesInFetchedRaces": len(rows),
        "horsesInFailedRaces": "不明(詳細未取得のため0とは扱わない)" if failed else 0,
        "apiComplete": api_complete, "apiMissing": api_missing,
        "apiNote": "details=0のためmissing/completeは一覧由来。詳細の欠落はdetailFetchFailedで判定",
        "historyClassCounts": dict(Counter(r["history_class"] for r in rows)),
        "oddsStateCounts": dict(Counter(r["odds_state"] for r in rows)),
        "providerErrorStateCounts": dict(Counter(r["provider_error_state"] for r in rows)),
        "paginationStateCounts": dict(Counter(r["pagination_state"] for r in rows)),
        "auditComplete": complete, "incompleteReasons": reasons,
        "auditStatus": "監査完了" if complete else "監査不完全(" + "、".join(reasons) + ")。欠損0とは判断しない",
        "unverified": ["failedProviders/paginationComplete の付与元(app.py)は未確認", "オッズ取得エラーの保存先は未確認"],
    })
    csv_path = os.path.join(out_dir, "horses.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    problems = []
    if len(csv_rows) != len(rows):
        problems.append("csv-row-count")
    if sum(summary["historyClassCounts"].values()) != len(rows):
        problems.append("history-class-count")
    if sum(summary["oddsStateCounts"].values()) != len(rows):
        problems.append("odds-state-count")
    if summary["detailFetchSucceeded"] + summary["detailFetchFailed"] != summary["targetRaces"]:
        problems.append("race-count")
    if Counter(r["history_class"] for r in csv_rows) != Counter(summary["historyClassCounts"]):
        problems.append("csv-vs-summary-classes")
    summary["consistencyOk"] = not problems
    summary["consistencyProblems"] = problems
    write_json(os.path.join(out_dir, "summary.json"), summary)
    write_json(os.path.join(out_dir, "horses.json"), rows)
    print("ARVEXQ_CAREER_ODDS_AUDIT_SUMMARY=" + json.dumps({k: summary[k] for k in (
        "date", "targetRaces", "detailFetchSucceeded", "detailFetchFailed", "horsesInFetchedRaces", "auditStatus", "consistencyOk")}, ensure_ascii=False))
    return 0 if not problems else 4


def main():
    date = os.environ.get("ARVEXQ_DATE") or datetime.now(JST).date().isoformat()
    try:
        from arvexq.career_missing import build_career_analysis
    except Exception as exc:  # noqa: BLE001
        trace = traceback.format_exc()
        print("ARVEXQ_AUDIT_PROGRAM_FAILURE: cannot import arvexq.career_missing\n" + trace, file=sys.stderr)
        os.makedirs(OUT_DIR, exist_ok=True)
        write_json(os.path.join(OUT_DIR, "summary.json"), {
            "version": "arvexq-career-odds-audit-v2", "date": date, "readOnly": True, "runFailure": "import-failed",
            "error": f"{type(exc).__name__}: {exc}", "traceback": trace, "auditComplete": False,
            "auditStatus": "監査プログラムの実行失敗(馬のデータの判定不能ではない)"})
        return 3
    return run(date, get_json, build_career_analysis, OUT_DIR)


if __name__ == "__main__":
    sys.exit(main())
