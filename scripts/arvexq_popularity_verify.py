#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-back proof for the JRA popularity history repair.

For every race the repair claims to have changed, fetch the CURRENT
detail from the production API and prove two things:
  1. every finisher's popularity now equals the official value the
     repair recorded;
  2. with popularity masked out, the current detail is identical to
     the pre-repair bundle detail - i.e. the write changed nothing
     else (payouts, finishers, cards, forecasts all untouched).
Exits non-zero if any race fails either check.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
      "Mobile/15E148 Safari/604.1")


def _fetch(api_base: str, race_id: str) -> dict[str, Any] | None:
    req = urllib.request.Request(
        f"{api_base}/api/race/{race_id}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body.get("detail") or body


def _masked(detail: dict[str, Any]) -> dict[str, Any]:
    d = copy.deepcopy(detail)
    for f in ((d.get("result") or {}).get("finishers") or []):
        if isinstance(f, dict):
            f["popularity"] = "<masked>"
    return d


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="bundle-jra.json")
    p.add_argument("--report", default="popularity-repair-report.json")
    p.add_argument("--api-base", required=True)
    p.add_argument("--out", default="popularity-audit-report.json")
    args = p.parse_args()

    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    before = {str(d.get("id") or ""): d
              for d in (bundle.get("details") or []) if isinstance(d, dict)}
    official = report.get("official_popularity") or {}
    verdicts: dict[str, Any] = {}
    failures = 0
    for rid in report.get("repaired") or []:
        entry: dict[str, Any] = {"popularity_match": False,
                                 "only_popularity_changed": False}
        try:
            now = _fetch(args.api_base, rid)
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
            verdicts[rid] = entry
            failures += 1
            continue
        pops = {str(int(f.get("horseNumber") or 0)): f.get("popularity")
                for f in ((now.get("result") or {}).get("finishers") or [])
                if int(f.get("horseNumber") or 0) > 0}
        expected = official.get(rid) or {}
        entry["popularity_match"] = all(
            pops.get(no) == pop for no, pop in expected.items())
        old = before.get(rid)
        entry["only_popularity_changed"] = bool(
            old is not None and _masked(old) == _masked(now))
        if not (entry["popularity_match"] and entry["only_popularity_changed"]):
            failures += 1
        verdicts[rid] = entry
    out = {"date": report.get("date") or "",
           "checked": len(verdicts), "failures": failures,
           "verdicts": verdicts}
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checked": out["checked"], "failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
