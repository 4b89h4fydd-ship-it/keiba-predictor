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
added), and a race already carrying placeExpectedValues is final.
A fifth exception of the same kind is the ticket-R24 upgrade
(2026-11-08): the production trifecta recommendation switched
from formation B (36 points) to R24 (24 points) by user order, so
a forecast frozen with the B-form trifecta is re-issued once —
stamped kind "ticket-r24-upgrade" — with ONLY the trifecta
recommendation narrowed to the R24 subset of the very same stored
combinations (win leg = mark ranks 1-2); the forecast, marks,
probabilities, odds and every other ticket kind are kept
byte-for-byte, and a race whose trifecta already is the R24
subset is final. A sixth exception of the same kind is the
env-repair re-issue (2026-11-09): the NAR summary/detail builders
hardcoded the race surface to "" until main 2e01ec9e, so every
forecast computed from a payload fetched before that fix took
effect ran with the surface suitability feature dead for every
runner. By user instruction (「印かえていいよ」, 2026-11-09) a
frozen v9b forecast dated 2026-11-09 (NAR) whose probabilities
were last computed before the fix is re-issued once — stamped
kind "env-repair-upgrade" — recomputed from the current payload,
which now carries the stored surface; marks may move. Races
already recomputed after the fix do not qualify, and finished
races never reach the branch. The v9b
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
from rewrite.analysis.shadow_v8 import (  # noqa: E402
    NAR_EVIDENCE_DECAY_K, forecast_race_v8)
from rewrite.analysis.shadow_v9 import BLEND_WEIGHT as V9B_BLEND_WEIGHT  # noqa: E402
from rewrite.analysis.shadow_v9 import TEMPERATURE as V9B_TEMPERATURE  # noqa: E402
from rewrite.analysis.shadow_v9 import postprocess_forecast  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
from rewrite.analysis.master_v1 import master_candidate  # noqa: E402
from rewrite.analysis.master_bets import ticket_styles  # noqa: E402
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

# F1 evidence decay, NAR only (2026-11-12, user instruction after
# the development evaluation on research branch
# research/f1-evidence-decay-20261112: 331 NAR races, all six
# headline metrics improved for the runs-k2 candidate, ◎ win rate
# +2.42pt, date-cluster 95% CI +0.53..+4.05; the same evaluation
# showed no improvement — if anything harm — on JRA, so JRA is
# never decayed). On the v8 lane, a NAR race's raw ability scores
# are shrunk toward the scored-field mean by evidence reliability
# n / (n + k), k = NAR_EVIDENCE_DECAY_K, inside forecast_race_v8
# (which also gates on Segment.NAR itself). The lane and the model
# version do NOT move: the decay is an ability-layer change, so it
# is labelled where the ability layer is labelled — the sealed
# product's abilityModelVersion gains a "-nar-decay2" suffix on
# decayed races (stamped before the receipt hash, like the v9b
# label), and the lane marker records the same fact. Races already
# frozen keep their frozen forecast untouched; the decay reaches
# only races first-published (or re-issued) after this change.
NAR_DECAY_V9B_ABILITY_MODEL_VERSION = (
    V9B_ABILITY_MODEL_VERSION + "-nar-decay2")
NAR_DECAY_V8_ABILITY_MODEL_VERSION = (
    V8_ABILITY_MODEL_VERSION + "-nar-decay2")

# NAR decay upgrade (2026-11-12, user instruction "from today's
# remaining races"): the decay above reaches races first-published
# after it landed, but the user directed that today's NAR races
# still pre-post move to the new method as well. A NAR race frozen
# on the v9b lane with an UNDECAYED abilityModelVersion is therefore
# re-issued ONCE from the current payload (see
# _nar_decay_upgrade_info) — the same one-time upgrade pattern as
# the blend / env-repair branches, never a direct store rewrite.
# Exactly-once is structural: the re-issue stamps the decayed
# label, so the qualification can never hold again. Races past
# their post (or with a result) never reach the branch — the
# build's post/result checks run first. The lead guard matches
# the env-repair branch (15 minutes): the rebuild input is not
# odds-dependent, and the buffer keeps a race from starting
# between the guard's evaluation and its write.
NAR_DECAY_UPGRADE_MIN_LEAD = timedelta(minutes=15)

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

# Ticket-R24 upgrade (2026-11-08, user order: the production
# trifecta recommendation switches from formation B to R24 —
# win leg narrowed from mark ranks 1-3 to mark ranks 1-2, 36 ->
# 24 points — after the screen on the graded 194 production
# races of 2026-11-04..07, B ROI 0.7230 -> R24 0.9055). Races
# already published with the B-form trifecta are re-issued ONCE
# under the surgical pattern of the place-EV upgrade (see
# _ticket_r24_upgrade_info / _apply_ticket_r24_upgrade): only the
# trifecta recommendation blocks are filtered to the R24 subset
# of the stored combinations; the forecast itself never moves.
# The same 60-minute guard as the other upgrades keeps the
# recommendation stable in the final hour before post. The
# forward lane v34 is untouched: its control arm stays B36.
TICKET_R24_UPGRADE_MIN_LEAD = timedelta(minutes=60)

# Ticket formation by segment (2026-11-12, user order): the
# production trifecta formation is R24 for JRA and pool4-axis2
# ("P4A2") for NAR — R24 with the leg pool narrowed from the top
# five marks to the top four, so the fifth mark (☆) is in no leg
# (24 -> 12 points), no probability cut: the cut candidate from
# the same sweep is NOT adopted, its standalone effect was
# unestablished. Evidence: the offline threshold sweep on the
# frozen-gate corpus built from the stored production details
# (research/r24-threshold-sweep-20261112) returned 0.662 against
# R24's 0.486 on the #509 NAR test set (139 races) and 0.800
# against 0.629 on the extended 200-race set, ahead of R24 on
# all five days. New NAR publications build P4A2 directly and
# the lane marker records the fact under "ticketFormation"; a
# NAR race already frozen with the R24 trifecta is re-issued
# ONCE under the surgical pattern of the ticket-R24 upgrade
# (see _ticket_pool4_upgrade_info / _apply_ticket_pool4_upgrade):
# only the trifecta recommendation blocks are filtered to the
# P4A2 subset of the stored combinations; the forecast itself
# never moves. JRA publications stay exactly what they were —
# R24, and no ticketFormation marker entry.
NAR_TRIFECTA_FORMATION = "P4A2"
TICKET_POOL4_UPGRADE_MIN_LEAD = timedelta(minutes=60)

# Env-repair re-issue (2026-11-09, user instruction 「印かえていいよ」):
# the NAR summary/detail builders hardcoded the race surface to ""
# (app.py nar_race_summaries / nar_race_detail /
# _fast_local_race_detail) until main 2e01ec9e (committed
# 2026-11-09 10:21 JST) made them serve the stored races.surface,
# so any forecast computed from a payload fetched before the fix
# took effect ran with the surface suitability feature dead for
# every runner. A frozen v9b forecast dated ENV_REPAIR_DATE (NAR
# only) whose probabilities were last computed before
# ENV_REPAIR_FIX_LIVE_AT is therefore re-issued ONCE from the
# current payload — see _env_repair_upgrade_info. The probability
# computation time is the latest forecast-recomputing revision
# (roster change / lane upgrade / blend upgrade) or, when the
# latest revision is surgical (place-EV / ticket-R24 keep the
# stored probabilities), the first publication time. Races already
# recomputed at or after the fix (e.g. a roster-change re-issue
# later that morning) do not qualify. The lead guard is 15
# minutes: the repair input (the race's surface, served by the
# summary builder from the stored races.surface) is static and
# has been available since the fix, unlike the odds
# completeness the other upgrades wait on. The buffer exists
# so a race cannot start between the guard's evaluation (per
# race, at its build) and its write.
ENV_REPAIR_DATE = "2026-11-09"
ENV_REPAIR_FIX_LIVE_AT = datetime(2026, 11, 9, 10, 22, tzinfo=JST)
ENV_REPAIR_MIN_LEAD = timedelta(minutes=15)


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


