#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill ONLY result.finishers[*].marginText for stored JRA races whose
stored result came through the netkeiba fallback.

Why this exists: the same fallback result parser that dropped final
popularity also dropped the margin text for every finisher (it never
read the desktop layout's margin column, and the smartphone layout it
fetches carries the margin inside the time cell, which it ignored).
Stored fallback results of 2026-10-25..11-08 therefore carry no
marginText on any placed finisher (0 of 978 placed finishers across
the five days, against 828 of 828 for official-sourced results). The
official JRA parse carries the column, so this lane re-parses the
OFFICIAL result page for each affected race, collates it against the
stored finishers (same horses, same finishes), and copies only the
marginText subfield. The winner's official marginText is "" and is
never a fill target. Payouts, the finishers' other fields, cards and
forecasts are never touched. A race whose official parse disagrees
with the stored finishers in any way is skipped, not forced.

Discipline: sequential official fetches with a pause between races;
an HTTP 403/429 from jra.go.jp aborts the whole run (exit 3) instead
of pushing through.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import re

import app

ACCESS_S = "https://www.jra.go.jp/JRADB/accessS.html"
_SRL_RE = re.compile(r"pw01srl(?:00|01|10)\d{18}(?:/|%2F)[0-9A-Fa-f]{2}", re.I)


class _Aborted(Exception):
    """Official fetch drew HTTP 403/429: stop the whole run."""


def _request(url: str, cname: str | None, cache_sec: int) -> str:
    try:
        return app._jra_request(url, cname, cache_sec)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise _Aborted(f"http-{exc.code}") from exc
        raise


class _TokenDiscovery:
    """Result-token discovery for PAST race days via the official
    past-results menu (homepage seed -> month selector -> meeting ->
    result tokens), mirroring app._jra_prior_result_cnames but with
    the 00 token variant the current month carries (the production
    helper's meeting regex predates it). Tokens are always taken from
    official pages, never assembled."""

    def __init__(self, sleep_sec: float) -> None:
        self.sleep_sec = sleep_sec
        self._month_pages: dict[str, str] = {}
        self._by_meeting: dict[tuple[str, str], dict[int, str]] = {}

    def _month_page(self, yyyymm: str) -> str:
        if yyyymm in self._month_pages:
            return self._month_pages[yyyymm]
        home = _request("https://www.jra.go.jp/", None, 86400)
        seed = re.search(
            r"doAction\('/JRADB/accessS.html',\s*'(pw01skl[^']+)'", home)
        if not seed:
            raise ValueError("JRA past-results menu link absent")
        time.sleep(self.sleep_sec)
        menu = _request(ACCESS_S, seed.group(1), 86400)
        published = dict(re.findall(
            r'objParam\["(\d{4})"\]="([0-9A-Fa-f]{2})"', menu))
        current = re.search(r'var\s+yearMonth\s*=\s*"(\d{6})"', menu)
        if yyyymm[2:] not in published or not current:
            raise ValueError("JRA month selector token absent for " + yyyymm)
        selector = ("pw01skl" + ("00" if yyyymm >= current.group(1) else "10")
                    + yyyymm + "/" + published[yyyymm[2:]])
        time.sleep(self.sleep_sec)
        page = _request(ACCESS_S, selector, 86400)
        self._month_pages[yyyymm] = page
        return page

    def result_cnames(self, iso_date: str, track: str) -> dict[int, str]:
        key = (iso_date, track)
        if key in self._by_meeting:
            return self._by_meeting[key]
        code = app.JRA_TRACK_CODE_BY_NAME.get(track, "")
        if not code:
            self._by_meeting[key] = {}
            return {}
        page = self._month_page(iso_date[:7].replace("-", ""))
        links = list(dict.fromkeys(
            app._jra_norm_cname(x) for x in _SRL_RE.findall(page)))
        yyyymmdd = iso_date.replace("-", "")

        def digits(tok: str) -> str:
            return tok[9:-3] if len(tok) > 12 else ""

        meetings = [t for t in links
                    if digits(t)[:2] == code and digits(t)[-8:] == yyyymmdd]
        if not meetings:
            meetings = [t for t in links if digits(t)[:2] == code]
        found: dict[int, str] = {}
        for meeting in meetings:
            time.sleep(self.sleep_sec)
            mpage = _request(ACCESS_S, meeting, 86400)
            for tok in dict.fromkeys(
                    app._jra_norm_cname(x)
                    for x in app.JRA_RESULT_CNAME_RE.findall(mpage)):
                if app._jra_date_from_cname(tok) == iso_date \
                        and app._jra_any_track(tok) == track:
                    no = app._jra_any_race_no(tok)
                    if no:
                        found[no] = tok
            if found:
                break
        self._by_meeting[key] = found
        return found


