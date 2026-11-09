#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill ONLY weather / trackCondition for stored JRA races whose
stored environment is still the  placeholder.

Why this exists: the race-list builder hardcoded weather/condition to
 for JRA races saved before the 2026-11-09 environment
backfill lane landed (main b7d6a093), and the steady lane only drains
today/yesterday, so the 2026-10-24..11-07 JRA races kept the
placeholder permanently (69 races by the 2026-11-10 listing census).
The official JRA result page publishes  /  per race,
so this lane re-parses the OFFICIAL result page for each affected
race and copies only the environment fields (detail weather /
condition, the summary row's weather / condition, and the
environmentMeta stamp the steady lane writes). Results, payouts,
cards and forecasts are never touched. A race whose official parse
disagrees with the stored identity (date / track / race number) is
skipped, not forced.

Discipline: sequential official fetches with a pause between races;
an HTTP 403/429 from jra.go.jp aborts the whole run (exit 3) instead
of pushing through. Modelled on scripts/arvexq_margin_repair.py.
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
UNKNOWN = (None, "", "不明")


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
    past-results menu, identical to arvexq_margin_repair's (the
    production helper's meeting regex predates the 00 token variant).
    Tokens are always taken from official pages, never assembled."""

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


def _is_target(detail: dict[str, Any]) -> bool:
    return (detail.get("weather") in UNKNOWN
            or detail.get("condition") in UNKNOWN)


def _is_compact_tombstone(detail: dict[str, Any]) -> bool:
    """Archive-less compact tombstone (the 2026-11-01 D1 compact
    destroyed the forecast blocks; see the 2026-11-09 tombstone
    repair). protect_sync fail-closes any write to these that is not
    result/payout-only -- its registered exception covers
    {result, resultCname, payouts} only -- so an environment write
    through the sync route is refused by design. These races are
    reported as skipped with that reason instead of aborting the
    whole day's batches."""
    return (detail.get("predictionModelVersion")
            == "arvexq-prediction-removed"
            and not detail.get("unifiedForecast")
            and not detail.get("preoffStage64Archive")
            and not detail.get("horses"))


def _header_env_fallback(result_cname: str,
                         detail: dict[str, Any]) -> dict[str, Any]:
    """Fallback for races whose structured parse returns no weather
    or condition even though the official result page header prints
    them (observed on jra-2026-10-24-東京-10: the page header reads
     ダート , the production parse extracted neither).
    Reads the SAME official result page's header text only; the
    going is taken for the race's own surface."""
    try:
        html = _request(ACCESS_S, result_cname, 86400)
    except Exception:
        return {}
    import unicodedata
    text = re.sub(r"<[^>]+>", " ", html)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    out: dict[str, Any] = {}
    wm = re.search(r"天候\s*(晴|曇|雨|小雨|雪|小雪)", text)
    if wm:
        out["weather"] = wm.group(1)
        tail = text[wm.end():wm.end() + 40]
        gm = re.search(r"(芝|ダート)\s*(良|稍重|重|不良)", tail)
        if gm and (not detail.get("surface")
                   or gm.group(1) == str(detail.get("surface"))):
            out["condition"] = gm.group(2)
    return out


def _official_env(detail: dict[str, Any],
                  discovery: _TokenDiscovery) -> dict[str, Any] | None:
    """Official JRA environment for this race from its result page.
    Token order: the stored result token (identity-checked), then the
    past-results menu traversal for the race's date/track."""
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
    for key in ("date", "track", "raceNumber"):
        mine, theirs = detail.get(key), parsed.get(key)
        if mine not in (None, "", 0) and theirs not in (None, "", 0) \
                and str(mine) != str(theirs):
            return None
    env = {"weather": parsed.get("weather"),
           "condition": parsed.get("condition")}
    if env["weather"] in UNKNOWN or env["condition"] in UNKNOWN:
        fb = _header_env_fallback(result_cname, detail)
        if env["weather"] in UNKNOWN and fb.get("weather") not in UNKNOWN:
            env["weather"] = fb["weather"]
        if env["condition"] in UNKNOWN \
                and fb.get("condition") not in UNKNOWN:
            env["condition"] = fb["condition"]
    return env


