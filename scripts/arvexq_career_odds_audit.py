#!/usr/bin/env python3
"""Read-only audit: per-horse career-history state and win-odds state.

GET only against the race API. Never writes to D1, the repo, or production.
Evidence-limited: causes are only reported when a record supports them.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

API_BASE = os.environ.get("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
OUT_DIR = os.environ.get("ARVEXQ_OUT_DIR", "audit_out")
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


def get_json(url: str, retries: int = 2) -> dict:
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"user-agent": "ARVEXQ-readonly-audit/1.0", "accept": "application/json"}, method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def classify_history(analysis: dict) -> tuple[str, str]:
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


def classify_odds(horse: dict, live: dict | None) -> dict:
    status = str((live or {}).get("horse_status") or horse.get("status") or "").strip()
    scratched = bool(horse.get("scratched")) or bool(SCRATCH_RE.search(status))
    real = (live or {}).get("win_odds")
    if real is None and live is None:
        real = None
    forecast = horse.get("oddsForecast")
    if real is not None:
        state = "実オッズ取得済み"
    elif scratched:
        state = "未取得(出走取消・除外の記録あり)"
    else:
        state = "未取得・原因不明"
    return {
        "odds_state": state,
        "real_win_odds": real,
        "real_popularity": (live or {}).get("popularity"),
        "real_odds_updated_at_epoch": (live or {}).get("updated_at"),
        "horse_status": status or None,
        "forecast_odds": forecast,
        "odds_source_label": horse.get("oddsSource"),
    }


def main() -> int:
    date = os.environ.get("ARVEXQ_DATE") or datetime.now(JST).date().isoformat()
    fetched_at = datetime.now(JST).isoformat(timespec="seconds")
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        from arvexq.career_missing import build_career_analysis
        analysis_error = None
    except Exception as exc:  # noqa: BLE001
        build_career_analysis = None
        analysis_error = f"{type(exc).__name__}: {exc}"

    summary = {"version": "arvexq-career-odds-audit-v1", "date": date, "apiBase": API_BASE, "fetchedAtJst": fetched_at,
               "readOnly": True, "analysisModuleError": analysis_error}
    rows: list[dict] = []
    failed_races: list[dict] = []

    try:
        day = get_json(f"{API_BASE}/api/day?" + urllib.parse.urlencode({"date": date, "details": "0"}))
        races = day.get("races") or []
    except Exception as exc:  # noqa: BLE001
        summary.update({"dayListError": str(exc), "auditComplete": False, "auditStatus": "監査不完全(レース一覧の取得失敗)"})
        with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return 2

    for race in races:
        rid = str(race.get("id") or "")
        try:
            payload = get_json(f"{API_BASE}/api/race/{urllib.parse.quote(rid, safe='')}")
            if not payload.get("ok") or not isinstance(payload.get("detail"), dict):
                raise RuntimeError(f"unusable-response ok={payload.get('ok')}")
        except Exception as exc:  # noqa: BLE001
            failed_races.append({"race_id": rid, "circuit": race.get("circuit"), "track": race.get("track"),
                                 "raceNumber": race.get("raceNumber"), "error": str(exc)})
            continue
        detail = payload["detail"]
        live_by_no = {}
        for o in payload.get("odds") or []:
            try:
                live_by_no[int(o.get("horse_no"))] = o
            except (TypeError, ValueError):
                pass
        rdict = {"date": detail.get("date") or race.get("date"), "raceDate": detail.get("date") or race.get("date")}
        for horse in detail.get("horses") or []:
            if not isinstance(horse, dict):
                continue
            try:
                no = int(float(horse.get("horseNumber") or 0))
            except (TypeError, ValueError):
                no = 0
            row = {"race_id": rid, "circuit": detail.get("circuit") or race.get("circuit"), "track": detail.get("track") or race.get("track"),
                   "raceNumber": detail.get("raceNumber") or race.get("raceNumber"), "horseNumber": no or None, "name": horse.get("name")}
            if build_career_analysis is None:
                row.update({"history_class": L_UNDECIDABLE, "history_reason": f"analysis-module-unavailable:{analysis_error}",
                            "career_state_raw": None, "acquisition_status": None, "field_completeness": None,
                            "failedProviders": "", "provider_error_present": None})
            else:
                try:
                    ca = build_career_analysis(horse, rdict)
                    cls, why = classify_history(ca)
                    ev = ca.get("acquisition_evidence") or {}
                    fp = ev.get("failedProviders") or []
                    row.update({"history_class": cls, "history_reason": why, "career_state_raw": ca.get("career_state"),
                                "acquisition_status": ca.get("acquisition_status"), "field_completeness": ca.get("field_completeness"),
                                "eligible_dated_runs": ca.get("eligible_dated_runs"), "reportedStarts": ev.get("reportedStarts"),
                                "failedProviders": ";".join(map(str, fp)), "provider_error_present": bool(fp)})
                except Exception as exc:  # noqa: BLE001
                    row.update({"history_class": L_UNDECIDABLE, "history_reason": f"analysis-exception:{type(exc).__name__}:{exc}",
                                "career_state_raw": None, "acquisition_status": None, "field_completeness": None,
                                "failedProviders": "", "provider_error_present": None})
            row.update(classify_odds(horse, live_by_no.get(no)))
            rows.append(row)

    ok_races = len(races) - len(failed_races)
    complete = not failed_races and len(races) > 0 and build_career_analysis is not None
    summary.update({
        "targetRaces": len(races), "detailFetchSucceeded": ok_races, "detailFetchFailed": len(failed_races),
        "failedRaces": failed_races, "horsesInFetchedRaces": len(rows),
        "horsesInFailedRaces": "不明(詳細未取得のため0とは扱わない)" if failed_races else 0,
        "historyClassCounts": dict(Counter(r["history_class"] for r in rows)),
        "oddsStateCounts": dict(Counter(r["odds_state"] for r in rows)),
        "providerErrorPresentHorses": sum(1 for r in rows if r.get("provider_error_present")),
        "auditComplete": complete,
        "auditStatus": "監査完了" if complete else "監査不完全(取得失敗または分析モジュール未読込あり。欠損0とは判断しない)",
        "notUnverified": ["failedProviders/paginationComplete の付与元(app.py)は未確認", "オッズ取得エラーの保存先は未確認"],
    })
    with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    cols = sorted({k for r in rows for k in r}) if rows else []
    with open(os.path.join(OUT_DIR, "horses.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("ARVEXQ_CAREER_ODDS_AUDIT_SUMMARY=" + json.dumps({k: summary[k] for k in ("date", "targetRaces", "detailFetchSucceeded", "detailFetchFailed", "horsesInFetchedRaces", "auditStatus")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
