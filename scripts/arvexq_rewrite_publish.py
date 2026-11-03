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

Forecast freeze (adopted 2026-11-01 after the intraday marks-drift
incident, see goals/arvexq/hidden_files/
marks-drift-investigation-20261101.md): once a race has been published
ready by this lane, later cycles never recompute or overwrite its
forecast — late-arriving input backfill must not move a forecast that
is already on sale. The exceptions are a roster change (a scratch
or an added runner), which re-issues that race alone and stamps the
revision into preparedMeta.rewritePublish.revision, and a lane
upgrade (2026-11-02): a forecast frozen on the v1 fallback only
because the v8 extras had not landed yet is re-issued on the top
lane once the extras exist, also stamped as a revision. A third
exception of the same kind is the blend upgrade (2026-11-04): a
forecast frozen on the v9b lane WITHOUT its market blend, only
because win odds were incomplete at first publication, is
re-issued once — stamped kind "blend-upgrade" — when the current
payload carries win odds for every active runner and the post is
still at least 60 minutes away; once blended it is final, and
later odds movement never re-triggers it. A fourth exception of
the same kind is the place-EV upgrade (2026-11-04): a forecast
frozen on the v9b lane WITHOUT placeExpectedValues, only because
the upstream sync did not yet carry place （複勝） odds, is
re-issued once — stamped kind "place-ev-upgrade" — when the
current payload carries an observed place range for every active
runner and the post is still at least 60 minutes away; the
re-issue is surgical (stored probabilities, marks and tickets are
kept; only the place side and the combined-gate 注 overlay are
added), and a race already carrying placeExpectedValues is final. The v9b
adoption (2026-11-03) adds one dated branch of the same kind: a
forecast frozen on the v8 lane for a race dated 2026-11-04 is
re-issued on the v9b lane (revision reason
lane-upgrade-v9b-adoption; user instruction: no v8 left standing
on 2026-11-04). Publications stamped under the previous model
version stay frozen across the version bump. Frozen state
is recognised from the stored detail itself (the lane marker plus
the receipt roster recorded in the unified forecast); if that state
cannot be read consistently the cycle fails closed and does not
overwrite. Symmetrically, a first publication of a v8-eligible race
is DEFERRED while its extras are still expected (they land with the
nightly shadow seal at ~21:40, after the evening first publish), so
the bad first publish cannot happen; the deferral has a hard
deadline of 06:00 JST on race day, after which the race publishes
on the v1 fallback as before — a v1 forecast is better than none.

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
from rewrite.analysis.shadow_v8 import WEIGHTS as V8_WEIGHTS  # noqa: E402
from rewrite.analysis.shadow_v8 import forecast_race_v8  # noqa: E402
from rewrite.analysis.shadow_v9 import BLEND_WEIGHT as V9B_BLEND_WEIGHT  # noqa: E402
from rewrite.analysis.shadow_v9 import TEMPERATURE as V9B_TEMPERATURE  # noqa: E402
from rewrite.analysis.shadow_v9 import postprocess_forecast  # noqa: E402
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

# v8 cutover (adopted 2026-11-01 after the first forward verdict:
# same-137 logloss v1 2.1492 vs v8 2.0145, 95%CI for the difference
# [-0.1924, -0.0718]). Races dated on/after V8_CUTOVER_DATE use the
# v8 ability layer (margin-weighted Elo + speed index v2) when the
# shadow lane's exported extras exist for the race; races in segments
# without a v8 candidate, races without extras, and any v8 forecast
# that does not come back "ok" fall back to the frozen v1 lane
# configuration above. The pre-off sealing lane is unchanged and
# keeps sealing the frozen v1 series.
#
# Ordering (2026-11-02 fix): next-day races are collected by the
# evening prefetch and first-published around 21:00, but the extras
# file is exported by the shadow-seal job at ~21:40. On 2026-11-02
# all 36 races were therefore first-published on the v1 lane and the
# freeze then locked them there under the v2 model version. Two
# guards now close that trap: first publication of a v8-eligible
# race defers while its extras are missing (hard deadline 06:00 JST
# on race day, see _v8_extras_deadline), and a frozen v1-lane
# forecast upgrades to the v8 lane once its extras exist (see
# _lane_upgrade_info). The extras file is re-read for every race
# (no per-run cache), so a file landing mid-run is picked up by the
# races that follow it in the same run.
V8_CUTOVER_DATE = "2026-11-01"
V8_EXTRAS_DIR = ROOT / "rewrite" / "data" / "v8_extras"
V8_ABILITY_MODEL_VERSION = "arvexq-v8-elo-speed2-fitted"
V8_ABILITY_STATUS = "rewrite-ability-elo-speed2-v8"

