#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-back proof for the JRA environment history repair.

For every race the repair claims to have changed, fetch the CURRENT
detail from the production API and prove:
  1. env_match - weather / condition now equal the official values
     the repair recorded;
  2. result_intact - the result block is identical to the pre-repair
     bundle detail (finishers, payouts, status untouched);
  3. forecasts_intact - the forecast-bearing blocks (unifiedForecast,
     predictionMarks, prediction, recommendedBets) are identical;
  4. listing_match - the day listing's summary row for the race now
     carries the same weather / condition.
Differing top-level keys outside {weather, condition,
environmentMeta, updatedAt} are reported as observed_diffs. Exits
non-zero if any race fails checks 1-4.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
      "Mobile/15E148 Safari/604.1")
FORECAST_KEYS = ("unifiedForecast", "predictionMarks", "prediction",
                 "recommendedBets")
ALLOWED_DIFFS = {"weather", "condition", "environmentMeta", "updatedAt"}


def _fetch_json(url: str) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


def _fetch_detail(api_base: str, race_id: str) -> dict[str, Any] | None:
    url = (f"{api_base}/api/race/{urllib.parse.quote(race_id, safe='')}"
           f"?t={int(time.time() * 1000)}")
    body = _fetch_json(url)
    return body.get("detail") or body


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="bundle-jra.json")
    p.add_argument("--report", default="env-repair-report.json")
    p.add_argument("--api-base", required=True)
    p.add_argument("--out", default="env-audit-report.json")
    args = p.parse_args()

    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    before = {str(d.get("id") or ""): d
              for d in (bundle.get("details") or []) if isinstance(d, dict)}
    official = report.get("official_env") or {}
    date = report.get("date") or ""
    listing: dict[str, Any] = {}
    if date:
        try:
            day = _fetch_json(
                f"{args.api_base}/api/races?date={date}"
                f"&t={int(time.time() * 1000)}")
            for r in day.get("races") or day.get("items") or []:
                listing[str(r.get("race_id") or r.get("id") or "")] = r
        except Exception as exc:
            print("listing fetch failed:", exc)
    verdicts: dict[str, Any] = {}
    failures = 0
    for rid in report.get("repaired") or []:
        entry: dict[str, Any] = {"env_match": False,
                                 "result_intact": False,
                                 "forecasts_intact": False,
                                 "listing_match": False,
                                 "observed_diffs": []}
        try:
            now = _fetch_detail(args.api_base, rid)
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
            verdicts[rid] = entry
            failures += 1
            continue
        exp = official.get(rid) or {}
        entry["env_match"] = (
            now.get("weather") == exp.get("weather")
            and now.get("condition") == exp.get("condition"))
        old = before.get(rid) or {}
        entry["result_intact"] = old.get("result") == now.get("result")
        entry["forecasts_intact"] = all(
            old.get(k) == now.get(k) for k in FORECAST_KEYS)
        row = listing.get(rid) or {}
        entry["listing_match"] = (
            row.get("weather") == exp.get("weather")
            and row.get("condition") == exp.get("condition"))
        checked = {"result", *FORECAST_KEYS} | ALLOWED_DIFFS
        entry["observed_diffs"] = sorted(
            k for k in set(old) | set(now)
            if k not in checked and old.get(k) != now.get(k))
        if not (entry["env_match"] and entry["result_intact"]
                and entry["forecasts_intact"] and entry["listing_match"]):
            failures += 1
        verdicts[rid] = entry
    out = {"date": date, "checked": len(verdicts), "failures": failures,
           "verdicts": verdicts}
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checked": out["checked"], "failures": failures}))
    for rid, v in verdicts.items():
        if not (v["env_match"] and v["result_intact"]
                and v["forecasts_intact"] and v["listing_match"]):
            print("VERIFY_FAIL", rid, json.dumps(v, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