def repair(bundle_path: str, payload_path: str, report_path: str) -> int:
    bundle = _read_json(bundle_path)
    details = [d for d in (bundle.get("details") or [])
               if isinstance(d, dict) and str(d.get("id") or "").startswith("jra-")]
    rows = {str(r.get("id") or ""): r for r in (bundle.get("races") or [])
            if isinstance(r, dict)}
    sleep_sec = float(os.getenv("ENV_REPAIR_SLEEP_SEC", "2"))
    discovery = _TokenDiscovery(sleep_sec)
    targets: list[str] = []
    repaired: list[str] = []
    skipped: list[dict[str, str]] = []
    official_env: dict[str, dict[str, Any]] = {}
    changed_fields: dict[str, int] = {}
    changed_details: list[dict[str, Any]] = []
    changed_summaries: list[dict[str, Any]] = []
    aborted = ""

    for detail in details:
        rid = str(detail.get("id") or "")
        row = rows.get(rid) or {}
        summary_unknown = (row.get("weather") in UNKNOWN
                           or row.get("condition") in UNKNOWN)
        if not _is_target(detail) and not summary_unknown:
            continue
        if _is_compact_tombstone(detail):
            skipped.append({
                "race_id": rid,
                "reason": "compact tombstone: protect fail-closes "
                          "non-result writes by design (env fields are "
                          "outside the result-only exception)"})
            continue
        targets.append(rid)
        try:
            official = _official_env(detail, discovery)
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
        weather = official.get("weather")
        condition = official.get("condition")
        if weather not in UNKNOWN:
            weather = app._env_clean_weather(weather)
        if condition not in UNKNOWN:
            condition = app._env_clean_condition(condition)
        new_detail = copy.deepcopy(detail)
        n_changed = 0
        if new_detail.get("weather") in UNKNOWN and weather not in UNKNOWN:
            new_detail["weather"] = weather
            n_changed += 1
        if new_detail.get("condition") in UNKNOWN and condition not in UNKNOWN:
            new_detail["condition"] = condition
            n_changed += 1
        new_row = None
        summary_changed = False
        row = rows.get(rid)
        if row is not None:
            new_row = copy.deepcopy(row)
            if new_row.get("weather") in UNKNOWN \
                    and new_detail.get("weather") not in UNKNOWN:
                new_row["weather"] = new_detail["weather"]
                summary_changed = True
            if new_row.get("condition") in UNKNOWN \
                    and new_detail.get("condition") not in UNKNOWN:
                new_row["condition"] = new_detail["condition"]
                summary_changed = True
        if not n_changed and not summary_changed:
            skipped.append({"race_id": rid,
                            "reason": "official environment also unknown"})
            continue
        if n_changed:
            new_detail["environmentMeta"] = {
                "source": "JRA公式結果",
                "updatedAt": int(time.time() * 1000),
                "raceId": rid,
            }
        repaired.append(rid)
        official_env[rid] = {"weather": new_detail.get("weather"),
                             "condition": new_detail.get("condition")}
        changed_fields[rid] = n_changed
        changed_details.append(new_detail)
        if new_row is not None:
            changed_summaries.append(new_row)

    payload = {
        "summaries": changed_summaries,
        "details": changed_details,
        "meta": {
            "source": "github-actions-jra-env-history-repair-v1",
            "sync_date": bundle.get("date") or "",
            "started_race_count": len(repaired),
            "env_target_count": len(targets),
            "env_repaired_count": len(repaired),
            "env_skipped_count": len(skipped),
            "env_repair_at": int(time.time()),
        },
    }
    report = {
        "date": bundle.get("date") or "",
        "targets": targets,
        "repaired": repaired,
        "skipped": skipped,
        "official_env": official_env,
        "changed_fields": changed_fields,
        "aborted": aborted,
    }
    _write_json(payload_path, payload)
    _write_json(report_path, report)
    print("ENV_REPAIR_AUDIT",
          f"targets={len(targets)}", f"repaired={len(repaired)}",
          f"skipped={len(skipped)}", f"aborted={aborted or '-'}")
    for s in skipped:
        print("ENV_REPAIR_SKIP", s["race_id"], s["reason"])
    return 3 if aborted else 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="bundle-jra.json")
    p.add_argument("--payload", default="env-repair-payload.json")
    p.add_argument("--report", default="env-repair-report.json")
    args = p.parse_args()
    return repair(args.bundle, args.payload, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
