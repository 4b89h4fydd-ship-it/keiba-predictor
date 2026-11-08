#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Named-check audit for repaired results (item 2, 2026-11-08).

Replaces the Result Repair workflow's monolithic inline verify step.
The old step lumped the repair report's result_missing /
payout_missing lists and a podium-only read-back probe into one
anonymous ``result repair incomplete`` failure: when it failed
(2026-11-08 06:21Z / 07:13Z / 07:19Z, every write green) nobody could
tell which race failed which condition.

This runner audits every started race through the independent named
checks in ``arvexq.results.audit`` — result_fetch, race_identity,
finisher_completeness, payout_cross_check (incorporating the standing
payout_combination_shape check), save_read_back — and records each
failure as {check, race_id, failure_class, expected, actual,
timestamp, retry_state}.  Exit status is success iff every non-deferred
check passes; the failure message names the failing check(s) and
race(s).

Grace: a race the repair report still lists as missing whose start
was less than --grace-minutes ago is deferred (official results often
arrive minutes after the start), exactly as the old step deferred it;
its failures are reported with retry_state=deferred_within_grace and
do not fail the run.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.results import JST, row_date, started
from arvexq.results.audit import ALL_CHECKS, audit_race, summarise

try:
    from arvexq.ingest.full_snapshot_codec import KEY as FULL_PAYLOAD_KEY
    from arvexq.ingest.full_snapshot_codec import unpack_detail
except Exception:  # pragma: no cover - codec is present in repo
    FULL_PAYLOAD_KEY = ""
    unpack_detail = None