def _get_admin(path: str, token: str) -> dict:
    """GET an SYNC_TOKEN-authenticated API path (snapshot export)."""
    req = urllib.request.Request(
        API_BASE + path,
        headers={"User-Agent": UA, "Accept": "application/json",
                 "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Surgical ticket revisions (the one-time formation narrowings)
# keep the stored forecast — and with it the masterAnalysis
# shadow sidecar — byte-identical by construction; they never
# recompute the analysis the sidecar signs.
SURGICAL_TICKET_REVISION_KINDS = ("ticket-r24-upgrade",
                                  "ticket-pool4-upgrade")


def _restore_pristine_sidecar(new: dict, token: str | None):
    """Replace a surgical re-issue's masterAnalysis with the
    pristine stored copy, fetched over the authenticated
    snapshot-export channel.

    Returns (ok, reason): reason names the failing step when ok
    is False, so a rejected lane run says exactly which link of
    the chain broke instead of a bare failure.

    Why: the lane reads stored details through the public API
    projection, which does not preserve the sidecar's signed
    bytes (its contentSha256 no longer re-hashes over the read
    copy), and protect_detail strict-verifies the sidecar of any
    marker-advancing publish write — so a surgical re-issue,
    whose marker advances while its sidecar is inherited from
    the projected read, is rejected with "masterAnalysis
    signature or capture mismatch" even though nothing about
    the analysis changed. The D1 row itself still holds the
    pristine sidecar; the snapshot export returns it verbatim.

    The stored copy is adopted only when its identity chains to
    this write: same version and capturedAt as the incoming
    sidecar, the stored publication's receipt equals the
    revision's previousReceiptSha256, and the stored sidecar's
    own digest verifies. Anything else fails and the caller
    fails the write closed (retryable) rather than post a
    sidecar whose bytes cannot be verified.
    """
    sidecar = new.get("masterAnalysis")
    if not isinstance(sidecar, dict):
        return True, "no-sidecar"  # nothing signed to restore
    if not token:
        return False, "no-token"
    race_id = str(new.get("id") or "")
    if not race_id:
        return False, "no-race-id"
    revision = ((new.get("preparedMeta") or {}).get("rewritePublish")
                or {}).get("revision") or {}
    try:
        resp = _get_admin(
            "/api/admin/snapshot-export?table=race_details&race_id="
            + urllib.parse.quote(race_id, safe=""), token)
    except Exception as exc:
        return False, f"export-fetch: {type(exc).__name__}: {exc}"
    rows = resp.get("rows") or []
    if not rows:
        return False, "export-no-rows"
    payload = rows[0].get("payload")
    try:
        stored = (json.loads(payload) if isinstance(payload, str)
                  else payload)
        if not isinstance(stored, dict):
            return False, "payload-not-a-dict"
        from arvexq.ingest.full_snapshot_codec import unpack_detail
        stored = unpack_detail(stored)
    except Exception as exc:
        return False, f"payload-parse: {type(exc).__name__}: {exc}"
    stored_sidecar = stored.get("masterAnalysis")
    if not isinstance(stored_sidecar, dict):
        return False, "no-stored-sidecar"
    if stored_sidecar.get("version") != sidecar.get("version"):
        return False, "version-mismatch"
    if stored_sidecar.get("capturedAt") != sidecar.get("capturedAt"):
        return False, "captured-at-mismatch"
    stored_marker = ((stored.get("preparedMeta") or {})
                     .get("rewritePublish") or {})
    if (not revision.get("previousReceiptSha256")
            or stored_marker.get("receiptSha256")
            != revision.get("previousReceiptSha256")):
        return False, "receipt-chain-mismatch"
    from hashlib import sha256
    unsigned = {k: v for k, v in stored_sidecar.items()
                if k != "contentSha256"}
    expected = sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    if stored_sidecar.get("contentSha256") != expected:
        return False, "stored-digest-mismatch"
    import copy as _copy
    new["masterAnalysis"] = _copy.deepcopy(stored_sidecar)
    return True, "restored"


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


def _parse_stamp(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed


def _env_repair_upgrade_info(old: dict, now: datetime,
                             summary_surface=None) -> dict | None:
    """Facts for the one-time env-repair re-issue of a frozen v9b race.

    A stored forecast qualifies only when ALL of these hold:

    - the race is dated ENV_REPAIR_DATE and is a NAR race (the
      surface builders that hardcoded "" serve the NAR payloads;
      the dated scope keeps the repair to the day the user
      authorised it for);
    - it was published on the v9b lane (abilityLane
      v9b-cal-market);
    - its probabilities were last computed BEFORE
      ENV_REPAIR_FIX_LIVE_AT — the moment the surface fix
      (main 2e01ec9e) landed. The computation time is read from
      the lane marker: the latest forecast-recomputing revision
      (roster change / lane upgrade / blend upgrade) sets it;
      surgical revisions (place-EV, ticket-R24) keep the stored
      probabilities, so with one of those on top the
      probabilities still date from the first publication. A
      race recomputed at or after the fix (e.g. a roster-change
      re-issue later that morning) already ran with the live
      surface and does not qualify;
    - it does not already carry an env-repair-upgrade revision
      (the repair is exactly-once — the sole exception is a
      stored detail whose two marks blocks DISAGREE after the
      first repair's write raced a sync refresh; that race
      re-qualifies as a marks resync, see below);
    - the rebuild's surface input is real: normalize_race takes
      the race surface as _first(summary.surface,
      detail.surface) and keeps "" as a value, so the SUMMARY's
      surface is the value the rebuild computes with. The stored
      detail's own surface may still carry the "" baked in
      before the fix — that does not block the repair, and the
      summary (which the fixed summary builder serves from the
      stored races.surface) is what must be non-empty;
    - the post is still at least ENV_REPAIR_MIN_LEAD away.

    Anything unreadable does not qualify; the caller keeps the
    frozen forecast (fail-closed). The caller still re-verifies
    after the rebuild that the forecast landed on the v9b lane
    before stamping anything.
    """
    if str(old.get("date") or "") != ENV_REPAIR_DATE:
        return None
    race_id = str(old.get("id") or "")
    if not race_id.startswith("nar-"):
        return None
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    if marker.get("abilityLane") != V9B_LANE:
        return None
    revision = marker.get("revision")
    kind = None
    revised_at = None
    if isinstance(revision, dict):
        kind = revision.get("kind") or revision.get("reason")
        revised_at = revision.get("revisedAt")
    resync = False
    if kind == "env-repair-upgrade":
        # Exactly-once — with one narrow exception: the first
        # repair's write raced a concurrent sync refresh on three
        # races (Saga 3R, Nagoya 7R, Morioka 10R, 2026-11-09) and
        # the stored detail came out of the merge with the NEW
        # unifiedForecast beside the OLD predictionMarks — the
        # two marks blocks disagree, the state the protect seam
        # exists to prevent. Such a race re-qualifies so the
        # rebuild re-derives both blocks from one forecast and
        # the stored detail resyncs; a repaired race whose
        # blocks agree is final.
        def _marks(entries, *keys):
            out = {}
            for e in entries or []:
                if not isinstance(e, dict):
                    continue
                label = next((e.get(k) for k in keys if e.get(k)), None)
                if label:
                    out[str(label)] = e.get("horseNumber")
            return out
        pm = _marks(old.get("predictionMarks"), "mark")
        uf = _marks((old.get("unifiedForecast") or {}).get("marks"),
                    "markSymbol", "mark")
        if not (len(pm) == 5 and len(uf) == 5 and pm != uf):
            return None
        resync = True
        computed_at = _parse_stamp(
            revision.get("probabilityComputedAt") or revised_at)
        if computed_at is None:
            return None
    elif kind in ("blend-upgrade", "lane-upgrade",
                  "lane-upgrade-v9b-adoption", "roster-change"):
        computed_at = _parse_stamp(revised_at)
    else:
        computed_at = _parse_stamp(
            marker.get("firstPublishedAt") or marker.get("publishedAt"))
    if not resync and (computed_at is None
                       or computed_at >= ENV_REPAIR_FIX_LIVE_AT):
        return None
    surface = summary_surface
    if not (isinstance(surface, str) and surface.strip()):
        return None
    post = _post_at(old)
    if post is None or post - now < ENV_REPAIR_MIN_LEAD:
        return None
    return {"publishedAt": marker.get("publishedAt"),
            "firstPublishedAt": marker.get("firstPublishedAt"),
            "previousAbilityLane": V9B_LANE,
            "reason": "env-repair-upgrade",
            "surface": surface,
            "marksResync": resync,
            "probabilityComputedAt":
                computed_at.isoformat(timespec="seconds")}


def _nar_decay_upgrade_info(old: dict, now: datetime) -> dict | None:
    """Facts for the one-time NAR evidence-decay re-issue.

    A stored forecast qualifies only when ALL of these hold:

    - the race is a NAR race (race id prefix — the same test the
      env-repair branch uses; the decay is NAR-only by design and
      a jra- race can never qualify);
    - it was published on the v9b lane (abilityLane
      v9b-cal-market);
    - its sealed product does NOT already carry the decay: the
      abilityModelVersion stamped inside the receipt is one of the
      undecayed labels (the v9b or the v8 label). A race
      first-published after the decay landed, and a race already
      re-issued by this upgrade, carries a "-nar-decay2" label and
      never qualifies again — the upgrade is exactly-once by
      construction, with no date gate to expire;
    - the post is still at least NAR_DECAY_UPGRADE_MIN_LEAD away.

    Anything unreadable does not qualify; the caller keeps the
    frozen forecast (fail-closed). The caller still re-verifies
    after the rebuild that the decay actually landed (the rebuilt
    forecast came out of the decayed v8 layer) before stamping
    anything.
    """
    race_id = str(old.get("id") or "")
    if not race_id.startswith("nar-"):
        return None
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    if marker.get("abilityLane") != V9B_LANE:
        return None
    unified = old.get("unifiedForecast")
    if not isinstance(unified, dict):
        return None
    if unified.get("abilityModelVersion") not in (
            V9B_ABILITY_MODEL_VERSION, V8_ABILITY_MODEL_VERSION):
        return None
    post = _post_at(old)
    if post is None or post - now < NAR_DECAY_UPGRADE_MIN_LEAD:
        return None
    return {"publishedAt": marker.get("publishedAt"),
            "firstPublishedAt": marker.get("firstPublishedAt"),
            "previousAbilityLane": V9B_LANE,
            "reason": "nar-decay-upgrade"}


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


def _stored_mark_order(old: dict) -> list[int] | None:
    """Mark-ordered runner numbers (◎○▲△☆) from the stored detail.

    Read from BOTH stored mark blocks (top-level predictionMarks
    and the unified forecast's marks); the two must agree exactly,
    and every marked runner must carry one of the five symbols.
    Anything unreadable returns None (fail-closed).
    """
    symbols = ("◎", "○", "▲", "△", "☆")

    def _order(entries, number_key, symbol_key):
        if not isinstance(entries, list):
            return None
        by_symbol: dict[str, int] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            symbol = entry.get(symbol_key)
            if symbol not in symbols:
                continue
            try:
                number = int(entry[number_key])
            except (KeyError, TypeError, ValueError):
                return None
            if symbol in by_symbol:
                return None
            by_symbol[symbol] = number
        if not by_symbol:
            return None
        return [by_symbol[s] for s in symbols if s in by_symbol]

    top = _order(old.get("predictionMarks"), "horseNumber", "mark")
    unified = old.get("unifiedForecast")
    inner = _order(unified.get("marks") if isinstance(unified, dict)
                   else None, "horseNumber", "markSymbol")
    if top is None or inner is None or top != inner:
        return None
    return top


def _ticket_r24_upgrade_info(old: dict, now: datetime) -> dict | None:
    """Facts for the one-time ticket-R24 upgrade of a frozen race.

    A stored forecast qualifies only when ALL of these hold:

    - it carries this lane's publish marker (the caller reaches
      here only for a race the freeze decision classified as this
      lane's frozen publication, so marker/receipt consistency is
      already established) and it does not already carry a
      ticket-r24-upgrade revision (the upgrade is exactly-once);
    - the post is still at least TICKET_R24_UPGRADE_MIN_LEAD away;
    - the stored mark order is readable and identical in both
      stored mark blocks, with at least the ◎○▲ marks present;
    - the stored recommended trifecta is still exactly the
      formation-B construction on those marks (a race already
      carrying the R24 subset, or anything else, is final — the
      upgrade narrows B to R24 and invents nothing).

    Anything unreadable simply does not qualify; the caller keeps
    the frozen forecast (fail-closed).
    """
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    revision = marker.get("revision")
    if isinstance(revision, dict) and (
            revision.get("kind") == "ticket-r24-upgrade"
            or revision.get("reason") == "ticket-r24-upgrade"):
        return None
    post = _post_at(old)
    if post is None or post - now < TICKET_R24_UPGRADE_MIN_LEAD:
        return None
    unified = old.get("unifiedForecast")
    if not isinstance(unified, dict):
        return None
    if not isinstance(unified.get("ticketPlan"), dict):
        return None
    mark_order = _stored_mark_order(old)
    if mark_order is None or len(mark_order) < 3:
        return None
    from rewrite.analysis.tickets import (
        formation_b_selections, formation_r24_selections)
    trifecta = None
    for entry in old.get("recommendedBets") or []:
        if isinstance(entry, dict) and entry.get("kind") == "3連単":
            trifecta = entry
            break
    if trifecta is None:
        return None
    try:
        stored = {tuple(int(n) for n in combo)
                  for combo in trifecta.get("combos") or []}
    except (TypeError, ValueError):
        return None
    if stored == set(formation_r24_selections(mark_order)):
        return None  # already R24: final
    if stored != set(formation_b_selections(mark_order)):
        return None  # not the B construction: do not guess
    return {"publishedAt": marker.get("publishedAt"),
            "firstPublishedAt": marker.get("firstPublishedAt"),
            "previousAbilityLane": marker.get("abilityLane"),
            "reason": "ticket-r24-upgrade",
            "markOrder": mark_order}


def _apply_ticket_r24_upgrade(old: dict, info: dict, captured: str):
    """Build the ticket-R24 upgrade re-issue of a frozen forecast.

    Surgical by construction: the stored forecast — probabilities,
    marks, diagnosis, odds, EV blocks and every non-trifecta ticket
    kind — is kept exactly as published. Only the trifecta
    recommendation is narrowed: in the grouped recommendedBets
    (top level, and the prediction block's mirror, which the
    publisher always writes identical to it) every stored
    combination whose first leg is not a mark-rank 1-2 runner is
    dropped, and in the unified ticket plan the 3連単 items are
    filtered the same way. The result must equal the canonical
    R24 construction on the stored marks exactly, or the upgrade
    aborts (returns None; the caller keeps the frozen forecast).
    The receipt is re-sealed over the modified unified forecast
    and the revision is stamped kind "ticket-r24-upgrade" with the
    first publication time preserved.
    """
    import copy

    from rewrite.analysis.tickets import formation_r24_selections

    mark_order = info["markOrder"]
    top_two = set(mark_order[:2])
    expected = set(formation_r24_selections(mark_order))

    def _narrow(bets):
        if not isinstance(bets, list):
            return None
        out = []
        for entry in bets:
            if not isinstance(entry, dict):
                return None
            entry = copy.deepcopy(entry)
            if entry.get("kind") == "3連単":
                try:
                    kept = [list(combo) for combo in entry.get("combos") or []
                            if int(combo[0]) in top_two]
                    kept_set = {tuple(int(n) for n in combo)
                                for combo in kept}
                except (TypeError, ValueError, IndexError):
                    return None
                if kept_set != expected:
                    return None
                entry["combos"] = kept
                entry["points"] = len(kept)
            out.append(entry)
        return out

    new = copy.deepcopy(old)
    narrowed = _narrow(new.get("recommendedBets"))
    if narrowed is None:
        return None
    new["recommendedBets"] = narrowed
    prediction = new.get("prediction")
    if isinstance(prediction, dict):
        # The publisher writes prediction.recommendedBets identical
        # to the top-level list; the API projection strips it from
        # the read, so restore the mirror from the narrowed list
        # rather than dropping the stored block.
        prediction["recommendedBets"] = copy.deepcopy(narrowed)
    unified = new.get("unifiedForecast")
    if not isinstance(unified, dict):
        return None
    plan = unified.get("ticketPlan")
    if not isinstance(plan, dict) or not isinstance(plan.get("items"), list):
        return None
    items = []
    for item in plan["items"]:
        if isinstance(item, dict) and item.get("kind") == "3連単":
            combo = item.get("combo") or []
            try:
                first = int(combo[0])
            except (TypeError, ValueError, IndexError):
                return None
            if first not in top_two:
                continue
        items.append(item)
    plan["items"] = items
    unified["receiptSha256"] = _canonical_receipt(unified)

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
        "kind": "ticket-r24-upgrade",
        "reason": "ticket-r24-upgrade",
        "revisedAt": captured,
        "revisionCount": (prev_count if isinstance(prev_count, int)
                          else 0) + 1,
        "previousReceiptSha256": info.get("receipt")
        or previous.get("receiptSha256"),
        "previousAbilityLane": info.get("previousAbilityLane"),
        "abilityLane": info.get("previousAbilityLane"),
        "note": ("one-time ticket-R24 upgrade (user order "
                 "2026-11-08): the production trifecta "
                 "recommendation switched from formation B (win "
                 "leg = mark ranks 1-3, 36 points) to R24 (win "
                 "leg = mark ranks 1-2, 24 points); probabilities, "
                 "marks and every other ticket kind are the stored "
                 "ones, only the trifecta recommendation was "
                 "narrowed to the R24 subset of the stored "
                 "combinations"),
    }
    meta["rewritePublish"] = marker
    new["preparedMeta"] = meta
    return new, unified["receiptSha256"]


def _ticket_pool4_upgrade_info(old: dict, now: datetime) -> dict | None:
    """Facts for the one-time ticket-pool4 upgrade of a frozen NAR race.

    The NAR sibling of _ticket_r24_upgrade_info, under the same
    rules. A stored forecast qualifies only when ALL of these hold:

    - the race is NAR (race id prefix "nar-", the same identity
      test the env-repair upgrade uses — JRA races keep R24 and
      never qualify);
    - it carries this lane's publish marker, it has not already
      been re-issued by this upgrade (exactly-once), and its
      marker does not already record the P4A2 ticket formation
      (a race first-published with P4A2 is final);
    - the post is still at least TICKET_POOL4_UPGRADE_MIN_LEAD away;
    - the stored mark order is readable and identical in both
      stored mark blocks, with all five marks present (with fewer
      marks the R24 and P4A2 constructions coincide, so there is
      nothing to narrow);
    - the stored recommended trifecta is still exactly the R24
      construction on those marks (a race already carrying the
      P4A2 subset, a formation-B trifecta — that is the R24
      upgrade's input, handled by its own step first — or anything
      else, is left alone: the upgrade narrows R24 to P4A2 and
      invents nothing).

    Anything unreadable simply does not qualify; the caller keeps
    the frozen forecast (fail-closed).
    """
    race_id = str(old.get("id") or "")
    if not race_id.startswith("nar-"):
        return None
    marker = (old.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    revision = marker.get("revision")
    if isinstance(revision, dict) and (
            revision.get("kind") == "ticket-pool4-upgrade"
            or revision.get("reason") == "ticket-pool4-upgrade"):
        return None
    formation = marker.get("ticketFormation")
    if isinstance(formation, dict) and (
            formation.get("formation") == NAR_TRIFECTA_FORMATION):
        return None
    post = _post_at(old)
    if post is None or post - now < TICKET_POOL4_UPGRADE_MIN_LEAD:
        return None
    unified = old.get("unifiedForecast")
    if not isinstance(unified, dict):
        return None
    if not isinstance(unified.get("ticketPlan"), dict):
        return None
    mark_order = _stored_mark_order(old)
    if mark_order is None or len(mark_order) < 5:
        return None
    from rewrite.analysis.tickets import (
        formation_pool4_axis2_selections, formation_r24_selections)
    trifecta = None
    for entry in old.get("recommendedBets") or []:
        if isinstance(entry, dict) and entry.get("kind") == "3連単":
            trifecta = entry
            break
    if trifecta is None:
        return None
    try:
        stored = {tuple(int(n) for n in combo)
                  for combo in trifecta.get("combos") or []}
    except (TypeError, ValueError):
        return None
    if stored == set(formation_pool4_axis2_selections(mark_order)):
        return None  # already P4A2: final
    if stored != set(formation_r24_selections(mark_order)):
        return None  # not the R24 construction: do not guess
    return {"publishedAt": marker.get("publishedAt"),
            "firstPublishedAt": marker.get("firstPublishedAt"),
            "previousAbilityLane": marker.get("abilityLane"),
            "reason": "ticket-pool4-upgrade",
            "markOrder": mark_order}


def _apply_ticket_pool4_upgrade(old: dict, info: dict, captured: str):
    """Build the ticket-pool4 upgrade re-issue of a frozen NAR forecast.

    Surgical by construction, exactly like _apply_ticket_r24_upgrade:
    the stored forecast — probabilities, marks, diagnosis, odds, EV
    blocks and every non-trifecta ticket kind — is kept exactly as
    published. Only the trifecta recommendation is narrowed: in the
    grouped recommendedBets (top level, and the prediction block's
    mirror, which the publisher always writes identical to it) every
    stored combination carrying a leg outside the top four marks is
    dropped (the fifth mark, ☆, was the only such leg in an R24
    combination), and in the unified ticket plan the 3連単 items are
    filtered the same way. The result must equal the canonical P4A2
    construction on the stored marks exactly, or the upgrade aborts
    (returns None; the caller keeps the frozen forecast). The
    receipt is re-sealed over the modified unified forecast and the
    revision is stamped kind "ticket-pool4-upgrade" with the first
    publication time preserved; the marker also gains the
    ticketFormation entry fresh NAR publications carry.
    """
    import copy

    from rewrite.analysis.tickets import formation_pool4_axis2_selections

    mark_order = info["markOrder"]
    leg_pool = set(mark_order[:4])
    expected = set(formation_pool4_axis2_selections(mark_order))

    def _narrow(bets):
        if not isinstance(bets, list):
            return None
        out = []
        for entry in bets:
            if not isinstance(entry, dict):
                return None
            entry = copy.deepcopy(entry)
            if entry.get("kind") == "3連単":
                try:
                    kept = [list(combo) for combo in entry.get("combos") or []
                            if all(int(n) in leg_pool for n in combo)]
                    kept_set = {tuple(int(n) for n in combo)
                                for combo in kept}
                except (TypeError, ValueError, IndexError):
                    return None
                if kept_set != expected:
                    return None
                entry["combos"] = kept
                entry["points"] = len(kept)
            out.append(entry)
        return out

    new = copy.deepcopy(old)
    narrowed = _narrow(new.get("recommendedBets"))
    if narrowed is None:
        return None
    new["recommendedBets"] = narrowed
    prediction = new.get("prediction")
    if isinstance(prediction, dict):
        # The publisher writes prediction.recommendedBets identical
        # to the top-level list; the API projection strips it from
        # the read, so restore the mirror from the narrowed list
        # rather than dropping the stored block.
        prediction["recommendedBets"] = copy.deepcopy(narrowed)
    unified = new.get("unifiedForecast")
    if not isinstance(unified, dict):
        return None
    plan = unified.get("ticketPlan")
    if not isinstance(plan, dict) or not isinstance(plan.get("items"), list):
        return None
    items = []
    for item in plan["items"]:
        if isinstance(item, dict) and item.get("kind") == "3連単":
            combo = item.get("combo") or []
            try:
                legs = [int(n) for n in combo]
            except (TypeError, ValueError, IndexError):
                return None
            if not all(n in leg_pool for n in legs):
                continue
        items.append(item)
    plan["items"] = items
    unified["receiptSha256"] = _canonical_receipt(unified)

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
    marker["ticketFormation"] = {
        "formation": NAR_TRIFECTA_FORMATION, "scope": "nar-only"}
    marker["revision"] = {
        "kind": "ticket-pool4-upgrade",
        "reason": "ticket-pool4-upgrade",
        "revisedAt": captured,
        "revisionCount": (prev_count if isinstance(prev_count, int)
                          else 0) + 1,
        "previousReceiptSha256": info.get("receipt")
        or previous.get("receiptSha256"),
        "previousAbilityLane": info.get("previousAbilityLane"),
        "abilityLane": info.get("previousAbilityLane"),
        "note": ("one-time ticket-pool4 upgrade (user order "
                 "2026-11-12): the NAR trifecta recommendation "
                 "switched from R24 (leg pool = mark ranks 1-5, "
                 "24 points) to pool4-axis2 (leg pool = mark "
                 "ranks 1-4, win leg = mark ranks 1-2, 12 "
                 "points); probabilities, marks and every other "
                 "ticket kind are the stored ones, only the "
                 "trifecta recommendation was narrowed to the "
                 "pool4-axis2 subset of the stored combinations"),
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


def _projection_tombstone(old: dict) -> bool:
    """Whether this read carries the API worker's projection tombstone.

    The kraiz-api GET projection (publicRace / authorizedStage64)
    honours only a stored detail whose top-level predictionStatus is
    exactly "ready". Anything else — including a complete, valid
    publication of this lane whose stored status reads
    "unified-reference-ready" (the Python delivery projection's
    vocabulary, carried into stored details by prepared-detail
    writes) — is served as predictionStatus "disabled" /
    predictionModelVersion "arvexq-prediction-removed" with the
    prediction and predictionMarks blocks stripped. The lane marker
    (preparedMeta.rewritePublish) and the unified forecast pass
    through that projection untouched, so a tombstoned read can
    still be verified against them; the two top-level status fields
    cannot — they are the projection's values, not the stored
    detail's.
    """
    return (old.get("predictionStatus") == "disabled"
            and old.get("predictionModelVersion")
            == "arvexq-prediction-removed")


def _freeze_decision(old: dict):
    """Classify a stored detail against this lane's frozen publication.

    Returns None when the race was never published ready by this lane
    (normal first publication), ("frozen", receipt) when the stored
    ready forecast must be left byte-stable, or ("reissue", info)
    when the active roster changed since the frozen publication.
    A detail that carries this lane's ready markers but whose frozen
    state cannot be read consistently raises ValueError; the caller
    fails closed (skip, no overwrite) rather than guess.

    A read carrying the API projection's tombstone (see
    _projection_tombstone) is classified on the lane marker and the
    unified forecast alone: the projection rewrites the top-level
    status fields and strips blocks, but the marker receipt must
    still equal the unified forecast's receipt and the receipt
    roster must still match the active roster before the race may
    be treated as this lane's frozen publication.
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
    if not _projection_tombstone(old):
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


def _build_mass_feature_archive(old: dict):
    """Freeze the pre-off mass-feature archive for a publication.

    Returns (archive, status): archive is the lossless transport
    envelope produced by mass_feature_transport.archive_snapshot
    (the exact producer pack_mass_detail uses) or None; status is a
    small dict describing the outcome for the caller to stamp/count.

    Why this exists (2026-11-11): the legacy persistence path froze
    a mass-feature snapshot whenever a detail carrying a
    preRacePrediction lock was stored, and protect_sync later packed
    it into massFeatureArchive. This lane — the sole forecast
    producer since the cutover — never carried that lock, so no
    published detail has carried the archive since 2026-10-17 while
    v9b publications only exist from 2026-11-04: the sealed-forecast
    x feature-archive intersection is empty, and no same-race model
    comparison can ever be graded from stored data. Freezing the
    matrix here, from the same pre-off input detail the forecast is
    computed from, restarts that accumulation.

    The feature factory reads only pre-race facts (past runs strictly
    before the race date, entries, and the market as observed in the
    input detail), and the snapshot's featureHash is the origin hash
    the transport re-verifies, so the archive's originHashVerified
    is earned, not asserted. pack_mass_detail itself is not reused:
    it requires a preRacePrediction lock in the detail, and this
    lane's provenance anchor is the sealed publication (receipt +
    lane marker) — fabricating a lock would change other lanes'
    semantics. The archive is research evidence only: it feeds no
    mark, probability, ticket or receipt.

    A failure never blocks publication (the masterAnalysis shadow
    rule); the caller stamps and counts it instead.
    """
    try:
        from arvexq.ingest.banei import is_banei
        if is_banei(old.get("track"), old.get("id")):
            return None, {"status": "excluded-banei"}
        from arvexq.prediction.mass_feature_factory import (
            FEATURE_SCHEMA_VERSION)
        from arvexq.prediction.mass_feature_snapshot import (
            SNAPSHOT_VERSION, build_mass_feature_snapshot)
        from arvexq.prediction.mass_feature_transport import (
            archive_snapshot)
        snapshot = build_mass_feature_snapshot(old)
        archive = archive_snapshot(
            snapshot,
            race_id=str(old.get("id") or ""),
            race_date=str(old.get("date") or ""))
        return archive, {
            "status": "attached",
            "featureHash": archive["featureHash"],
            "rawBytes": archive["rawBytes"],
            "payloadBytes": len(archive["payload"]),
            "horseCount": archive["horseCount"],
            "schemaVersion": FEATURE_SCHEMA_VERSION,
            "snapshotVersion": SNAPSHOT_VERSION,
        }
    except Exception as exc:
        return None, {"status": "error",
                      "error": f"{type(exc).__name__}: {exc}"}


def build_publish_detail(old_detail: dict, summary: dict, now: datetime):
    """Return (new_detail, receipt) or (None, reason) when not publishable."""
    from arvexq.ingest.full_snapshot_codec import unpack_detail
    from arvexq.prediction.unified_product import race_family

    old = unpack_detail(old_detail)
    # Race binding: the summary supplies the race identity (normalize
    # prefers it) while the runners come from the detail. The caller
    # fetched both by the same race id, but assert the merge point
    # itself: a summary/detail pair that names different races must
    # never be published as one race's forecast.
    summary_id = str(summary.get("race_id") or summary.get("id") or "")
    detail_id = str(old.get("id") or "")
    if summary_id and detail_id and summary_id != detail_id:
        return None, (f"identity mismatch: summary {summary_id} vs "
                      f"detail {detail_id}; not publishing")
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
    env_repair_upgrade = None
    decay_upgrade = None
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
                # _blend_upgrade_info); a v9b forecast whose
                # probabilities were computed while the NAR surface
                # builders served "" is re-issued once from the
                # repaired payload (see _env_repair_upgrade_info —
                # a full rebuild, so it precedes the surgical
                # upgrades below; a blend upgrade in the same pass
                # already rebuilds from the repaired payload and
                # subsumes it); a NAR forecast frozen WITHOUT the
                # F1 evidence decay only because it was first
                # published before the decay reached this lane is
                # re-issued once from the current payload (see
                # _nar_decay_upgrade_info — also a full rebuild, so
                # it too precedes the surgical upgrades); a v9b forecast frozen
                # WITHOUT placeExpectedValues only because the
                # upstream sync did not carry place odds yet is
                # re-issued once when they complete (see
                # _place_ev_upgrade_info — surgical, it applies on
                # top of the freshest stored forecast and never
                # undoes a blend upgrade). Anything else stays
                # frozen.
                blend_upgrade = _blend_upgrade_info(old, now)
                if blend_upgrade is None:
                    env_repair_upgrade = _env_repair_upgrade_info(
                        old, now, summary.get("surface"))
                if (blend_upgrade is None
                        and env_repair_upgrade is None):
                    decay_upgrade = _nar_decay_upgrade_info(old, now)
                if (blend_upgrade is None
                        and env_repair_upgrade is None
                        and decay_upgrade is None):
                    place_ev_upgrade = _place_ev_upgrade_info(old, now)
                    if place_ev_upgrade is None:
                        # The last freeze exceptions, both surgical
                        # ticket upgrades that apply on top of the
                        # freshest stored forecast and never undo a
                        # blend or place-EV upgrade: a forecast
                        # frozen with the formation-B trifecta is
                        # re-issued once with the recommendation
                        # narrowed to R24 (see
                        # _ticket_r24_upgrade_info); a NAR forecast
                        # frozen with the R24 trifecta is likewise
                        # re-issued once narrowed to pool4-axis2
                        # (see _ticket_pool4_upgrade_info). A race
                        # carrying the B form takes the R24 step
                        # first and the pool4 step on a later pass.
                        # Anything else stays frozen.
                        ticket_upgrade = _ticket_r24_upgrade_info(old, now)
                        upgrade_apply = _apply_ticket_r24_upgrade
                        upgrade_label = "ticket-R24"
                        if ticket_upgrade is None:
                            ticket_upgrade = _ticket_pool4_upgrade_info(
                                old, now)
                            upgrade_apply = _apply_ticket_pool4_upgrade
                            upgrade_label = "ticket-pool4"
                        if ticket_upgrade is None:
                            return None, (
                                f"frozen: already published ready "
                                f"(receipt {str(freeze[1])[:12]}…); "
                                f"roster unchanged")
                        if _projection_tombstone(old):
                            # The surgical ticket upgrade rebuilds
                            # the recommendation blocks from the
                            # stored detail; through the API
                            # projection the prediction blocks are
                            # stripped, so applying it from this
                            # read could damage the publication.
                            # Keep the frozen forecast and leave
                            # the upgrade pending for a read that
                            # carries the stored blocks.
                            return None, (
                                f"frozen: already published ready "
                                f"(receipt {str(freeze[1])[:12]}…); "
                                f"{upgrade_label} upgrade deferred: the "
                                f"API projection does not carry the "
                                f"stored prediction blocks for this "
                                f"race")
                        ticket_upgrade["receipt"] = freeze[1]
                        upgraded = upgrade_apply(
                            old, ticket_upgrade,
                            now.isoformat(timespec="seconds"))
                        if upgraded is None:
                            return None, (
                                f"frozen: already published ready "
                                f"(receipt {str(freeze[1])[:12]}…); "
                                f"{upgrade_label} upgrade could not be "
                                f"computed from the stored product; "
                                f"keeping the frozen forecast")
                        return upgraded
                    if _projection_tombstone(old):
                        # The surgical place-EV upgrade rebuilds the
                        # marks and prediction blocks from the stored
                        # detail; through the API projection those
                        # blocks are stripped, so applying it from
                        # this read would damage the publication.
                        # Keep the frozen forecast and leave the
                        # upgrade pending for a read that carries
                        # the stored blocks.
                        return None, (
                            f"frozen: already published ready "
                            f"(receipt {str(freeze[1])[:12]}…); "
                            f"place-EV upgrade deferred: the API "
                            f"projection does not carry the stored "
                            f"prediction blocks for this race")
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
                if blend_upgrade is not None:
                    blend_upgrade["receipt"] = freeze[1]
                elif env_repair_upgrade is not None:
                    env_repair_upgrade["receipt"] = freeze[1]
                elif decay_upgrade is not None:
                    decay_upgrade["receipt"] = freeze[1]
        else:
            reissue = freeze[1]
    race = normalize_race(summary, old, source="production-api-readback")
    race_date = str(old.get("date") or race.date or "")
    segment = race.segment.value
    forecast = None
    used_v8 = False
    nar_evidence_decay = False
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
                v8_forecast = forecast_race_v8(
                    race, extras,
                    evidence_decay_k=(NAR_EVIDENCE_DECAY_K
                                      if segment == "nar" else None))
                if v8_forecast.status == "ok":
                    forecast = v8_forecast
                    used_v8 = True
                    nar_evidence_decay = segment == "nar"
                else:
                    v8_fallback_status = v8_forecast.status
        elif reissue is None and lane_upgrade is None \
                and blend_upgrade is None \
                and env_repair_upgrade is None \
                and decay_upgrade is None:
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
    if env_repair_upgrade is not None and not used_v9b:
        # The repair was attempted but the rebuild did not land
        # on the v9b lane (the v8 forecast did not come back ok,
        # or the v9b transform passed through): re-issuing now
        # would move the race onto another lane or an uncalibrated
        # vector, which the repair never justifies. Keep the
        # frozen forecast byte-stable; the qualification stands
        # down because this branch is dated to 2026-11-09.
        return None, (f"frozen: already published ready "
                      f"(receipt {str(env_repair_upgrade['receipt'])[:12]}…); "
                      f"env-repair rebuild did not land on the "
                      f"v9b lane; keeping the frozen forecast")
    if decay_upgrade is not None and not nar_evidence_decay:
        # The decay upgrade was attempted but the rebuild did not
        # land on the decayed v8 layer (the v8 forecast did not
        # come back ok, so the race fell back to the v1 lane, or
        # the segment no longer classifies as NAR): re-issuing now
        # would rewrite a forecast on sale WITHOUT the one change
        # that justifies it. Keep the frozen forecast byte-stable;
        # a later cycle can retry while the qualification holds.
        return None, (f"frozen: already published ready "
                      f"(receipt {str(decay_upgrade['receipt'])[:12]}…); "
                      f"nar-decay rebuild did not land on the "
                      f"decayed v8 layer; keeping the frozen forecast")
    # Trifecta R24 (adopted 2026-11-08 by user order after the
    # screen on the graded 194 production races: B ROI 0.7230 ->
    # R24 0.9055): formation B's mark-order skeleton with the win
    # leg narrowed to mark ranks 1-2 (24 points). Formation B was
    # the production formation from 2026-10-31 to this switch;
    # races already frozen with the B-form trifecta are narrowed
    # by the one-time ticket-r24-upgrade above. Probabilities,
    # marks and every other ticket kind are unchanged; the
    # sealing lane keeps the legacy formation and lane v34 keeps
    # B36 as its control arm.
    # Since 2026-11-12 (user order, see NAR_TRIFECTA_FORMATION
    # above) the formation is segment-dependent: NAR builds
    # pool4-axis2 (P4A2, 12 points) and JRA keeps R24. Races
    # already frozen with the R24 trifecta on the NAR side are
    # narrowed by the one-time ticket-pool4-upgrade above.
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
    tickets = generate_tickets(
        forecast, win_odds,
        calibration_validated=False,
        trifecta_formation=(NAR_TRIFECTA_FORMATION
                            if segment == "nar" else "R24"),
        place_odds=place_odds)
    # Evaluate the user's 18-factor master specification on the EXACT same
    # pre-off race and incumbent forecast. Shadow output is advisory only:
    # production v9b marks, R24 tickets, receipts, and frozen history remain
    # authoritative until paired forward accuracy / ROI is validated.
    master_analysis = {"version": "master-18-factor-shadow-v1",
                       "status": "unavailable"}
    try:
        master_forecast, master_audit = master_candidate(race, forecast)
        master_plans = ticket_styles(master_forecast, master_audit)
        master_analysis = {
            "version": master_audit["version"],
            "status": master_audit["status"],
            "probabilityStatus": master_audit["probabilityStatus"],
            "validated": False,
            "evidenceConfidence": master_audit.get("evidenceConfidence"),
            "marketStatus": master_audit.get("marketStatus"),
            "pace": master_audit["pace"],
            "runners": [
                {
                    "horseNumber": item["horseNumber"],
                    "score100": item["score100"],
                    "coveragePoints": item["coveragePoints"],
                    "evidenceRuns": item["evidenceRuns"],
                    "categories": {
                        k: v["earned"] for k, v in item["categories"].items()
                    },
                    "missingCategories": item["missingCategories"],
                    "mark": item.get("mark"),
                    "pWin": item.get("pWin"),
                    "pTop3": item.get("pTop3"),
                    "marketRank": item.get("marketRank"),
                    "popularRisk": item.get("popularRisk"),
                    "valueHypothesis": item.get("valueHypothesis", False),
                }
                for item in master_audit["runners"]
            ],
            "ticketStyles": master_plans,
        }
    except Exception as exc:
        # A shadow experiment is never allowed to block pre-off publication.
        master_analysis["status"] = "shadow-evaluation-error"
        master_analysis["errorType"] = type(exc).__name__
    captured = now.isoformat(timespec="seconds")
    master_analysis["capturedAt"] = captured
    master_analysis["contentSha256"] = sha256(json.dumps(
        master_analysis, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    # Freeze the pre-off feature matrix beside the forecast (see
    # _build_mass_feature_archive): built from the same input detail
    # the forecast was computed from, attached to the same published
    # detail, so the sealed v9b product and its feature evidence can
    # later be graded on the SAME race. Research evidence only.
    mass_archive, mass_archive_status = _build_mass_feature_archive(old)
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
        # hash so the label is part of the verified product. A NAR
        # race whose ability scores carry the F1 evidence decay is
        # labelled as such (see NAR_DECAY_* above).
        unified["abilityModelVersion"] = (
            NAR_DECAY_V9B_ABILITY_MODEL_VERSION if nar_evidence_decay
            else V9B_ABILITY_MODEL_VERSION)
        unified["probabilityStatus"] = V9B_PROBABILITY_STATUS
    elif used_v8:
        # Per-race honest labeling: this forecast's ability layer is
        # the adopted v8 candidate, not the v1 prior. Stamped before
        # the receipt hash so the label is part of the verified
        # product.
        unified["abilityModelVersion"] = (
            NAR_DECAY_V8_ABILITY_MODEL_VERSION if nar_evidence_decay
            else V8_ABILITY_MODEL_VERSION)
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
    # Namespaced research-only sidecar. No prediction marks / tickets change.
    new["masterAnalysis"] = master_analysis
    if mass_archive is not None:
        # Frozen pre-off feature evidence, packed by the transport
        # into its lossless archive envelope. The raw snapshot is
        # not stored alongside: the archive restores it byte-exactly
        # (mass_feature_transport.restore_snapshot), which is the
        # form the MotherDuck export and the ranking challenger read.
        new["massFeatureArchive"] = mass_archive
        new["massFeatureHash"] = mass_archive["featureHash"]
        new["massFeatureSchemaVersion"] = mass_archive_status[
            "schemaVersion"]
        new["massFeatureSnapshotVersion"] = mass_archive_status[
            "snapshotVersion"]
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
    if nar_evidence_decay:
        # F1 evidence decay (NAR only): the ability scores of this
        # publication were shrunk toward the scored-field mean by
        # evidence reliability n / (n + k) inside the v8 layer. The
        # sealed product's abilityModelVersion carries the matching
        # "-nar-decay2" suffix; this marker entry is the lane-side
        # record of the same fact.
        meta["rewritePublish"]["evidenceDecay"] = {
            "type": "evidence-runs-shrinkage",
            "k": NAR_EVIDENCE_DECAY_K,
            "scope": "nar-only"}
    if segment == "nar":
        # Ticket pool4-axis2 (NAR only, 2026-11-12): this
        # publication's trifecta was built with the P4A2 formation
        # (leg pool = mark ranks 1-4, win leg = mark ranks 1-2)
        # instead of R24; JRA publications keep R24 and carry no
        # such entry, exactly as before. The one-time
        # ticket-pool4-upgrade stamps the same entry when it
        # narrows a frozen NAR publication.
        meta["rewritePublish"]["ticketFormation"] = {
            "formation": NAR_TRIFECTA_FORMATION, "scope": "nar-only"}
    if v9b_passthrough is not None:
        meta["rewritePublish"]["v9bPassthrough"] = (
            f"v9b post-processing passed through: {v9b_passthrough}; "
            f"v8 probabilities kept for this race")
    if v8_fallback_status is not None:
        meta["rewritePublish"]["v8Fallback"] = (
            f"v8 forecast not ok: {v8_fallback_status}; v1 lane used")
    if mass_archive_status.get("status") == "error":
        # The feature archive is research evidence; publication
        # proceeds without it, but the failure stays on the lane
        # marker and in the run counts instead of vanishing silently.
        meta["rewritePublish"]["massFeatureArchiveError"] = (
            mass_archive_status["error"])
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
    if env_repair_upgrade is not None:
        # Env-repair re-issue of a frozen forecast: the roster and
        # the lane are unchanged — the only change is that the
        # forecast is recomputed from a payload whose race surface
        # is real, where the stored probabilities were computed
        # while the builders served "" and the surface suitability
        # feature was dead. Same audit chain as the other
        # re-issues: the first publication time is preserved, the
        # previous receipt is recorded, and the revision also
        # carries the surface the rebuild used and the time the
        # stored probabilities dated from, so the repair stays
        # auditable per race. The exactly-once property is the
        # revision kind itself (see _env_repair_upgrade_info).
        previous = (old.get("preparedMeta") or {}).get("rewritePublish") or {}
        prev_revision = previous.get("revision")
        prev_count = (prev_revision.get("revisionCount")
                      if isinstance(prev_revision, dict) else None)
        meta["rewritePublish"]["firstPublishedAt"] = (
            env_repair_upgrade.get("firstPublishedAt")
            or env_repair_upgrade.get("publishedAt") or captured)
        meta["rewritePublish"]["revision"] = {
            "kind": "env-repair-upgrade",
            "reason": "env-repair-upgrade",
            "revisedAt": captured,
            "revisionCount": (prev_count if isinstance(prev_count, int)
                              else 0) + 1,
            "previousReceiptSha256": env_repair_upgrade["receipt"],
            "previousAbilityLane": V9B_LANE,
            "abilityLane": V9B_LANE,
            "surface": env_repair_upgrade["surface"],
            "probabilityComputedAt":
                env_repair_upgrade["probabilityComputedAt"],
            **({"marksResync": True}
               if env_repair_upgrade.get("marksResync") else {}),
            "note": ("one-time env-repair re-issue (user "
                     "instruction 2026-11-09): the stored "
                     "probabilities were computed while the NAR "
                     "surface builders served an empty surface "
                     "(fixed in main 2e01ec9e), so the surface "
                     "suitability feature was dead for every "
                     "runner; the forecast is recomputed from "
                     "the current payload, which carries the "
                     "stored surface"),
        }
    if decay_upgrade is not None:
        # NAR evidence-decay re-issue of a frozen forecast: the
        # roster and the lane are unchanged — the only change is
        # that the ability scores are recomputed with the F1
        # evidence decay this race predates. Same audit chain as
        # the other re-issues: the first publication time is
        # preserved and the previous receipt is recorded. The
        # exactly-once property is structural: the rebuilt product
        # carries the decayed abilityModelVersion, so
        # _nar_decay_upgrade_info can never qualify this race again.
        previous = (old.get("preparedMeta") or {}).get("rewritePublish") or {}
        prev_revision = previous.get("revision")
        prev_count = (prev_revision.get("revisionCount")
                      if isinstance(prev_revision, dict) else None)
        meta["rewritePublish"]["firstPublishedAt"] = (
            decay_upgrade.get("firstPublishedAt")
            or decay_upgrade.get("publishedAt") or captured)
        meta["rewritePublish"]["revision"] = {
            "kind": "nar-decay-upgrade",
            "reason": "nar-decay-upgrade",
            "revisedAt": captured,
            "revisionCount": (prev_count if isinstance(prev_count, int)
                              else 0) + 1,
            "previousReceiptSha256": decay_upgrade["receipt"],
            "previousAbilityLane": V9B_LANE,
            "abilityLane": V9B_LANE,
            "note": (f"one-time NAR evidence-decay adoption "
                     f"(user instruction 2026-11-12): this race "
                     f"was first published before the F1 evidence "
                     f"decay reached the production lane, so its "
                     f"ability scores were computed undamped; the "
                     f"forecast is recomputed with the decay "
                     f"(runs-k{NAR_EVIDENCE_DECAY_K:g}, NAR only) "
                     f"while the race is still pre-post"),
        }
    new["preparedMeta"] = meta
    return new, unified["receiptSha256"]


def publish_date(date: str, token: str | None, dry_run: bool) -> dict:
    from arvexq.ingest.banei import is_banei
    from arvexq.ingest.full_snapshot_codec import pack_detail, unpack_detail
    from arvexq.prediction.unified_product import verified as verified_unified

    protect_detail = _load_protect()
    listing = _get(f"/api/races?date={date}")
    summaries = listing.get("races") or listing.get("summaries") or []
    counts = {"races": len(summaries), "published": 0, "skipped": 0,
              "frozen": 0, "deferred": 0, "reissued": 0, "failed": 0,
              "receiptMismatch": 0,
              "massArchived": 0, "massArchiveFailed": 0}
    for summary in summaries:
        race_id = summary.get("race_id") or summary.get("id")
        if not race_id or is_banei(summary.get("track"), race_id):
            # Banei is excluded on every route via the shared test;
            # the race-id check fires even when the track is missing
            # (the old track-only check let those races through).
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
            if isinstance(new.get("massFeatureArchive"), dict):
                counts["massArchived"] += 1
            else:
                # Frozen/skipped races returned above never reach
                # here; a built publication without its feature
                # archive is a research-evidence gap for this race
                # and is named, never silently absorbed.
                counts["massArchiveFailed"] += 1
                mass_err = ((new.get("preparedMeta") or {})
                            .get("rewritePublish") or {}
                            ).get("massFeatureArchiveError")
                print(f"MASS-ARCHIVE-SKIP {race_id}: "
                      f"{mass_err or 'archive not attached'}")
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
            _sidecar_ok, _sidecar_reason = (True, "not-surgical")
            if (revision is not None
                    and (revision.get("kind") or revision.get("reason"))
                    in SURGICAL_TICKET_REVISION_KINDS):
                _sidecar_ok, _sidecar_reason = \
                    _restore_pristine_sidecar(new, token)
            if not _sidecar_ok:
                # The surgical re-issue inherits its sidecar from
                # the projected read, whose signed bytes the
                # projection does not preserve; without the
                # pristine stored sidecar protect_detail would
                # reject the write. Fail closed (the frozen
                # forecast stays; a later cycle retries).
                counts["failed"] += 1
                print(f"FAIL {race_id}: pristine masterAnalysis "
                      f"restore failed ({_sidecar_reason}); "
                      f"keeping the frozen forecast")
                continue
            final = protect_detail(old_raw, new)
            # The self-verify above ran on the pre-protection product,
            # but protect_detail may restore or merge stored blocks,
            # and the sync worker re-serializes values afterwards.
            # The 2026-11-11 audit found 256 stored v9b receipts whose
            # CONTENT no longer re-hashes to the sealed receipt (every
            # re-sealed upgrade verifies; first publications stored
            # after these later transforms often do not). Verify the
            # exact protected product that is about to be posted, and
            # fail closed instead of storing an unverifiable receipt.
            final_detail = (unpack_detail(final)
                            if isinstance(final, dict)
                            and "arvexqFullPayload" in final else final)
            protected_check = verified_unified(dict(
                unpack_detail(old_raw),
                unifiedForecast=final_detail.get("unifiedForecast")))
            if protected_check is None:
                counts["failed"] += 1
                counts["receiptMismatch"] += 1
                print(f"FAIL {race_id}: protected product does not "
                      "self-verify (receipt-content-mismatch)")
                continue
            if isinstance(old_raw, dict) and "arvexqFullPayload" in old_raw:
                final = pack_detail(final)
            result = _post_sync(final, token)
            if not result.get("ok"):
                counts["failed"] += 1
                print(f"FAIL {race_id}: sync rejected: {result}")
                continue
            back = _get("/api/race/" + urllib.parse.quote(str(race_id), safe=""))
            back_detail = back.get("detail") or {}
            stored = back_detail.get("unifiedForecast") or {}
            if stored.get("receiptSha256") != receipt:
                counts["failed"] += 1
                counts["receiptMismatch"] += 1
                print(f"FAIL {race_id}: read-back receipt mismatch")
                continue
            # The string check above cannot detect content drift:
            # the receipt string is copied verbatim even when a later
            # transform changed the sealed values (the 256-ticket
            # failure mode). Re-verify the stored product's content
            # against its own receipt before calling this published.
            if verified_unified(back_detail) is None:
                counts["failed"] += 1
                counts["receiptMismatch"] += 1
                print(f"FAIL {race_id}: read-back content does not "
                      "verify (receipt-content-mismatch)")
                continue
            # The receipt covers only the unified product. The stored
            # detail also carries predictionMarks (what the entry list
            # renders), and the blend-upgrade reissues of 2026-11-07/08
            # stored details whose predictionMarks still named the
            # first publication's horses beside the reissue's
            # unifiedForecast — two different ◎ for one race, invisible
            # to the receipt check. Verify the marks blocks agree.
            def _marks_of(entries, *keys):
                out = {}
                for e in entries or []:
                    if not isinstance(e, dict):
                        continue
                    label = next((e.get(k) for k in keys if e.get(k)), None)
                    if label:
                        out[str(label)] = e.get("horseNumber")
                return out
            built_pm = _marks_of(new.get("predictionMarks"), "mark")
            stored_pm = _marks_of(back_detail.get("predictionMarks"), "mark")
            stored_uf = _marks_of(stored.get("marks"), "markSymbol", "mark")
            if (len(built_pm) == 5 and stored_pm != built_pm) or (
                    len(stored_uf) == 5 and stored_pm != stored_uf):
                counts["failed"] += 1
                print(f"FAIL {race_id}: read-back marks mismatch "
                      f"(stored predictionMarks {stored_pm} vs built "
                      f"{built_pm} / stored unified {stored_uf})")
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

# Cycle trigger 2026-11-09 15:20 JST: give the env-repair
# marks-resync branch another evaluation while Nagoya 7R is
# still outside its 15-minute lead guard (post 16:05).