# v9b adoption (2026-11-03, user decision after the full blind
# evaluation on the graded v8 forward seals: paired logloss
# differences -0.2109 / -0.2187 at two date-split cutoffs, both
# significant; see goals/arvexq/hidden_files/
# v9-blind-eval-20261103.md and the frozen preregistration
# shadow-v9-preregistration-20261102.md). On the v8 lane the v8
# probability vector is now post-processed with EXACTLY the shadow
# lane's v9b definition (rewrite/analysis/shadow_v9.py, ported
# verbatim): temperature scaling at the frozen T = 0.6692, then a
# geometric market blend at the frozen weight w = 0.5 applied only
# when win odds exist for every runner in the probability vector;
# races without full odds get the temperature only. Marks, tickets
# and the win-EV display all derive from the post-processed
# probabilities; the EV ticket lane stays gated off
# (calibration_validated=False), only the display label changes.
# The v1 fallback path is untouched. The model version moves to
# arvexq-rewrite-v3-v9b (api_shape and unified_product together);
# the freeze keeps recognising the previous v2 stamp so v2-era
# publications stay frozen, and the lane-upgrade mechanism gains
# one adoption-day branch: a race dated V9B_ADOPTION_DATE that is
# frozen on the v8 lane is re-issued onto the v9b lane with the
# revision reason stamped below (user instruction 2026-11-03:
# no v8 left standing on 2026-11-04).
PREVIOUS_MODEL_VERSION = "arvexq-rewrite-v2-elo-speed2"
V9B_LANE = "v9b-cal-market"
V9B_ABILITY_MODEL_VERSION = "arvexq-v9b-elo-speed2-temp0.6692-blend50"
V9B_ABILITY_STATUS = "rewrite-ability-elo-speed2-v9b"
V9B_PROBABILITY_STATUS = "calibrated-market-blend-v9b"
V9B_ADOPTION_DATE = "2026-11-04"

# Blend upgrade (2026-11-04, user instruction after the adoption
# night left 24 of 59 races calibration-only): some venues post
# their win odds only on race-day morning (coverage is normally
# complete by ~09:40 JST), hours after the evening first publish
# froze those races with the temperature-only probabilities. A
# frozen v9b forecast whose blend did not apply is therefore
# re-issued ONCE when the odds have completed — see
# _blend_upgrade_info. The guard below keeps the upgrade out of
# the final hour before post, where a moving forecast would be
# unfair to anyone already holding the published one; after the
# upgrade the forecast is blended and final, and later odds
# movement never re-triggers anything.
BLEND_UPGRADE_MIN_LEAD = timedelta(minutes=60)

# Place-EV upgrade (2026-11-04, user instruction: the combined
# win + top-3 EV display and its 注 attention mark go live on
# TODAY's races, not from tomorrow): forecasts published before
# the upstream sync carried place （複勝） odds have no
# placeExpectedValues in their ticket plan. A frozen v9b forecast
# is therefore re-issued ONCE — stamped kind "place-ev-upgrade" —
# when the current payload carries an observed place range for
# every active runner and the post is still at least 60 minutes
# away. The re-issue is surgical: the stored probabilities, marks
# and tickets are kept byte-for-byte and only the place side is
# priced in (see _apply_place_ev_upgrade), so it can never drift a
# forecast on sale or undo a blend upgrade — it applies on top of
# the freshest stored forecast, after the blend upgrade in the
# same pass. A race already carrying placeExpectedValues is final.
PLACE_EV_UPGRADE_MIN_LEAD = timedelta(minutes=60)


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


