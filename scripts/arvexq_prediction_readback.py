#!/usr/bin/env python3
"""Read-only production verification for the existing forecast contract.

The API must return the lossless pre-off detail for a compressed D1 row.  A
thin ``disabled`` index is not a successful forecast readback when its full
snapshot contains a valid unified receipt.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import Counter


def get(base: str, path: str) -> dict:
    request = urllib.request.Request(base.rstrip("/") + path,
                                     headers={"User-Agent": "ARVEXQ-preoff-readback/1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise RuntimeError("API response is not an object: " + path)
    return value


def verify_detail(detail: dict) -> tuple[str, str]:
    if detail.get("arvexqFullPayload"):
        raise AssertionError("thin compressed index returned instead of restored detail")
    horses = [h for h in detail.get("horses") or [] if isinstance(h, dict)]
    source = detail.get("unifiedForecast")
    if isinstance(source, dict):
        if source.get("raceId") != detail.get("id") or source.get("raceDate") != detail.get("date"):
            raise AssertionError("unified receipt race identity mismatch")
        if source.get("researchOnly") is not True or source.get("probabilitiesCalibrated") is not False:
            raise AssertionError("unified receipt provenance gate changed")
        if len(source.get("roster") or []) != len(horses):
            raise AssertionError("unified receipt roster mismatch")
        marks = source.get("marks") or []
        if sum(row.get("markSymbol") == "◎" for row in marks) != 1:
            raise AssertionError("unified receipt must contain exactly one ◎")
        if len(source.get("paceStages") or []) != 4:
            raise AssertionError("unified receipt must contain four pace stages")
        return "unified", str(detail.get("circuit") or "unknown")
    prediction = detail.get("prediction")
    if isinstance(prediction, dict) and prediction.get("predictionStatus") == "ready":
        marks = detail.get("predictionMarks") or []
        if not marks:
            raise AssertionError("ready prediction has no marks")
        return "empirical", str(detail.get("circuit") or "unknown")
    return "unavailable", str(detail.get("circuit") or "unknown")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--allow-unavailable", action="store_true")
    args = parser.parse_args(argv)
    day = get(args.api_base, "/api/day?date=" + urllib.parse.quote(args.date) + "&details=1")
    rows = [row for row in day.get("races") or []
            if isinstance(row, dict) and row.get("id")
            and str(row.get("track") or "") not in {"帯広", "帯広ば"}
            and "-帯広-" not in str(row.get("id"))
            and "-帯広ば-" not in str(row.get("id"))]
    counts = Counter()
    failures = []
    for row in rows:
        try:
            response = get(args.api_base, "/api/race/" + urllib.parse.quote(str(row["id"]), safe=""))
            kind, circuit = verify_detail(response.get("detail") or response)
            counts[(circuit, kind)] += 1
        except Exception as exc:
            failures.append({"raceId": row["id"], "error": str(exc)})
    report = {"date": args.date, "races": len(rows),
              "counts": {"|".join(k): v for k, v in sorted(counts.items())},
              "failures": failures, "successRate": (len(rows) - len(failures)) / len(rows) if rows else 0}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if failures and not args.allow_unavailable:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