def _read_json(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _active(row: Any) -> bool:
    """Same retired-Banei exclusion as the repair lane."""
    if not isinstance(row, dict) or not row.get("id"):
        return False
    rid = str(row["id"])
    return (str(row.get("track") or "") not in ("帯広", "帯広ば")
            and "-帯広-" not in rid and "-帯広ば-" not in rid)


def _fetch_read_back(api_base: str, rid: str, attempts: int = 4) -> tuple[dict[str, Any] | None, str]:
    url = (api_base.rstrip("/") + "/api/race/" +
           urllib.parse.quote(rid, safe="") +
           "?t=" + str(int(time.time() * 1000)))
    err = ""
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url, headers={"accept": "application/json",
                              "user-agent": "ARVEXQ-Result-Verify/2"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                value = json.loads(resp.read().decode("utf-8"))
            if isinstance(value, dict):
                candidates = [value, value.get("detail"), value.get("race")]
                for item in candidates:
                    if isinstance(item, dict) and str(item.get("id") or "") == rid:
                        if FULL_PAYLOAD_KEY and FULL_PAYLOAD_KEY in item \
                                and unpack_detail is not None:
                            item = unpack_detail(item)
                        return item, ""
                err = "race endpoint returned no matching detail"
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            time.sleep(1 + attempt)
    return None, err


def _retry_state(rid: str, summary: dict[str, Any], report: dict[str, Any],
                 now: datetime, grace_minutes: int) -> str:
    if rid in {str(x) for x in (report.get("repaired") or [])}:
        return "repaired_this_run"
    pending_items: dict[str, dict[str, Any]] = {}
    for key in ("result_missing", "payout_missing"):
        for item in report.get(key) or []:
            if isinstance(item, dict) and item.get("race_id"):
                pending_items[str(item["race_id"])] = item
    if rid not in pending_items:
        return "not_pending"
    item = pending_items[rid]
    day = str(row_date(summary) or item.get("date")
              or report.get("date") or "")
    start = str(summary.get("startTime") or summary.get("start_time")
                or summary.get("scheduledStartTime")
                or item.get("start_time") or "")
    try:
        dt = datetime.strptime(day + " " + start, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
        age = (now - dt).total_seconds() / 60
    except (TypeError, ValueError):
        age = None
    if age is not None and 0 <= age < grace_minutes:
        return "deferred_within_grace"
    return "due"


def run_audit(bundle: dict[str, Any], report: dict[str, Any], *,
              api_base: str = "",
              read_back_details: dict[str, dict[str, Any]] | None = None,
              payload: dict[str, Any] | None = None,
              now: datetime | None = None,
              grace_minutes: int = 15) -> dict[str, Any]:
    """Audit one day bundle; returns the audit report dict.

    Read-back details come from --api-base fetches when an API base is
    given, else from ``read_back_details`` (an independently fetched
    bundle's details), else the bundle details themselves (they were
    read from D1 by the bundle fetcher).

    The save_read_back comparison source is the repair *payload*
    detail for races the lane published this run (that is the detail
    that was supposed to be saved — comparing against the pre-repair
    bundle would flag every genuine repair as a mismatch), and the
    bundle detail for all other races.
    """
    moment = now if isinstance(now, datetime) else datetime.now(JST)
    rows = [r for r in (bundle.get("races") or []) if _active(r)]
    source_by_id = {str(d["id"]): d for d in (bundle.get("details") or [])
                    if _active(d) and d.get("id")}
    if payload:
        for d in payload.get("details") or []:
            if isinstance(d, dict) and d.get("id"):
                source_by_id[str(d["id"])] = d
    summary_by_id = {str(r["id"]): r for r in rows}

    started_ids = [str(r["id"]) for r in rows if started(r, moment)]
    # Races the repair report flags stay in scope even if the bundle's
    # started() judgement differs (defensive; normally identical).
    for key in ("result_missing", "payout_missing"):
        for item in report.get(key) or []:
            if isinstance(item, dict) and item.get("race_id"):
                rid = str(item["race_id"])
                if rid in summary_by_id and rid not in started_ids:
                    started_ids.append(rid)

    failures: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for rid in started_ids:
        summary = summary_by_id[rid]
        source = source_by_id.get(rid)
        retry_state = _retry_state(rid, summary, report, moment, grace_minutes)
        fetch_error = ""
        if api_base:
            read_back, fetch_error = _fetch_read_back(api_base, rid)
        elif read_back_details is not None:
            read_back = read_back_details.get(rid)
            fetch_error = "" if read_back else "no read-back detail returned"
        else:
            read_back = source
        identity = {
            "date": row_date(summary) or "",
            "track": summary.get("track") or "",
            "raceNumber": summary.get("raceNumber") or summary.get("raceNo")
            or summary.get("race_no") or "",
        }
        records = audit_race(
            source, read_back,
            expected_race_id=rid,
            expected_identity=identity,
            fetched=read_back is not None or source is not None,
            fetch_error=fetch_error,
            read_back_error=fetch_error,
            now=moment, retry_state=retry_state)
        for record in records:
            if retry_state == "deferred_within_grace":
                deferred.append(record)
            else:
                failures.append(record)

    by_check = summarise(failures)
    return {
        "date": bundle.get("date") or report.get("date") or "",
        "generated_at": moment.isoformat(),
        "started_race_count": len(started_ids),
        "success": not failures,
        "checks": by_check,
        "failures": failures,
        "deferred_failures": deferred,
        "deferred_race_ids": sorted({str(r.get("race_id") or "") for r in deferred}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="bundle.json")
    parser.add_argument("--report", default="result-repair-report.json")
    parser.add_argument("--payload", default="",
                        help="repair payload JSON; its details are the "
                             "save_read_back comparison source for "
                             "published races")
    parser.add_argument("--readback-bundle", default="",
                        help="second, independently fetched bundle whose "
                             "details are the save read-back view")
    parser.add_argument("--api-base", default="",
                        help="when set, read each started race back from "
                             "this API base instead of a bundle")
    parser.add_argument("--out", default="result-audit-report.json")
    parser.add_argument("--grace-minutes", type=int, default=15)
    parser.add_argument("--now", default="",
                        help="ISO timestamp override (tests/reproduction)")
    args = parser.parse_args()

    bundle = _read_json(args.bundle)
    report = _read_json(args.report)
    payload = _read_json(args.payload) if args.payload else None
    read_back_details = None
    if args.readback_bundle:
        other = _read_json(args.readback_bundle)
        read_back_details = {str(d["id"]): d
                             for d in (other.get("details") or [])
                             if isinstance(d, dict) and d.get("id")}
    now = None
    if args.now:
        parsed = datetime.fromisoformat(args.now)
        now = parsed if parsed.tzinfo else parsed.replace(tzinfo=JST)

    audit = run_audit(bundle, report, api_base=args.api_base,
                      read_back_details=read_back_details, payload=payload,
                      now=now, grace_minutes=args.grace_minutes)
    Path(args.out).write_text(json.dumps(audit, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    for record in audit["failures"]:
        print("RESULT_AUDIT_FAILURE", json.dumps(record, ensure_ascii=False,
                                                 separators=(",", ":")))
    for record in audit["deferred_failures"]:
        print("RESULT_AUDIT_DEFERRED", json.dumps(record, ensure_ascii=False,
                                                  separators=(",", ":")))
    counts = {name: audit["checks"][name]["failure_count"] for name in ALL_CHECKS}
    print("RESULT_AUDIT_SUMMARY",
          f"success={audit['success']}",
          f"started={audit['started_race_count']}",
          f"failures_by_check={json.dumps(counts, ensure_ascii=False)}",
          f"deferred_races={len(audit['deferred_race_ids'])}")
    if not audit["success"]:
        failing_checks = sorted({str(r.get("check") or "")
                                 for r in audit["failures"]})
        failing_races = sorted({str(r.get("race_id") or "")
                                for r in audit["failures"]})
        raise SystemExit(
            "result audit failed: checks=[" + ",".join(failing_checks) +
            "] races=[" + ",".join(failing_races) + "]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