def _load_v8_extras(date: str) -> dict:
    """Per-race v8 extras exported by the shadow lane for one date.

    File format (written by the rewrite tree's
    scripts/arvexq_v8_extras_export.py): {"date": ..., "modelKey":
    ..., "races": {race_id: {"segment": ..., "extras":
    {str(number): {...}}}}}. A missing or unreadable file simply
    means no v8 extras for that date; the caller falls back to v1.
    """
    try:
        payload = json.loads(
            (V8_EXTRAS_DIR / f"{date}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    races = payload.get("races") if isinstance(payload, dict) else None
    return races if isinstance(races, dict) else {}


def _v8_extras_deadline(race_date: str) -> datetime | None:
    """Hard deadline for the v8-extras deferral: 06:00 JST on race day.

    A v8-eligible race whose extras have not landed is not published
    at all until then (the extras normally arrive with the nightly
    shadow seal at ~21:40 the evening before). At/after the deadline
    the race publishes on the v1 fallback exactly as before — a v1
    forecast is better than none, and a permanently missing export
    must not silence a whole day. An unparseable date disables the
    deferral (publish as before).
    """
    try:
        day = datetime.strptime(race_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return datetime(day.year, day.month, day.day, 6, 0, tzinfo=JST)


def _lane_upgrade_info(old: dict) -> dict | None:
    """Facts for healing a frozen forecast onto the current top lane.

    Two sources, both re-issued through the normal build and stamped
    as revisions (the caller re-issues only when the rebuilt
    forecast actually used the v9b lane, so an unusable upgrade
    keeps the frozen forecast byte-stable):

    - v1-prior (the 2026-11-02 trap): the stored forecast was
      published ready on the v1 fallback only because the v8 extras
      had not landed at first publication; the race is dated
      on/after the v8 cutover and exported extras for it NOW exist.
    - v8-elo-speed2 on the v9b adoption date only (2026-11-04):
      the stored forecast was published on the v8 lane before the
      v9b production adoption completed; the user instructed that
      no race dated 2026-11-04 stays on the v8 lane, so it is
      re-issued onto the v9b lane with the adoption reason stamped
      into the revision. Any other date's v8 publication is NOT an
      upgrade source: it stays frozen.
    """
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    lane = marker.get("abilityLane")
    if lane == "v1-prior":
        reason = "lane-upgrade"
    elif lane == "v8-elo-speed2":
        reason = "lane-upgrade-v9b-adoption"
    else:
        return None
    race_date = str(old.get("date") or "")
    if race_date < V8_CUTOVER_DATE:
        return None
    if reason == "lane-upgrade-v9b-adoption" and race_date != V9B_ADOPTION_DATE:
        return None
    race_id = str(old.get("id") or "")
    if not race_id:
        return None
    entry = _load_v8_extras(race_date).get(race_id)
    raw_extras = entry.get("extras") if isinstance(entry, dict) else None
    if not (isinstance(raw_extras, dict) and raw_extras):
        return None
    return {"publishedAt": marker.get("publishedAt"),
            "previousAbilityLane": lane,
            "reason": reason}


def _blend_upgrade_info(old: dict, now: datetime) -> dict | None:
    """Facts for the one-time blend upgrade of a frozen v9b race.

    A stored forecast qualifies only when ALL of these hold:

    - it was published on the v9b lane (abilityLane v9b-cal-market)
      with the market blend NOT applied (blendApplied false in the
      lane marker) — the blend was skipped at first publication
      solely because win odds were incomplete then;
    - it does not already carry a blend-upgrade revision (the
      upgrade is exactly-once; a blended forecast is final and
      later odds movement never re-triggers it);
    - the post is still at least BLEND_UPGRADE_MIN_LEAD away;
    - the CURRENT payload carries a win odd (> 1.0) for every
      horse on the active roster — the same coverage rule the
      blend itself applies to the probability vector, checked on
      the roster so an incomplete card never starts a rebuild.

    Anything unreadable (no marker, no recorded blend flag) simply
    does not qualify; the caller keeps the frozen forecast. The
    caller still re-verifies after the rebuild that the blend
    actually landed before stamping anything.
    """
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    if marker.get("abilityLane") != V9B_LANE:
        return None
    blend_applied = marker.get("blendApplied")
    if not isinstance(blend_applied, bool):
        post_processing = marker.get("postProcessing")
        if isinstance(post_processing, dict):
            blend_applied = post_processing.get("blendApplied")
    if blend_applied is not False:
        return None
    revision = marker.get("revision")
    if isinstance(revision, dict) and (
            revision.get("kind") == "blend-upgrade"
            or revision.get("reason") == "blend-upgrade"):
        return None
    post = _post_at(old)
    if post is None or post - now < BLEND_UPGRADE_MIN_LEAD:
        return None
    by_number: dict[int, dict] = {}
    for horse in old.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        try:
            by_number[int(horse["horseNumber"])] = horse
        except (KeyError, TypeError, ValueError):
            continue
    for number, _name in _active_roster(old):
        horse = by_number.get(number)
        value = horse.get("winOdds") if isinstance(horse, dict) else None
        if not (isinstance(value, (int, float))
                and not isinstance(value, bool) and value > 1.0):
            return None
    return {"publishedAt": marker.get("publishedAt"),
            "firstPublishedAt": marker.get("firstPublishedAt"),
            "previousAbilityLane": V9B_LANE,
            "reason": "blend-upgrade"}


def _place_ev_upgrade_info(old: dict, now: datetime) -> dict | None:
    """Facts for the one-time place-EV upgrade of a frozen v9b race.

    A stored forecast qualifies only when ALL of these hold:

    - it was published on the v9b lane (abilityLane v9b-cal-market)
      — the calibrated series the combined gate is defined on;
    - its ticket plan does not already carry placeExpectedValues
      (a race that has them is final) and it does not already carry
      a place-ev-upgrade revision (the upgrade is exactly-once);
    - the post is still at least PLACE_EV_UPGRADE_MIN_LEAD away;
    - the CURRENT payload carries an observed place range
      (placeOddsLow >= 1.0, placeOddsHigh >= placeOddsLow) for
      every horse on the active roster;
    - the active field is at least 8 strong: at seven or fewer the
      place payout covers the top two only, and the stored product
      carries no top-2 probability to price that with (the build
      path prices small fields from the full marginals at first
      publication instead).

    Anything unreadable simply does not qualify; the caller keeps
    the frozen forecast (fail-closed).
    """
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    if marker.get("abilityLane") != V9B_LANE:
        return None
    revision = marker.get("revision")
    if isinstance(revision, dict) and (
            revision.get("kind") == "place-ev-upgrade"
            or revision.get("reason") == "place-ev-upgrade"):
        return None
    unified = old.get("unifiedForecast")
    if not isinstance(unified, dict):
        return None
    plan = unified.get("ticketPlan")
    if not isinstance(plan, dict) or "placeExpectedValues" in plan:
        return None
    post = _post_at(old)
    if post is None or post - now < PLACE_EV_UPGRADE_MIN_LEAD:
        return None
    roster = _active_roster(old)
    if len(roster) < 8:
        return None
    by_number: dict[int, dict] = {}
    for horse in old.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        try:
            by_number[int(horse["horseNumber"])] = horse
        except (KeyError, TypeError, ValueError):
            continue

    def _num(value) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    place_odds: dict[int, tuple[float, float]] = {}
    for number, _name in roster:
        horse = by_number.get(number)
        low = _num(horse.get("placeOddsLow")) if isinstance(horse, dict) else None
        high = _num(horse.get("placeOddsHigh")) if isinstance(horse, dict) else None
        if low is None or high is None or low < 1.0 or high < low:
            return None
        place_odds[number] = (low, high)
    return {"publishedAt": marker.get("publishedAt"),
            "firstPublishedAt": marker.get("firstPublishedAt"),
            "previousAbilityLane": V9B_LANE,
            "reason": "place-ev-upgrade",
            "placeOdds": place_odds}


def _apply_place_ev_upgrade(old: dict, info: dict, captured: str):
    """Build the place-EV upgrade re-issue of a frozen forecast.

    Surgical by construction: the stored probabilities, marks and
    tickets are kept exactly as published; the place side is priced
    from the STORED top-3 probabilities (the unified diagnosis
    carries every runner's) and the current payload's observed
    place ranges. Adds ticketPlan.placeExpectedValues +
    combinedPicks, flags the combined-gate qualifiers with the 注
    attention overlay, and re-seals the receipt. The combined gate
    is the frozen candidate rule of 2026-11-04 (win EV >= 1.25 AND
    win probability >= 0.05 AND place EV lower bound >= 1.0),
    evaluated on the stored win EV entries. Returns (new_detail,
    receipt), or None when the stored product cannot support the
    computation (fail-closed: the caller keeps the frozen
    forecast).
    """
    import copy

    unified = copy.deepcopy(old.get("unifiedForecast") or {})
    plan = unified.get("ticketPlan")
    if not isinstance(plan, dict):
        return None
    win = {
        e.get("horseNumber"): e
        for e in plan.get("winExpectedValues") or []
        if isinstance(e, dict) and isinstance(e.get("horseNumber"), int)
    }
    top3: dict[int, float] = {}
    for d in unified.get("diagnosis") or []:
        if not isinstance(d, dict):
            continue
        value = d.get("top3Probability")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            top3[d.get("horseNumber")] = float(value)
    entries = []
    for number, (low, high) in info["placeOdds"].items():
        probability = top3.get(number)
        if probability is None:
            return None
        entries.append({
            "horseNumber": number,
            "top3Probability": round(probability, 4),
            "placeOddsLow": low,
            "placeOddsHigh": high,
            "expectedValueLow": round(probability * low, 4),
            "expectedValueHigh": round(probability * high, 4),
        })
    entries.sort(key=lambda e: (-e["expectedValueLow"], e["horseNumber"]))
    picks = []
    for e in entries:
        w = win.get(e["horseNumber"]) or {}
        win_ev = w.get("expectedValue")
        win_p = w.get("winProbability")
        if (isinstance(win_ev, (int, float)) and win_ev >= 1.25
                and isinstance(win_p, (int, float)) and win_p >= 0.05
                and e["expectedValueLow"] >= 1.0):
            picks.append(e["horseNumber"])
    plan["placeExpectedValues"] = entries
    plan["combinedPicks"] = picks
    suppressed = plan.get("suppressed")
    if isinstance(suppressed, dict):
        suppressed.pop("ev_place", None)
    pick_set = set(picks)
    for m in unified.get("marks") or []:
        if isinstance(m, dict) and m.get("horseNumber") in pick_set:
            m["attention"] = True
    unified["receiptSha256"] = _canonical_receipt(unified)

    new = copy.deepcopy(old)
    new["unifiedForecast"] = unified
    marks = copy.deepcopy(old.get("predictionMarks") or [])
    by_no = {
        m.get("horseNumber"): m
        for m in marks
        if isinstance(m, dict) and isinstance(m.get("horseNumber"), int)
    }
    for number in picks:
        entry = by_no.get(number)
        if entry is not None:
            entry["attention"] = True
        else:
            w = win.get(number) or {}
            marks.append({
                "horseNumber": number,
                "mark": "",
                "winProbability": w.get("winProbability"),
                "attention": True,
            })
    new["predictionMarks"] = marks
    if isinstance(new.get("prediction"), dict):
        new["prediction"]["predictionMarks"] = marks
    previous = (old.get("preparedMeta") or {}).get("rewritePublish") or {}
    prev_revision = previous.get("revision")
    prev_count = (prev_revision.get("revisionCount")
                  if isinstance(prev_revision, dict) else None)
    meta = dict(old.get("preparedMeta") or {})
    marker = dict(previous)
    marker["publishedAt"] = captured
    marker["receiptSha256"] = unified["receiptSha256"]
    marker["firstPublishedAt"] = (
        info.get("firstPublishedAt") or info.get("publishedAt") or captured)
    marker["revision"] = {
        "kind": "place-ev-upgrade",
        "reason": "place-ev-upgrade",
        "revisedAt": captured,
        "revisionCount": (prev_count if isinstance(prev_count, int)
                          else 0) + 1,
        "previousReceiptSha256": info.get("receipt")
        or previous.get("receiptSha256"),
        "previousAbilityLane": V9B_LANE,
        "abilityLane": V9B_LANE,
        "note": ("one-time place-EV upgrade (user instruction "
                 "2026-11-04): the upstream sync did not carry "
                 "place odds at first publication, so the ticket "
                 "plan had no placeExpectedValues; probabilities, "
                 "marks and tickets are the stored ones, only the "
                 "place side and the combined-gate attention "
                 "overlay were added"),
    }
    meta["rewritePublish"] = marker
    new["preparedMeta"] = meta
    return new, unified["receiptSha256"]


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


def _active_roster(detail: dict) -> list[tuple[int, str]]:
    """The detail's current active roster, built exactly as the
    receipt roster is built at publish time."""
    return sorted(
        (int(h["horseNumber"]), str(h.get("name") or ""))
        for h in detail.get("horses") or []
        if isinstance(h, dict) and h.get("horseNumber")
        and not _is_inactive(h))


def _freeze_decision(old: dict):
    """Classify a stored detail against this lane's frozen publication.

    Returns None when the race was never published ready by this lane
    (normal first publication), ("frozen", receipt) when the stored
    ready forecast must be left byte-stable, or ("reissue", info)
    when the active roster changed since the frozen publication.
    A detail that carries this lane's ready markers but whose frozen
    state cannot be read consistently raises ValueError; the caller
    fails closed (skip, no overwrite) rather than guess.
    """
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    # Publications stamped by this lane under the current OR the
    # previous model version are this lane's frozen state: a model
    # version bump must not silently unfreeze (and recompute) a
    # forecast that is already on sale. Movement between lanes
    # happens only through the explicit lane-upgrade re-issue.
    if marker.get("modelVersion") not in (MODEL_VERSION,
                                          PREVIOUS_MODEL_VERSION):
        return None
    if old.get("predictionStatus") != "ready":
        return None
    if old.get("predictionModelVersion") not in (MODEL_VERSION,
                                                 PREVIOUS_MODEL_VERSION):
        return None
    unified = old.get("unifiedForecast")
    if not isinstance(unified, dict):
        raise ValueError("lane-marked ready detail has no unifiedForecast")
    receipt = unified.get("receiptSha256")
    if not receipt or marker.get("receiptSha256") != receipt:
        raise ValueError(
            "lane marker receipt does not match the stored unified forecast")
    roster = unified.get("roster")
    if not isinstance(roster, list):
        raise ValueError("stored unified forecast has no receipt roster")
    frozen_roster = sorted(
        (int(r["horseNumber"]), str(r.get("name") or ""))
        for r in roster
        if isinstance(r, dict) and r.get("horseNumber"))
    if len(frozen_roster) != len(roster):
        raise ValueError("stored receipt roster has unreadable entries")
    current_roster = _active_roster(old)
    if current_roster == frozen_roster:
        return "frozen", receipt
    frozen_by_no = dict(frozen_roster)
    current_by_no = dict(current_roster)
    info = {
        "receipt": receipt,
        "publishedAt": marker.get("publishedAt"),
        "added": sorted(set(current_by_no) - set(frozen_by_no)),
        "removed": sorted(set(frozen_by_no) - set(current_by_no)),
        "renamed": sorted(
            no for no in set(frozen_by_no) & set(current_by_no)
            if frozen_by_no[no] != current_by_no[no]),
    }
    return "reissue", info


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
    # Forecast freeze: a race this lane already published ready is
    # never recomputed. A roster change re-issues it (stamped as a
    # revision below); so does a lane upgrade — a v1-lane fallback
    # frozen only because the v8 extras had not landed yet is
    # re-issued on the v8 lane once the extras exist; and so does
    # the one-time blend upgrade of a v9b forecast frozen without
    # its market blend (see _blend_upgrade_info). Unreadable
    # frozen state fails closed.
    try:
        freeze = _freeze_decision(old)
    except Exception as exc:  # state unreadable: do not overwrite
        return None, (f"frozen-state unreadable ({type(exc).__name__}: "
                      f"{exc}); not overwriting")
    reissue = None
    lane_upgrade = None
    blend_upgrade = None
    if freeze is not None:
        if freeze[0] == "frozen":
            lane_upgrade = _lane_upgrade_info(old)
            if lane_upgrade is not None:
                lane_upgrade["receipt"] = freeze[1]
            else:
                # The last freeze exceptions: a v9b forecast frozen
                # WITHOUT its market blend only because win odds
                # were incomplete at first publication is re-issued
                # once when the odds complete (see
                # _blend_upgrade_info); a v9b forecast frozen
                # WITHOUT placeExpectedValues only because the
                # upstream sync did not carry place odds yet is
                # re-issued once when they complete (see
                # _place_ev_upgrade_info — surgical, it applies on
                # top of the freshest stored forecast and never
                # undoes a blend upgrade). Anything else stays
                # frozen.
                blend_upgrade = _blend_upgrade_info(old, now)
                if blend_upgrade is None:
                    place_ev_upgrade = _place_ev_upgrade_info(old, now)
                    if place_ev_upgrade is None:
                        return None, (f"frozen: already published ready "
                                      f"(receipt {str(freeze[1])[:12]}…); "
                                      f"roster unchanged")
                    place_ev_upgrade["receipt"] = freeze[1]
                    upgraded = _apply_place_ev_upgrade(
                        old, place_ev_upgrade,
                        now.isoformat(timespec="seconds"))
                    if upgraded is None:
                        return None, (
                            f"frozen: already published ready "
                            f"(receipt {str(freeze[1])[:12]}…); "
                            f"place-EV upgrade could not be computed "
                            f"from the stored product; keeping the "
                            f"frozen forecast")
                    return upgraded
                blend_upgrade["receipt"] = freeze[1]
        else:
            reissue = freeze[1]
    race = normalize_race(summary, old, source="production-api-readback")
    race_date = str(old.get("date") or race.date or "")
    segment = race.segment.value
    forecast = None
    used_v8 = False
    v8_fallback_status = None
    if race_date >= V8_CUTOVER_DATE and segment in V8_WEIGHTS:
        entry = _load_v8_extras(race_date).get(race.race_id)
        raw_extras = entry.get("extras") if isinstance(entry, dict) else None
        if isinstance(raw_extras, dict) and raw_extras:
            try:
                extras = {int(n): v for n, v in raw_extras.items()
                          if isinstance(v, dict)}
            except (TypeError, ValueError):
                extras = {}
            if extras:
                v8_forecast = forecast_race_v8(race, extras)
                if v8_forecast.status == "ok":
                    forecast = v8_forecast
                    used_v8 = True
                else:
                    v8_fallback_status = v8_forecast.status
        elif reissue is None and lane_upgrade is None \
                and blend_upgrade is None:
            # Deferral: a v8-eligible race whose extras have not
            # landed yet is not first-published on the v1 lane (the
            # freeze would lock that fallback in for the whole day —
            # the 2026-11-02 incident). Skip this cycle; a later one
            # publishes it on the v8 lane. Hard deadline 06:00 JST on
            # race day: past it, fall through to the v1 fallback.
            # Re-issues (roster change / lane upgrade / blend
            # upgrade) never defer: they must proceed with whatever
            # lane is usable now.
            deadline = _v8_extras_deadline(race_date)
            if (deadline is not None and now.tzinfo is not None
                    and now < deadline):
                return None, (f"deferred: v8 extras for {race_date} "
                              f"not yet available; first publication "
                              f"waits for the extras or the race-day "
                              f"06:00 JST deadline")
    if forecast is None:
        forecast = forecast_race(
            race, beta=LANE_BETA,
            weights=LANE_WEIGHTS.get(segment, {}))
    if forecast.status != "ok":
        return None, f"forecast not ok: {forecast.status}"
    pace = forecast_pace(race)
    win_odds = {
        r.number: r.win_odds.value
        for r in race.runners
        if r.win_odds.present
        and isinstance(r.win_odds.value, (int, float))
    }
    # v9b post-processing (adopted 2026-11-03): on the v8 lane the
    # probability vector is calibrated and market-blended with the
    # shadow lane's exact transform before marks, tickets and the
    # EV display derive from it. The win odds are the publisher's
    # own payload odds at compute time; the blend applies only
    # when every runner in the vector carries one (> 1.0), never
    # imputed. A degenerate vector the transform passes through
    # unchanged keeps the plain v8 lane label for that race.
    used_v9b = False
    blend_applied = False
    v9b_passthrough = None
    if used_v8:
        forecast, pp_info = postprocess_forecast(
            forecast, arm="v9b", win_odds=win_odds)
        if "passthrough" in pp_info:
            v9b_passthrough = pp_info["passthrough"]
        else:
            used_v9b = True
            blend_applied = bool(pp_info["blendApplied"])
    if lane_upgrade is not None and not used_v9b:
        # The extras exist but this race still cannot take the top
        # lane (a segment without a candidate, or the v8 forecast
        # did not come back ok): keep the frozen forecast
        # byte-stable instead of recomputing it on the v1 lane,
        # where backfilled inputs could drift a forecast on sale.
        return None, (f"frozen: already published ready "
                      f"(receipt {str(lane_upgrade['receipt'])[:12]}…); "
                      f"v9b lane not usable for this race; "
                      f"keeping the frozen "
                      f"{lane_upgrade['previousAbilityLane']} forecast")
    if blend_upgrade is not None and not (used_v9b and blend_applied):
        # The upgrade was attempted but the blend did not land —
        # the odds in the rebuilt payload still do not cover the
        # probability vector, or the v9b transform passed through:
        # re-issuing now would rewrite a forecast on sale WITHOUT
        # the one change that justifies it, on inputs that may
        # have backfilled since first publication. Keep the frozen
        # calibration-only forecast byte-stable; a later cycle can
        # retry while the qualification still holds.
        return None, (f"frozen: already published ready "
                      f"(receipt {str(blend_upgrade['receipt'])[:12]}…); "
                      f"blend upgrade did not land; keeping the "
                      f"frozen calibration-only forecast")
    # Trifecta formation B (adopted 2026-10-31 after the
    # pre-registered primary paired judgement against legacy A at
    # 142 races). Probabilities, marks and every other ticket kind
    # are unchanged; the sealing lane keeps the legacy formation.
    # Place （複勝） odds ranges from the same payload rows as the
    # win odds: carried into the ticket plan as display-only place
    # EV ranges. Runners without an observed range simply have no
    # place estimate; nothing is derived from their win odds.
    place_odds = {}
    for r in race.runners:
        if r.place_odds_low.present and r.place_odds_high.present:
            low = r.place_odds_low.value
            high = r.place_odds_high.value
            if (isinstance(low, (int, float)) and not isinstance(low, bool)
                    and isinstance(high, (int, float))
                    and not isinstance(high, bool)):
                place_odds[r.number] = (float(low), float(high))
    tickets = generate_tickets(forecast, win_odds,
                               calibration_validated=False,
                               trifecta_formation="B",
                               place_odds=place_odds)
    captured = now.isoformat(timespec="seconds")
    payload = race_payload(
        race, forecast, pace, tickets,
        provenance={"captured_at": captured, "snapshot_sha256": None},
        calibrated_probabilities=used_v9b)
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
    if used_v9b:
        # Per-race honest labeling: ability is the v8 layer, the
        # probabilities are its v9b post-processing (temperature
        # calibration + market blend). Stamped before the receipt
        # hash so the label is part of the verified product.
        unified["abilityModelVersion"] = V9B_ABILITY_MODEL_VERSION
        unified["probabilityStatus"] = V9B_PROBABILITY_STATUS
    elif used_v8:
        # Per-race honest labeling: this forecast's ability layer is
        # the adopted v8 candidate, not the v1 prior. Stamped before
        # the receipt hash so the label is part of the verified
        # product.
        unified["abilityModelVersion"] = V8_ABILITY_MODEL_VERSION
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
        "methodologyStatus": (
            "rewrite-engine-probability-calibrated-market-blend"
            if used_v9b else
            "rewrite-engine-probability-uncalibrated"),
        "actualForecasterPublishedPicks": True,
        "calibrationMethod": (
            "temperature-0.6692+geometric-market-blend-0.5"
            if used_v9b else
            "none-probabilities-uncalibrated"),
        "modelVersion": MODEL_VERSION,
        "predictionStatus": "ready", "productionEligible": True,
        "stages": {
            "ability": {"status": V9B_ABILITY_STATUS if used_v9b
                        else V8_ABILITY_STATUS if used_v8
                        else "rewrite-ability-prior-v1"},
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
        "receiptSha256": unified["receiptSha256"],
        "abilityLane": V9B_LANE if used_v9b
        else "v8-elo-speed2" if used_v8 else "v1-prior"}
    if used_v9b:
        meta["rewritePublish"]["temperature"] = V9B_TEMPERATURE
        meta["rewritePublish"]["blendApplied"] = blend_applied
        meta["rewritePublish"]["postProcessing"] = {
            "type": "temperature+market-blend",
            "temperature": V9B_TEMPERATURE,
            "blendWeight": V9B_BLEND_WEIGHT,
            "blendApplied": blend_applied}
    if v9b_passthrough is not None:
        meta["rewritePublish"]["v9bPassthrough"] = (
            f"v9b post-processing passed through: {v9b_passthrough}; "
            f"v8 probabilities kept for this race")
    if v8_fallback_status is not None:
        meta["rewritePublish"]["v8Fallback"] = (
            f"v8 forecast not ok: {v8_fallback_status}; v1 lane used")
    if reissue is not None:
        # Roster-change re-issue of a frozen forecast: keep the chain
        # auditable inside the lane marker (first publication time,
        # previous receipt, exactly how the roster moved).
        previous = (old.get("preparedMeta") or {}).get("rewritePublish") or {}
        prev_revision = previous.get("revision")
        prev_count = (prev_revision.get("revisionCount")
                      if isinstance(prev_revision, dict) else None)
        meta["rewritePublish"]["firstPublishedAt"] = (
            reissue.get("publishedAt") or captured)
        meta["rewritePublish"]["revision"] = {
            "reason": "roster-change",
            "revisedAt": captured,
            "revisionCount": (prev_count if isinstance(prev_count, int)
                              else 0) + 1,
            "previousReceiptSha256": reissue["receipt"],
            "rosterAdded": reissue["added"],
            "rosterRemoved": reissue["removed"],
            "rosterRenamed": reissue["renamed"],
        }
    if lane_upgrade is not None:
        # Lane-upgrade re-issue of a frozen forecast: the roster is
        # unchanged, but the forecast moves from the lane it was
        # frozen on (the v1 fallback, frozen in only because the
        # extras had not landed at first publication — or, on the
        # v9b adoption date only, the v8 lane) to the v9b lane. Same
        # audit chain as a roster change: first publication time and
        # previous receipt, plus the lane it upgrades from and the
        # reason, so the two upgrade kinds stay distinguishable.
        previous = (old.get("preparedMeta") or {}).get("rewritePublish") or {}
        prev_revision = previous.get("revision")
        prev_count = (prev_revision.get("revisionCount")
                      if isinstance(prev_revision, dict) else None)
        meta["rewritePublish"]["firstPublishedAt"] = (
            lane_upgrade.get("publishedAt") or captured)
        revision = {
            "reason": lane_upgrade["reason"],
            "revisedAt": captured,
            "revisionCount": (prev_count if isinstance(prev_count, int)
                              else 0) + 1,
            "previousReceiptSha256": lane_upgrade["receipt"],
            "previousAbilityLane": lane_upgrade["previousAbilityLane"],
            "abilityLane": V9B_LANE,
        }
        if lane_upgrade["reason"] == "lane-upgrade-v9b-adoption":
            revision["note"] = (
                "v9b production adoption-day measure (user "
                "instruction 2026-11-03): no race dated "
                "2026-11-04 stays on the v8 lane")
        meta["rewritePublish"]["revision"] = revision
    if blend_upgrade is not None:
        # Blend-upgrade re-issue of a frozen forecast: the roster
        # and the lane are unchanged — the only change is that the
        # market blend, skipped at first publication because win
        # odds were incomplete, now applies. Same audit chain as
        # the other re-issues: the first publication time is
        # preserved and the previous receipt is recorded. The
        # marker's blendApplied (stamped above from the rebuild) is
        # true from here on, which is what makes the upgrade
        # exactly-once: this qualification can never hold again
        # for this race.
        previous = (old.get("preparedMeta") or {}).get("rewritePublish") or {}
        prev_revision = previous.get("revision")
        prev_count = (prev_revision.get("revisionCount")
                      if isinstance(prev_revision, dict) else None)
        meta["rewritePublish"]["firstPublishedAt"] = (
            blend_upgrade.get("firstPublishedAt")
            or blend_upgrade.get("publishedAt") or captured)
        meta["rewritePublish"]["revision"] = {
            "kind": "blend-upgrade",
            "reason": "blend-upgrade",
            "revisedAt": captured,
            "revisionCount": (prev_count if isinstance(prev_count, int)
                              else 0) + 1,
            "previousReceiptSha256": blend_upgrade["receipt"],
            "previousAbilityLane": V9B_LANE,
            "abilityLane": V9B_LANE,
            "note": ("one-time blend upgrade (user instruction "
                     "2026-11-04): win odds were incomplete at "
                     "first publication, so the race was frozen "
                     "with temperature calibration only; the "
                     "market blend applies from this revision"),
        }
    new["preparedMeta"] = meta
    return new, unified["receiptSha256"]


def publish_date(date: str, token: str | None, dry_run: bool) -> dict:
    from arvexq.ingest.full_snapshot_codec import pack_detail, unpack_detail
    from arvexq.prediction.unified_product import verified as verified_unified

    protect_detail = _load_protect()
    listing = _get(f"/api/races?date={date}")
    summaries = listing.get("races") or listing.get("summaries") or []
    counts = {"races": len(summaries), "published": 0, "skipped": 0,
              "frozen": 0, "deferred": 0, "reissued": 0, "failed": 0}
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
                if isinstance(receipt, str) and receipt.startswith("frozen:"):
                    counts["frozen"] += 1
                    print(f"FREEZE {race_id}: {receipt}")
                elif (isinstance(receipt, str)
                        and receipt.startswith("deferred:")):
                    counts["deferred"] += 1
                    print(f"DEFER {race_id}: {receipt}")
                else:
                    counts["skipped"] += 1
                    print(f"SKIP {race_id}: {receipt}")
                continue
            revision = ((new.get("preparedMeta") or {})
                        .get("rewritePublish") or {}).get("revision")
            if revision is not None:
                counts["reissued"] += 1
            check = verified_unified(dict(unpack_detail(old_raw),
                                          unifiedForecast=new["unifiedForecast"]))
            if check is None:
                counts["failed"] += 1
                print(f"FAIL {race_id}: product does not self-verify")
                continue
            if dry_run:
                counts["published"] += 1
                print(f"DRY  {race_id}: receipt {receipt[:12]}… verified"
                      + (f" ({revision.get('reason')} reissue)"
                         if revision else ""))
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
            print(f"OK   {race_id}: receipt {receipt[:12]}… live"
                  + (f" ({revision.get('reason')} reissue)"
                     if revision else ""))
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