def _read_json(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: str, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _targets(detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Placed finishers (finish >= 2) whose margin text is missing
    (empty list = not a target). The winner's marginText is "" by
    definition on the official table, so finish == 1 never targets."""
    fins = ((detail.get("result") or {}).get("finishers")) or []
    return [f for f in fins if isinstance(f, dict)
            and int(f.get("finish") or 0) >= 2
            and not str(f.get("marginText") or "")]


def _official_result(detail: dict[str, Any],
                     discovery: _TokenDiscovery) -> dict[str, Any] | None:
    """Official JRA result block for this race. Token order: the stored
    result token (identity-checked), then the past-results menu
    traversal for the race's date/track."""
    result_cname = str(detail.get("resultCname") or "")
    if result_cname and not app._jra_result_cname_matches_detail(
            result_cname, detail):
        result_cname = ""
    if not result_cname:
        tokens = discovery.result_cnames(
            str(detail.get("date") or ""), str(detail.get("track") or ""))
        result_cname = tokens.get(int(detail.get("raceNumber") or 0), "")
    if not result_cname:
        return None
    try:
        parsed = app._jra_parse_result(result_cname, detail, strict_errors=True)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise _Aborted(f"http-{exc.code}") from exc
        raise
    if not parsed:
        return None
    # Identity guard (same rule as _merge_official_result): an official
    # block naming a different race is never used.
    for key in ("date", "track", "raceNumber"):
        mine, theirs = detail.get(key), parsed.get(key)
        if mine not in (None, "", 0) and theirs not in (None, "", 0) \
                and str(mine) != str(theirs):
            return None
    return parsed.get("result") or None


def repair(bundle_path: str, payload_path: str, report_path: str) -> int:
    bundle = _read_json(bundle_path)
    details = [d for d in (bundle.get("details") or [])
               if isinstance(d, dict) and str(d.get("id") or "").startswith("jra-")]
    rows = {str(r.get("id") or ""): r for r in (bundle.get("races") or [])
            if isinstance(r, dict)}
    sleep_sec = float(os.getenv("MARGIN_REPAIR_SLEEP_SEC", "2"))
    discovery = _TokenDiscovery(sleep_sec)
    targets: list[str] = []
    repaired: list[str] = []
    skipped: list[dict[str, str]] = []
    official_margin: dict[str, dict[str, str]] = {}
    changed_fields: dict[str, int] = {}
    changed_details: list[dict[str, Any]] = []
    aborted = ""

    for detail in details:
        rid = str(detail.get("id") or "")
        missing = _targets(detail)
        if not missing:
            continue
        targets.append(rid)
        try:
            official = _official_result(detail, discovery)
        except _Aborted as exc:
            aborted = str(exc)
            skipped.append({"race_id": rid,
                            "reason": f"aborted: official fetch {aborted}"})
            break
        except urllib.error.HTTPError as exc:
            skipped.append({"race_id": rid,
                            "reason": f"official fetch HTTP {exc.code}"})
            continue
        except Exception as exc:
            skipped.append({"race_id": rid,
                            "reason": f"official fetch failed: {type(exc).__name__}: {exc}"[:200]})
            continue
        finally:
            time.sleep(sleep_sec)
        if not official:
            skipped.append({"race_id": rid, "reason": "official result unavailable"})
            continue
        off = {int(f.get("horseNumber") or 0): f
               for f in (official.get("finishers") or [])
               if int(f.get("horseNumber") or 0) > 0}
        sto = {int(f.get("horseNumber") or 0): f
               for f in ((detail.get("result") or {}).get("finishers") or [])
               if int(f.get("horseNumber") or 0) > 0}
        reason = ""
        if set(off) != set(sto):
            reason = (f"finisher set mismatch: stored={sorted(sto)} "
                      f"official={sorted(off)}")
        else:
            for no, f in sto.items():
                if int(f.get("finish") or 0) != int(off[no].get("finish") or 0):
                    reason = (f"finish mismatch horse {no}: stored "
                              f"{f.get('finish')} official {off[no].get('finish')}")
                    break
        if reason:
            skipped.append({"race_id": rid, "reason": reason})
            continue
        new_detail = copy.deepcopy(detail)
        n_changed = 0
        margins: dict[str, str] = {}
        for f in (new_detail.get("result") or {}).get("finishers") or []:
            no = int(f.get("horseNumber") or 0)
            if int(f.get("finish") or 0) < 2:
                continue
            text = str((off.get(no) or {}).get("marginText") or "")
            margins[str(no)] = text
            if text and not str(f.get("marginText") or ""):
                f["marginText"] = text
                n_changed += 1
        if n_changed:
            repaired.append(rid)
            official_margin[rid] = margins
            changed_fields[rid] = n_changed
            changed_details.append(new_detail)
        else:
            skipped.append({"race_id": rid, "reason": "nothing to change"})

    summaries = [rows[rid] for rid in repaired if rid in rows]
    payload = {
        "summaries": summaries,
        "details": changed_details,
        "meta": {
            "source": "github-actions-jra-margin-repair-v1",
            "sync_date": bundle.get("date") or "",
            "started_race_count": len(repaired),
            "margin_target_count": len(targets),
            "margin_repaired_count": len(repaired),
            "margin_skipped_count": len(skipped),
            "margin_repair_at": int(time.time()),
        },
    }
    report = {
        "date": bundle.get("date") or "",
        "targets": targets,
        "repaired": repaired,
        "skipped": skipped,
        "official_margin": official_margin,
        "changed_fields": changed_fields,
        "aborted": aborted,
    }
    _write_json(payload_path, payload)
    _write_json(report_path, report)
    print("MARGIN_REPAIR_AUDIT",
          f"targets={len(targets)}", f"repaired={len(repaired)}",
          f"skipped={len(skipped)}", f"aborted={aborted or '-'}")
    for s in skipped:
        print("MARGIN_REPAIR_SKIP", s["race_id"], s["reason"])
    return 3 if aborted else 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="bundle-jra.json")
    p.add_argument("--payload", default="margin-repair-payload.json")
    p.add_argument("--report", default="margin-repair-report.json")
    args = p.parse_args()
    return repair(args.bundle, args.payload, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
