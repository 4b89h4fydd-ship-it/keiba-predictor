#!/usr/bin/env python3
"""One-off residual repair (2026-11-10 sweep): entry bodyweight
correction + dataCoreHealth refresh for already-finished races.

Reads a request JSON (arvexq/residual_repair/requests.json):
  {"requestId": str,
   "jobs": [{"date": "YYYY-MM-DD",
             "races": [{"id": race_id,
                        "force": bool (optional; sync even if the
                               recomputed health is unchanged),
                        "bodyweightFixes": {"<horseNumber>":
                            {"from": <stored>, "to": <official>,
                             "changeFrom": <stored>, "changeTo": <official>}}}]}]}

For each date the pristine stored bundle is fetched with
arvexq_fetch_d1_bundle.py, the listed races are patched
(bodyweight cells and/or a dataCoreHealth recomputation via
app._data_core_health on the stored form), every patch is
passed through protect_sync.protect_detail (any raise or any
protect-side modification aborts the whole run before any
write), and the result is synced through the ordinary
arvexq_sync_batches.py path.  Compact-tombstone stubs and
records without a horse list are skipped and reported --
their health cannot be refreshed without a full republish.

Verification re-reads every written race from the public API
and compares the patched cells and the full health block.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API_BASE = "https://kraiz-api.4b89h4fydd.workers.dev"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
      "Mobile/15E148 Safari/604.1")


def log(msg: str) -> None:
    print(f"[residual-repair] {msg}", flush=True)


def get_json(url: str, retries: int = 4) -> dict:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retry then report
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


def fetch_bundle(date: str, work: Path) -> dict:
    out = work / f"bundle-{date}.json"
    cmd = [sys.executable, str(ROOT / "scripts/arvexq_fetch_d1_bundle.py"),
           "--api-base", API_BASE, "--date", date, "--out", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"bundle fetch failed for {date}: "
                           f"{proc.stdout[-500:]} {proc.stderr[-500:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def health_diff(a: dict, b: dict) -> list[str]:
    fields = ("card", "history", "odds", "body_weight", "environment",
              "result", "payouts", "analysis")
    diffs = []
    for key in fields:
        x, y = (a or {}).get(key) or {}, (b or {}).get(key) or {}
        for sub in ("status", "completeness", "note"):
            if x.get(sub) != y.get(sub):
                diffs.append(f"{key}.{sub}: {x.get(sub)!r} -> {y.get(sub)!r}")
    return diffs


def main() -> int:
    request_path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        ROOT / "arvexq/residual_repair/requests.json"
    work = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        ROOT / "arvexq/residual_repair/work"
    work.mkdir(parents=True, exist_ok=True)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    log(f"request {request.get('requestId')}")

    import app as app_module  # noqa: E402 - heavy import after arg parse
    from scripts import arvexq_protect_sync as protect  # noqa: E402

    report = {"requestId": request.get("requestId"), "races": {}}
    sync_details: list[dict] = []
    sync_summaries: list[dict] = []
    intended: dict[str, dict] = {}

    for job in request.get("jobs") or []:
        date = job["date"]
        bundle = fetch_bundle(date, work)
        details = {d.get("id"): d for d in bundle.get("details") or []}
        summaries = {s.get("id"): s for s in bundle.get("races") or []}
        for spec in job.get("races") or []:
            rid = spec["id"]
            old = details.get(rid)
            entry = {"date": date}
            report["races"][rid] = entry
            if old is None:
                entry["status"] = "missing-in-bundle"
                continue
            if protect._compact_tombstone_stub(old):
                entry["status"] = "skipped-tombstone-stub"
                continue
            if not (old.get("horses") or []):
                entry["status"] = "skipped-no-horses"
                continue
            new = copy.deepcopy(old)
            for num, fix in (spec.get("bodyweightFixes") or {}).items():
                cell = next((h for h in new["horses"]
                             if int(h.get("horseNumber") or 0) == int(num)),
                            None)
                if cell is None:
                    raise RuntimeError(f"{rid}: horse {num} not found")
                if cell.get("bodyWeight") != fix["from"]:
                    raise RuntimeError(
                        f"{rid} #{num}: stored bodyWeight "
                        f"{cell.get('bodyWeight')!r} != expected "
                        f"{fix['from']!r}; aborting")
                cell["bodyWeight"] = fix["to"]
                cell["bodyWeightChange"] = fix["changeTo"]
                entry.setdefault("bodyweight", []).append(
                    {"horseNumber": int(num), "from": fix["from"],
                     "to": fix["to"], "changeTo": fix["changeTo"]})
            new["dataCoreHealth"] = app_module._data_core_health(new)
            new["dataCoreVersion"] = app_module.ARVEXQ_DATA_CORE_VERSION
            new["dataCoreUpdatedAt"] = int(time.time())
            entry["healthDiff"] = health_diff(old.get("dataCoreHealth"),
                                              new["dataCoreHealth"])
            guarded = protect.protect_detail(old, new)
            if guarded != new:
                raise RuntimeError(
                    f"{rid}: protect_detail modified the patch; aborting")
            if new == old and not spec.get("force"):
                entry["status"] = "unchanged"
                continue
            entry["status"] = "to-sync"
            sync_details.append(new)
            if rid in summaries:
                sync_summaries.append(summaries[rid])
            intended[rid] = {"health": new["dataCoreHealth"],
                             "bodyweight": entry.get("bodyweight") or []}

    if not sync_details:
        log("nothing to sync")
        (work / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1),
            encoding="utf-8")
        return 0

    sync_input = {"summaries": sync_summaries, "details": sync_details,
                  "meta": {"source": "github-actions-residual-repair-20261110",
                           "requestId": request.get("requestId")}}
    sync_path = work / "sync-input.json"
    sync_path.write_text(json.dumps(sync_input, ensure_ascii=False),
                         encoding="utf-8")
    out_dir = work / "sync-out"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/arvexq_sync_batches.py"),
         "--input", str(sync_path), "--out-dir", str(out_dir)],
        capture_output=True, text=True)
    log(proc.stdout[-2000:])
    if proc.returncode != 0:
        raise RuntimeError(f"sync failed: {proc.stderr[-1000:]}")

    failures = []
    for rid, want in intended.items():
        detail = get_json(f"{API_BASE}/api/race/{rid}")["detail"]
        got_health = detail.get("dataCoreHealth") or {}
        for key, want_field in (want["health"] or {}).items():
            got_field = got_health.get(key) or {}
            for sub in ("status", "completeness", "note"):
                if got_field.get(sub) != want_field.get(sub):
                    failures.append(
                        f"{rid} health {key}.{sub}: got "
                        f"{got_field.get(sub)!r} want {want_field.get(sub)!r}")
        for fix in want["bodyweight"]:
            cell = next((h for h in detail.get("horses") or []
                         if int(h.get("horseNumber") or 0)
                         == fix["horseNumber"]), None)
            if not cell or cell.get("bodyWeight") != fix["to"] \
                    or cell.get("bodyWeightChange") != fix["changeTo"]:
                failures.append(
                    f"{rid} #{fix['horseNumber']} bodyweight read-back: "
                    f"{(cell or {}).get('bodyWeight')!r}/"
                    f"{(cell or {}).get('bodyWeightChange')!r} want "
                    f"{fix['to']!r}/{fix['changeTo']!r}")
        report["races"][rid]["status"] = "synced-verified" \
            if not any(f.startswith(rid) for f in failures) else "verify-failed"
    report["failures"] = failures
    (work / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if failures:
        log("VERIFY FAILURES: " + " | ".join(failures))
        return 1
    log(f"done: {len(intended)} races synced and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
