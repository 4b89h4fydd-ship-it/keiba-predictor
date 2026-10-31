#!/usr/bin/env python3
"""Publish rewrite-engine forecasts into production race details.

This is the sole forecast producer after the cutover. For each upcoming
race it fetches the CURRENT stored detail from the production API,
computes the rewrite engine's forecast from the detail's own facts,
replaces only the forecast-owned blocks, passes the result through
``arvexq_protect_sync.protect_detail`` (which preserves seals, career
archives and revision chains, and only accepts forecast replacement
from a write carrying this lane's marker), and posts it back through
POST /api/sync. Read-back verification requires the stored unified
receipt hash to equal the generated one.

Facts (entries, careers, results, odds) are never authored here; the
engine configuration is the frozen lane configuration shared with the
pre-off sealing lane (rewrite/analysis/lane_config.py), so what the app
displays is exactly what the sealed forward record later grades.

Usage:
  SYNC_TOKEN=... python3 scripts/arvexq_rewrite_publish.py [--date YYYY-MM-DD ...] [--dry-run]

Without --date, publishes today and tomorrow (JST). --dry-run builds
and self-verifies every product locally without posting.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.analysis.lane_config import LANE_BETA, LANE_WEIGHTS  # noqa: E402
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
from rewrite.data.normalize import normalize_race  # noqa: E402
from rewrite.output.api_shape import MODEL_VERSION, race_payload  # noqa: E402

JST = ZoneInfo("Asia/Tokyo")
API_BASE = os.environ.get("ARVEXQ_API_BASE",
                          "https://kraiz-api.4b89h4fydd.workers.dev")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
COMBO_KINDS = {"wide": "ワイド", "quinella": "馬連", "exacta": "馬単",
               "trio": "3連複", "trifecta": "3連単"}
SCRATCH_STATUSES = {"出走取消", "競走除外", "欠場"}


def _get(path: str) -> dict:
    last: Exception | None = None
    for _attempt in range(3):
        req = urllib.request.Request(API_BASE + path,
                                     headers={"User-Agent": UA,
                                              "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (TimeoutError, ConnectionError, OSError) as exc:
            last = exc
    raise last  # type: ignore[misc]


def _post_sync(detail: dict, token: str) -> dict:
    body = json.dumps(
        {"summaries": [], "details": [detail],
         "meta": {"source": "arvexq-rewrite-publish-v1", "race_count": 1}},
        ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + "/api/sync", data=body, method="POST",
        headers={"User-Agent": UA, "Content-Type": "application/json",
                 "x-sync-token": token})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _load_protect():
    spec = importlib.util.spec_from_file_location(
        "arvexq_protect_sync", ROOT / "scripts" / "arvexq_protect_sync.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.protect_detail


def _is_inactive(horse: dict) -> bool:
    if horse.get("scratched") or horse.get("withdrawn"):
        return True
    status = str(horse.get("status") or "")
    return any(s in status for s in SCRATCH_STATUSES)


def _post_at(detail: dict) -> datetime | None:
    raw = detail.get("scheduledStartTime") or detail.get("startTime")
    date = detail.get("date")
    if not raw or not date:
        return None
    try:
        return datetime.fromisoformat(f"{date}T{str(raw)[:5]}:00+09:00")
    except ValueError:
        return None


def _has_result(detail: dict) -> bool:
    result = detail.get("result")
    if not isinstance(result, dict):
        return False
    return bool(result.get("finishers")) or result.get("status") in (
        "finished", "確定", "結果確定")


def _canonical_receipt(product: dict) -> str:
    # Value-canonical receipt (shared with the verifier): integral floats
    # hash as ints, so the receipt survives the JS re-serialization the
    # payload undergoes on its way to and from D1. See
    # arvexq/prediction/unified_product.py canonical_receipt.
    from arvexq.prediction.unified_product import canonical_receipt
    return canonical_receipt(product)


def build_publish_detail(old_detail: dict, summary: dict, now: datetime):
    """Return (new_detail, receipt) or (None, reason) when not publishable."""
    from arvexq.ingest.full_snapshot_codec import unpack_detail
    from arvexq.prediction.unified_product import race_family

    old = unpack_detail(old_detail)
    if _has_result(old):
        return None, "already has a result"
    post = _post_at(old)
    if post is None or now >= post:
        return None, "post time reached or unknown"
    race = normalize_race(summary, old, source="production-api-readback")
    forecast = forecast_race(
        race, beta=LANE_BETA,
        weights=LANE_WEIGHTS.get(race.segment.value, {}))
    if forecast.status != "ok":
        return None, f"forecast not ok: {forecast.status}"
    pace = forecast_pace(race)
    win_odds = {
        r.number: r.win_odds.value
        for r in race.runners
        if r.win_odds.present
        and isinstance(r.win_odds.value, (int, float))
    }
    # Trifecta formation B (adopted 2026-10-31 after the
    # pre-registered primary paired judgement against legacy A at
    # 142 races). Probabilities, marks and every other ticket kind
    # are unchanged; the sealing lane keeps the legacy formation.
    tickets = generate_tickets(forecast, win_odds,
                               calibration_validated=False,
                               trifecta_formation="B")
    captured = now.isoformat(timespec="seconds")
    payload = race_payload(
        race, forecast, pace, tickets,
        provenance={"captured_at": captured, "snapshot_sha256": None})
    built = payload["detail"]
    unified = built["unifiedForecast"]
    # Production receipt semantics: roster is the detail's ACTIVE roster
    # (production verification rebuilds it from the stored horses), the
    # family comes from the production classifier, and the receipt hash
    # is the canonical product hash (not an input snapshot hash).
    unified["modelFamily"] = race_family(old)
    unified["roster"] = [
        {"horseNumber": int(h["horseNumber"]), "name": str(h.get("name") or "")}
        for h in old.get("horses") or []
        if isinstance(h, dict) and h.get("horseNumber")
        and not _is_inactive(h)]
    unified.pop("receiptKind", None)
    unified["receiptSha256"] = _canonical_receipt(unified)

    win = {r.number: round(r.p_win, 6) for r in forecast.runners}
    top3 = {r.number: round(r.p_top3, 6) for r in forecast.runners}
    marks = built["predictionMarks"]
    grouped: dict[str, list] = {}
    for t in tickets.probability_tickets:
        if t.kind in COMBO_KINDS:
            grouped.setdefault(COMBO_KINDS[t.kind], []).append(list(t.selection))
    recommended = [
        {"kind": kind, "combos": combos, "points": len(combos),
         "reason": "同一モデルの結合確率上位。期待値は券種別実オッズ不足と確率校正未検証のため表示しない"}
        for kind, combos in grouped.items()]
    minutes = int((post - now).total_seconds() // 60)
    prediction = {
        "raceId": old["id"], "date": old["date"],
        "circuit": old.get("circuit"),
        "capturedAt": captured,
        "methodologyStatus": "rewrite-engine-probability-uncalibrated",
        "actualForecasterPublishedPicks": True,
        "calibrationMethod": "none-probabilities-uncalibrated",
        "modelVersion": MODEL_VERSION,
        "predictionStatus": "ready", "productionEligible": True,
        "stages": {
            "ability": {"status": "rewrite-ability-prior-v1"},
            "pace": {"status": "past-corner-evidence-uncalibrated",
                     "text": built["forecastText"]},
            "probability": {"value": {"win": win, "top3": top3}},
            "marks": {"value": {"orderedWinCandidates":
                                [m["horseNumber"] for m in marks]}},
            "tickets": {"status": "probability-only-ev-suppressed"},
        },
        "predictionMarks": marks,
        "recommendedBets": recommended,
        "methodWeights": {}, "methodEvidence": {}, "calibrationRaces": 0,
        "forecastText": built["forecastText"],
        "humanOverrideAllowed": False,
    }
    pre_race_bet = {
        "raceId": old["id"], "fixedAt": captured, "fixedBeforePost": True,
        "fixedMinutesBeforePost": minutes,
        "decision": "推奨" if recommended else "見送り",
        "items": recommended, "modelVersion": MODEL_VERSION,
        "lockPolicy": "arvexq-rewrite-preoff-original-v1",
        "captureStatus": "captured",
    }
    new = dict(old)
    for key in ("fusionInputs", "fusionMethodPreoffReceipt",
                "predictionAudit", "frozenPredictionAudit"):
        new.pop(key, None)
    new["unifiedForecast"] = unified
    new["prediction"] = prediction
    new["predictionMarks"] = marks
    new["recommendedBets"] = recommended
    new["forecastText"] = built["forecastText"]
    new["predictionStatus"] = "ready"
    new["predictionModelVersion"] = MODEL_VERSION
    new["preRaceBet"] = pre_race_bet
    by_no = {m["horseNumber"]: m["mark"] for m in marks}
    horses = []
    for h in old.get("horses") or []:
        h = dict(h)
        h.pop("mark", None)
        h.pop("integratedEvaluation", None)
        if h.get("horseNumber") in by_no:
            h["predMark"] = by_no[h["horseNumber"]]
        else:
            h.pop("predMark", None)
        horses.append(h)
    new["horses"] = horses
    meta = dict(old.get("preparedMeta") or {})
    meta["rewritePublish"] = {
        "modelVersion": MODEL_VERSION, "publishedAt": captured,
        "receiptSha256": unified["receiptSha256"]}
    new["preparedMeta"] = meta
    return new, unified["receiptSha256"]


def publish_date(date: str, token: str | None, dry_run: bool) -> dict:
    from arvexq.ingest.full_snapshot_codec import pack_detail, unpack_detail
    from arvexq.prediction.unified_product import verified as verified_unified

    protect_detail = _load_protect()
    listing = _get(f"/api/races?date={date}")
    summaries = listing.get("races") or listing.get("summaries") or []
    counts = {"races": len(summaries), "published": 0, "skipped": 0,
              "failed": 0}
    for summary in summaries:
        race_id = summary.get("race_id") or summary.get("id")
        if not race_id or "帯広" in str(summary.get("track") or ""):
            counts["skipped"] += 1
            continue
        try:
            resp = _get("/api/race/" + urllib.parse.quote(str(race_id), safe=""))
            old_raw = resp.get("detail") or {}
            now = datetime.now(JST)
            new, receipt = build_publish_detail(old_raw, summary, now)
            if new is None:
                counts["skipped"] += 1
                print(f"SKIP {race_id}: {receipt}")
                continue
            check = verified_unified(dict(unpack_detail(old_raw),
                                          unifiedForecast=new["unifiedForecast"]))
            if check is None:
                counts["failed"] += 1
                print(f"FAIL {race_id}: product does not self-verify")
                continue
            if dry_run:
                counts["published"] += 1
                print(f"DRY  {race_id}: receipt {receipt[:12]}… verified")
                continue
            final = protect_detail(old_raw, new)
            if isinstance(old_raw, dict) and "arvexqFullPayload" in old_raw:
                final = pack_detail(final)
            result = _post_sync(final, token)
            if not result.get("ok"):
                counts["failed"] += 1
                print(f"FAIL {race_id}: sync rejected: {result}")
                continue
            back = _get("/api/race/" + urllib.parse.quote(str(race_id), safe=""))
            stored = (back.get("detail") or {}).get("unifiedForecast") or {}
            if stored.get("receiptSha256") != receipt:
                counts["failed"] += 1
                print(f"FAIL {race_id}: read-back receipt mismatch")
                continue
            counts["published"] += 1
            print(f"OK   {race_id}: receipt {receipt[:12]}… live")
        except Exception as exc:  # per-race isolation; report and continue
            counts["failed"] += 1
            print(f"FAIL {race_id}: {type(exc).__name__}: {exc}")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dates = args.date
    if not dates:
        today = datetime.now(JST).date()
        dates = [today.isoformat(), (today + timedelta(days=1)).isoformat()]
    token = os.environ.get("SYNC_TOKEN")
    if not args.dry_run and not token:
        print("SYNC_TOKEN is required for publishing", file=sys.stderr)
        return 2
    total_failed = 0
    for date in dates:
        counts = publish_date(date, token, args.dry_run)
        total_failed += counts["failed"]
        print(f"{date}: {counts}")
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
