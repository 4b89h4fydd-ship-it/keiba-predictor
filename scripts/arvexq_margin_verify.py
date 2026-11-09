#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-back proof for the JRA margin history repair.

For every race the repair claims to have changed, fetch the CURRENT
detail from the production API and prove:
  1. margin_match - every placed finisher's (finish >= 2) marginText
     now equals the official value the repair recorded;
  2. result_intact - the result block with marginText masked out is
     identical to the pre-repair bundle detail (finishers' other
     fields, payouts, status untouched);
  3. forecasts_intact - the forecast-bearing blocks (unifiedForecast,
     predictionMarks, prediction, recommendedBets) are identical.
Any other differing top-level key is reported as observed_diffs for
the record. Exits non-zero if any race fails checks 1-3.
"""
from __future__ import annotations

import argparse
import copy
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


def _fetch(api_base: str, race_id: str) -> dict[str, Any] | None:
    # Cache-busting query, mirroring the bundle fetcher: the API can
    # serve a cached projection otherwise. Bounded retries, as in the
    # bundle fetcher: large details occasionally truncate in transit.
    url = (f"{api_base}/api/race/{urllib.parse.quote(race_id, safe='')}"
           f"?t={int(time.time() * 1000)}")
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as res:
                body = json.loads(res.read().decode("utf-8"))
            return body.get("detail") or body
        except Exception as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


def _masked_result(detail: dict[str, Any]) -> Any:
    res = copy.deepcopy((detail or {}).get("result"))
    if isinstance(res, dict):
        for f in res.get("finishers") or []:
            if isinstance(f, dict):
                f["marginText"] = "<masked>"
    return res


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="bundle-jra.json")
    p.add_argument("--report", default="margin-repair-report.json")
    p.add_argument("--api-base", required=True)
    p.add_argument("--out", default="margin-audit-report.json")
    args = p.parse_args()

    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    before = {str(d.get("id") or ""): d
              for d in (bundle.get("details") or []) if isinstance(d, dict)}
    official = report.get("official_margin") or {}
    verdicts: dict[str, Any] = {}
    failures = 0
    for rid in report.get("repaired") or []:
        entry: dict[str, Any] = {"margin_match": False,
                                 "result_intact": False,
                                 "forecasts_intact": False,
                                 "observed_diffs": []}
        try:
            now = _fetch(args.api_base, rid)
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
            verdicts[rid] = entry
            failures += 1
            continue
        fins = (now.get("result") or {}).get("finishers") or []
        texts = {str(int(f.get("horseNumber") or 0)):
                 str(f.get("marginText") or "")
                 for f in fins if int(f.get("horseNumber") or 0) > 0}
        expected = official.get(rid) or {}
        entry["margin_match"] = (
            all(texts.get(no) == text for no, text in expected.items())
            and all(str(f.get("marginText") or "") for f in fins
                    if int(f.get("finish") or 0) >= 2
                    and expected.get(str(int(f.get("horseNumber") or 0)))))
        old = before.get(rid) or {}
        entry["result_intact"] = _masked_result(old) == _masked_result(now)
        entry["forecasts_intact"] = all(
            old.get(k) == now.get(k) for k in FORECAST_KEYS)
        checked = {"result", *FORECAST_KEYS}
        entry["observed_diffs"] = sorted(
            k for k in set(old) | set(now)
            if k not in checked and old.get(k) != now.get(k))
        if not (entry["margin_match"] and entry["result_intact"]
                and entry["forecasts_intact"]):
            failures += 1
        verdicts[rid] = entry
    out = {"date": report.get("date") or "",
           "checked": len(verdicts), "failures": failures,
           "verdicts": verdicts}
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checked": out["checked"], "failures": failures}))
    for rid, v in verdicts.items():
        if not (v["margin_match"] and v["result_intact"]
                and v["forecasts_intact"]):
            print("VERIFY_FAIL", rid, json.dumps(v, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
