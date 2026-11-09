#!/usr/bin/env python3
"""Diagnostic probe for the residual-repair lane: runs each risky
step in isolation and records the outcome, never dying silently."""
import json
import sys
import traceback
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "arvexq/residual_repair/probe-result.json"
results = {}


def probe(name, fn):
    try:
        results[name] = {"ok": True, "value": fn()}
    except Exception:  # noqa: BLE001
        results[name] = {"ok": False, "error": traceback.format_exc()[-1500:]}
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(name, results[name]["ok"], flush=True)


def fetch(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, len(resp.read())


probe("import_app", lambda: __import__("app").ARVEXQ_DATA_CORE_VERSION)
probe("import_protect",
      lambda: hasattr(__import__("scripts.arvexq_protect_sync",
                                 fromlist=["protect_detail"]),
                      "protect_detail"))
probe("fetch_race_safari_ua", lambda: fetch(
    "https://kraiz-api.4b89h4fydd.workers.dev/api/race/"
    "nar-2026-11-09-%E4%BD%90%E8%B3%80-04",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"))
probe("fetch_race_hydrator_ua", lambda: fetch(
    "https://kraiz-api.4b89h4fydd.workers.dev/api/race/"
    "nar-2026-11-09-%E4%BD%90%E8%B3%80-04", "ARVEXQ-D1-Hydrator/1"))
probe("fetch_day_safari_ua", lambda: fetch(
    "https://kraiz-api.4b89h4fydd.workers.dev/api/day?date=2026-11-09"
    "&details=0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"))
print(json.dumps(results, ensure_ascii=False)[:2000])
