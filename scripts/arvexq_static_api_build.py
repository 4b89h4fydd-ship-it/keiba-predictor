"""Build same-origin static JSON packs that mirror the public read API.

The app historically read everything from the D1-backed Worker API
(``/api/day``, ``/api/race/<id>?view=display``).  That Worker has a hard
daily request ceiling, so the read path is being moved to static files
generated from the very payloads the sync/publish lanes already build:

* ``day/<date>.json``       -- body equivalent of ``GET /api/day?date=D&details=0``
* ``race/<race_id>.json``   -- body equivalent of ``GET /api/race/<id>?view=display``
* ``index.json``            -- manifest of generated dates
* ``day-full/<date>.json``  -- body equivalent of ``GET /api/day?date=D``
  (only with ``--with-day-full``; a full day is ~35MB, above the Workers
  Assets per-file limit, so it is a local/audit artifact, never deployed)

A day's race packs are ~30MB in git, so ``--prune-days N`` drops packs
older than N days (counted from the built date) out of the tree; the app
falls back to the API / static racecards for pruned dates.

Accepted inputs (auto-detected):

* sync payload   -- ``{"summaries": [...], "details": [...], "odds_current": [...]}``
  (the POST /api/sync body the lanes build, e.g. prefetch-payload.json)
* official snapshot -- ``{"results": [{"id": ..., "detail": <GET /api/race response>}]}``
  (the auto-publish official snapshot format)
* day response   -- ``{"races": [...], "details": [...]}`` (full /api/day body)

With ``--fetch-date`` the payload is instead read back from the API the
same way the posting scripts do (day listing + one GET per race).  That
mode is transitional: it lets a standalone workflow regenerate the packs
without lane changes, and it fails soft (exit 2, nothing written) while
the API is unavailable so the last good packs stay deployed.

Forecast carry-over guard: a full build regenerates details from the
analyzed prefetch payload, whose sealed originals record prediction /
bet absent for every race, so the build alone would strip the sealed
forecast blocks of every race an earlier run published — and the
post-build merge only re-overlays the races the CURRENT run
(re)published, leaving earlier-published (frozen) races stripped
(2026-11-24 pack incident: 24 frozen races + 1 resulted race lost
their blocks while the lane counted them published).  Before writing,
``carry_over_forecast_blocks`` grafts the sealed forecast blocks from
the existing pack onto any incoming forecast-less detail for the same
race.  Nothing is invented: a race with no published pack keeps its
incoming detail untouched.

Day-status carry-over guard: lane payload summaries are built
before the races run and carry no ``raceStatus``, so a full build
rewrote every day row's status to "" — erasing the 確定/速報 the
result lane had already published until the next result merge
restored it.  ``carry_over_day_statuses`` heals an empty incoming
status from the race's own existing day pack; a non-empty incoming
status always wins.

Research evidence carry-over guard: the observed mineta/margin
evidence (``horses[].researchEvidence``, attached by the prefetch
analyze stage) reaches a lane payload only when that stage decorated
the race in that run.  On the retired D1 path the stored detail was
protected by ``arvexq_protect_sync``; the pack lanes have no such
guard, so an undecorated full build erased the evidence day after
day (2026-11-22..25) and the app showed every horse as unevaluated.
``carry_over_research_evidence`` applies the same rule as
protect_sync at pack build time: an incoming horse that lacks the
evidence block regains the block from the race's own existing pack;
an incoming value is never replaced, and a race whose pack never
carried evidence is left untouched.

Research evidence self-heal guard: carry-over can only restore what
a race's pack carried before, so a race whose payload arrives
undecorated on every lane (the analyze stage never decorated it, or
never ran for it) still published with every horse unevaluated —
the 2026-11-26 recurrence, where 47 of 48 races had never carried
evidence in any committed pack version.  ``heal_missing_research_
evidence`` therefore runs the analyze stage's own decoration
procedure (margin completion from the stored packs, then
``attach_evidence``) on any detail that still has horses without an
evidence block — or with a block whose items are all unavailable,
which is the same unevaluated state on screen (2026-11-26, Urawa
3R: the one residual horse carried an empty block, so a heal keyed
on missing blocks alone never picked her up) — right before the
packs are written, whichever lane produced the payload.  The
procedure's transitive import closure is stdlib-only (verified
2026-11-26), so the lanes — which run this script with setup-python
only — can import it from the checkout.
The heal is idempotent, never rewrites a block that has available
items, replaces an empty block only when the recompute yields at
least one available item (otherwise the original block is kept
verbatim), and never touches forecast or result content.  Horses
that remain evidence-empty afterwards are reported machine-readably to
``evidence-residual/<date>.json`` next to the packs (plus stdout
and the Actions job summary) instead of passing silently; the file
is written on every build, with an explicit zero count on clean
days.  The build itself never fails on a residual: issuance
continues, but the abnormality is immediately visible.

With ``--merge-existing`` the input model is overlaid on the packs
already in ``--out-dir`` for the same date instead of replacing them.
Delta payloads (the realtime sync lane's ``live-payload.json`` carries
only the races it updated; the rewrite publish lane emits only the
races it published) can therefore refresh their races without shrinking
the day pack to the delta.  Entries present in the input win; entries
absent from it keep their existing pack content.

Banei (Obihiro) races are excluded on every path, matching the API.
Files whose canonical content is unchanged are not rewritten, so
regeneration does not create commit churn.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

VERSION = "arvexq-static-api-v1"
JST = ZoneInfo("Asia/Tokyo")
BANEI_TRACKS = ("帯広", "帯広ば")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_banei(race_id: str, track: str) -> bool:
    return track in BANEI_TRACKS or "帯広" in (race_id or "")


def _day_row_from_db_row(r: dict) -> dict:
    """Replicates worker_default /api/day summary mapping (race_summaries row)."""
    return {
        "id": r.get("race_id"),
        "date": r.get("race_date"),
        "circuit": r.get("circuit"),
        "track": r.get("track"),
        "raceNumber": r.get("race_no"),
        "startTime": r.get("start_time"),
        "scheduledStartTime": r.get("start_time"),
        "title": r.get("title"),
        "surface": r.get("surface"),
        "distance": r.get("distance"),
        "weather": r.get("weather"),
        "condition": r.get("condition"),
        "volatility": {"label": r.get("volatility_label") or "",
                       "score": r.get("volatility_score")},
        "raceStatus": r.get("race_status") or "",
        "updatedAtEpoch": r.get("updated_at"),
    }


def _day_row_from_summary(s: dict) -> dict:
    """Normalizes a lane-built summary object (camelCase or DB-row shape)."""
    if "race_id" in s and "id" not in s:
        return _day_row_from_db_row(s)
    vol = s.get("volatility")
    if not isinstance(vol, dict):
        vol = {"label": s.get("volatility_label") or s.get("volatilityLabel") or "",
               "score": s.get("volatility_score", s.get("volatilityScore"))}
    return {
        "id": s.get("id"),
        "date": s.get("date"),
        "circuit": s.get("circuit"),
        "track": s.get("track"),
        "raceNumber": s.get("raceNumber", s.get("race_no")),
        "startTime": s.get("startTime", s.get("start_time")),
        "scheduledStartTime": s.get("scheduledStartTime", s.get("startTime", s.get("start_time"))),
        "title": s.get("title"),
        "surface": s.get("surface"),
        "distance": s.get("distance"),
        "weather": s.get("weather"),
        "condition": s.get("condition"),
        "volatility": vol,
        "raceStatus": s.get("raceStatus", s.get("race_status")) or "",
        "updatedAtEpoch": s.get("updatedAtEpoch", s.get("updated_at")),
    }


def _sort_key(row: dict):
    return (str(row.get("circuit") or ""), str(row.get("track") or ""),
            int(row.get("raceNumber") or 0))


class DayModel:
    def __init__(self, date: str):
        self.date = date
        self.summaries: dict[str, dict] = {}   # race_id -> day row (camelCase)
        self.details: dict[str, dict] = {}     # race_id -> detail payload
        self.odds: dict[str, list] = {}        # race_id -> odds_current rows
        self.analysis_ready: dict[str, bool] = {}
        self.detail_updated_at: dict[str, Any] = {}
        self.skipped_banei = 0


def _add_detail(model: DayModel, payload: Any, odds=None,
                analysis_ready=None, updated_at=None) -> None:
    if not isinstance(payload, dict):
        return
    rid = str(payload.get("id") or payload.get("race_id") or payload.get("raceId") or "")
    if not rid:
        return
    if _is_banei(rid, str(payload.get("track") or "")):
        model.skipped_banei += 1
        return
    model.details[rid] = payload
    if odds is not None:
        model.odds[rid] = odds
    if analysis_ready is None:
        analysis_ready = bool((payload.get("preparedMeta") or {}).get("diagnosisReady"))
    model.analysis_ready[rid] = bool(analysis_ready)
    if updated_at is not None:
        model.detail_updated_at[rid] = updated_at


def model_from_sync_payload(payload: dict) -> DayModel:
    date = ""
    for s in payload.get("summaries") or []:
        if isinstance(s, dict):
            date = str(s.get("date") or s.get("race_date") or date)
    for d in payload.get("details") or []:
        if isinstance(d, dict) and not date:
            date = str(d.get("date") or "")
    model = DayModel(date)
    for s in payload.get("summaries") or []:
        if not isinstance(s, dict):
            continue
        row = _day_row_from_summary(s)
        rid = str(row.get("id") or "")
        if not rid:
            continue
        if _is_banei(rid, str(row.get("track") or "")):
            model.skipped_banei += 1
            continue
        model.summaries[rid] = row
    odds_rows = payload.get("odds_current") or payload.get("oddsCurrent") or []
    odds_by_id: dict[str, list] = {}
    for o in odds_rows:
        if isinstance(o, dict):
            odds_by_id.setdefault(str(o.get("race_id") or o.get("raceId") or ""), []).append(o)
    for row in payload.get("details") or []:
        if not isinstance(row, dict):
            continue
        # Sync detail rows may wrap the payload ({payload: {...}}) or be the
        # payload itself.  analysis_ready mirrors the /api/sync handler:
        # row.analysis_ready ?? row.analysisReady ?? preparedMeta.diagnosisReady.
        detail = row.get("payload") or row.get("detail") or row
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except Exception:
                continue
        if not isinstance(detail, dict):
            continue
        rid = str(row.get("race_id") or row.get("raceId") or row.get("id")
                  or detail.get("id") or detail.get("race_id") or "")
        ready = row.get("analysis_ready", row.get("analysisReady"))
        if ready is None:
            ready = (detail.get("preparedMeta") or {}).get("diagnosisReady")
        updated = row.get("updated_at", row.get("updatedAt", row.get("updatedAtEpoch")))
        _add_detail(model, detail, odds=odds_by_id.get(rid),
                    analysis_ready=bool(ready), updated_at=updated)
    # Odds rows for races whose detail is not in this payload (the live
    # lane's odds-only updates): keep them on the model so a
    # --merge-existing build can refresh that race's existing pack odds
    # without touching its detail.  Without a detail (and no existing
    # pack to merge into) they are simply never written.
    for rid, rows in odds_by_id.items():
        if rid and rid not in model.details and rid not in model.odds:
            track = str((model.summaries.get(rid) or {}).get("track") or "")
            if not _is_banei(rid, track):
                model.odds[rid] = rows
    return model


def model_from_official_snapshot(payload: dict) -> DayModel:
    model = DayModel(str(payload.get("date") or ""))
    for entry in payload.get("results") or []:
        if not isinstance(entry, dict):
            continue
        resp = entry.get("detail")
        if not isinstance(resp, dict):
            continue
        summary = resp.get("summary")
        if isinstance(summary, dict) and summary.get("race_id"):
            row = _day_row_from_db_row(summary)
            rid = str(row.get("id") or "")
            if _is_banei(rid, str(row.get("track") or "")):
                model.skipped_banei += 1
                continue
            model.summaries[rid] = row
        _add_detail(model, resp.get("detail"), odds=resp.get("odds"),
                    analysis_ready=resp.get("analysis_ready"),
                    updated_at=resp.get("detail_updated_at"))
    if not model.date and model.summaries:
        model.date = str(next(iter(model.summaries.values())).get("date") or "")
    return model


def model_from_day_response(payload: dict) -> DayModel:
    model = DayModel(str(payload.get("date") or ""))
    for s in payload.get("races") or []:
        if not isinstance(s, dict):
            continue
        row = _day_row_from_summary(s)
        rid = str(row.get("id") or "")
        if not rid:
            continue
        if _is_banei(rid, str(row.get("track") or "")):
            model.skipped_banei += 1
            continue
        model.summaries[rid] = row
    for d in payload.get("details") or []:
        _add_detail(model, d)
    return model


def detect_model(payload: dict) -> DayModel:
    if isinstance(payload.get("results"), list) and payload.get("results") and \
            isinstance(payload["results"][0], dict) and "detail" in payload["results"][0]:
        return model_from_official_snapshot(payload)
    if isinstance(payload.get("summaries"), list) or isinstance(payload.get("details"), list) \
            and not isinstance(payload.get("races"), list):
        return model_from_sync_payload(payload)
    if isinstance(payload.get("races"), list):
        return model_from_day_response(payload)
    if isinstance(payload.get("summaries"), list):
        return model_from_sync_payload(payload)
    raise ValueError("unrecognized payload shape: expected sync payload, "
                     "official snapshot, or full /api/day response")


def model_from_existing_packs(out_dir: Path, date: str) -> DayModel:
    """Seeds a model from packs already written under out_dir (the base
    for --merge-existing).  Missing/corrupt files simply yield an
    emptier base; nothing is invented."""
    model = DayModel(date)
    day_path = out_dir / "day" / f"{date}.json"
    try:
        day = json.loads(day_path.read_text(encoding="utf-8"))
    except Exception:
        return model
    race_ids = []
    for s in day.get("races") or []:
        if not isinstance(s, dict):
            continue
        row = _day_row_from_summary(s)
        rid = str(row.get("id") or "")
        if not rid:
            continue
        if _is_banei(rid, str(row.get("track") or "")):
            continue
        model.summaries[rid] = row
        race_ids.append(rid)
    for rid in race_ids:
        try:
            body = json.loads((out_dir / "race" / f"{rid}.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        odds = body.get("odds")
        _add_detail(model, body.get("detail"),
                    odds=odds if isinstance(odds, list) else None,
                    analysis_ready=body.get("analysis_ready"),
                    updated_at=body.get("detail_updated_at"))
    return model


def merge_models(base: DayModel, overlay: DayModel) -> DayModel:
    """Overlay wins per race; races only in base survive unchanged."""
    merged = DayModel(overlay.date or base.date)
    merged.summaries = {**base.summaries, **overlay.summaries}
    merged.details = {**base.details, **overlay.details}
    merged.odds = {**base.odds, **overlay.odds}
    merged.analysis_ready = {**base.analysis_ready, **overlay.analysis_ready}
    merged.detail_updated_at = {**base.detail_updated_at,
                                **overlay.detail_updated_at}
    merged.skipped_banei = base.skipped_banei + overlay.skipped_banei
    return merged


# Sealed forecast blocks a published detail carries (mirrors the
# publish lane's detail shape; cf. scripts/arvexq_sealed_restore.py).
FORECAST_CARRYOVER_KEYS = (
    "unifiedForecast", "prediction", "predictionMarks", "recommendedBets",
    "forecastText", "predictionModelVersion", "preRaceBet",
    "masterAnalysis", "massFeatureArchive", "massFeatureHash",
    "massFeatureSchemaVersion", "massFeatureSnapshotVersion", "biasPace",
)


# predictionStatus values that mark an existing detail as carrying
# the sealed forecast.  Two spellings name the same publication: the
# publish lane's own "ready" and the delivery projection's
# "unified-reference-ready" (arvexq/forecast/publication.py renames
# the status when it serves a verified unified product; app.py and
# scripts/arvexq_protect_sync.py both treat the two as equivalent).
# The result-ingest lane's payload details pass through that
# projection, so its merges rewrite the pack status to
# "unified-reference-ready" while keeping the blocks.  Accepting
# only "ready" here made the NEXT forecast-less build reject those
# packs as a carry-over source and strip their blocks — and once
# stripped, the pack's own "disabled" status disqualified it as a
# source forever (2026-11-24: restore "ready" 12:27 -> projection
# status 14:44 -> stripped 15:23, never healed again; 2026-11-25
# Sonoda 1R: ready 12:44 -> "unified-reference-ready" 12:45 ->
# disabled 14:41).
FORECAST_CARRYOVER_SOURCE_STATUSES = ("ready", "unified-reference-ready")


def _has_forecast(detail: Any) -> bool:
    return isinstance(detail, dict) and isinstance(
        detail.get("unifiedForecast"), dict)


def carry_over_forecast_blocks(model: DayModel, out_dir: Path) -> list[str]:
    """Graft sealed forecast blocks from the existing packs onto
    incoming forecast-less details for the same race.

    The full-build input (the analyzed prefetch payload) carries no
    forecast blocks for any race, and the publish lane's merge step
    only re-overlays the races the current run (re)published, so
    without this guard every full build strips the blocks of races
    published by earlier runs and frozen since.  Only a published
    existing detail (``predictionStatus`` in
    ``FORECAST_CARRYOVER_SOURCE_STATUSES`` with a sealed
    ``unifiedForecast``) is a carry-over source; races never published
    keep the incoming detail untouched.  Returns the healed race ids.
    """
    if not DATE_RE.match(model.date or ""):
        return []
    existing = model_from_existing_packs(out_dir, model.date)
    healed: list[str] = []
    for rid, detail in model.details.items():
        if _has_forecast(detail):
            continue
        prior = existing.details.get(rid)
        if not _has_forecast(prior):
            continue
        if prior.get("predictionStatus") not in FORECAST_CARRYOVER_SOURCE_STATUSES:
            continue
        for key in FORECAST_CARRYOVER_KEYS:
            if key in prior:
                detail[key] = copy.deepcopy(prior[key])
        detail["predictionStatus"] = "ready"
        marker = (prior.get("preparedMeta") or {}).get("rewritePublish")
        if marker is not None:
            detail.setdefault("preparedMeta", {})[
                "rewritePublish"] = copy.deepcopy(marker)
        healed.append(rid)
    if healed:
        print("STATIC_API_FORECAST_CARRYOVER", model.date,
              len(healed), sorted(healed))
    return healed


# Top-level evidence stamps restored alongside the per-horse blocks
# (mirrors the protect_sync restore list for the same decoration).
EVIDENCE_CARRYOVER_KEYS = (
    "researchEvidenceVersion", "biasProvenance",
)


def _horse_number(horse: Any) -> int:
    if not isinstance(horse, dict):
        return 0
    try:
        return int(horse.get("horseNumber") or 0)
    except (TypeError, ValueError):
        return 0


def carry_over_research_evidence(model: DayModel, out_dir: Path) -> list[str]:
    """Graft the observed research evidence from the existing packs
    onto incoming details whose horses lack it.

    The evidence (``horses[].researchEvidence`` plus the top-level
    ``researchEvidenceVersion`` / ``researchEvidenceHorses`` /
    ``biasProvenance`` stamps) is decoration attached by the prefetch
    analyze stage (``attach_evidence``).  Lane payloads only carry it
    when that stage actually decorated the race in that run, so a full
    build from an undecorated payload — or a delta overlay whose
    detail never carried it — strips the evidence an earlier build
    published, and the app then renders every horse of the race as
    unevaluated (2026-11-22..25: the GitHub-only pack lanes have no
    equivalent of the protect_sync guard that kept the evidence alive
    on the retired D1 sync path).  The rule mirrors protect_sync: an
    incoming value is never replaced, only a missing one is restored
    from the race's own existing pack.  Nothing is invented: a race
    with no published evidence keeps its incoming detail untouched.
    Returns the healed race ids.
    """
    if not DATE_RE.match(model.date or ""):
        return []
    existing = model_from_existing_packs(out_dir, model.date)
    healed: list[str] = []
    for rid, detail in model.details.items():
        if not isinstance(detail, dict):
            continue
        prior = existing.details.get(rid)
        if not isinstance(prior, dict):
            continue
        prior_horses = {_horse_number(h): h for h in (prior.get("horses") or [])
                        if _horse_number(h) > 0
                        and isinstance(h.get("researchEvidence"), dict)}
        if not prior_horses:
            continue
        grafted = False
        for horse in detail.get("horses") or []:
            no = _horse_number(horse)
            if no <= 0 or isinstance(horse.get("researchEvidence"), dict):
                continue
            source = prior_horses.get(no)
            if source is not None:
                horse["researchEvidence"] = copy.deepcopy(
                    source["researchEvidence"])
                grafted = True
        if not grafted:
            continue
        for key in EVIDENCE_CARRYOVER_KEYS:
            if key not in detail and key in prior:
                detail[key] = copy.deepcopy(prior[key])
        count = sum(1 for h in (detail.get("horses") or [])
                    if _horse_number(h) > 0
                    and isinstance(h.get("researchEvidence"), dict))
        if count:
            detail["researchEvidenceHorses"] = count
        healed.append(rid)
    if healed:
        print("STATIC_API_EVIDENCE_CARRYOVER", model.date,
              len(healed), sorted(healed))
    return healed


def carry_over_day_statuses(model: DayModel, out_dir: Path) -> list[str]:
    """Preserve a published raceStatus when the incoming summary
    row carries none.

    Lane payload summaries are built before the races run (the
    prefetch payload's summaries carry no raceStatus at all), so a
    full build rewrites every day row's status to "" — erasing the
    確定/速報 the result lane had already published until the next
    result-ingest merge happens to restore it (2026-11-25 Sonoda 1R:
    day row "" at the 12:44 and 14:41 builds while the race detail
    already held the final result since 12:19).  Only an empty
    incoming status is healed, from the race's own existing day
    pack; a non-empty incoming status always wins, and a race with
    no published status keeps the incoming row untouched.  Returns
    the healed race ids.
    """
    if not DATE_RE.match(model.date or ""):
        return []
    existing = model_from_existing_packs(out_dir, model.date)
    healed: list[str] = []
    for rid, row in model.summaries.items():
        if str(row.get("raceStatus") or ""):
            continue
        prior = existing.summaries.get(rid)
        if not prior:
            continue
        status = str(prior.get("raceStatus") or "")
        if status:
            row["raceStatus"] = status
            healed.append(rid)
    if healed:
        print("STATIC_API_DAY_STATUS_CARRYOVER", model.date,
              len(healed), sorted(healed))
    return healed


EVIDENCE_RESIDUAL_VERSION = "arvexq-evidence-residual-v1"
_PAST_RUN_KEYS = ("recentRaces", "allPastRuns", "pastRaces", "history", "runs")


def _block_available_count(block: Any) -> int:
    """Available-item count of one evidence block; -1 when it is not
    a block at all."""
    if not isinstance(block, dict):
        return -1
    items = (block.get("factors") or {}).get("items") or []
    return sum(1 for it in items
               if isinstance(it, dict) and it.get("available"))


def _evidence_available_count(horse: Any) -> int:
    """Available-item count of a horse's evidence block; -1 when the
    horse carries no block at all."""
    if not isinstance(horse, dict):
        return -1
    return _block_available_count(horse.get("researchEvidence"))


def _horse_has_past_runs(horse: Any) -> bool:
    if not isinstance(horse, dict):
        return False
    return any(isinstance(horse.get(k), list) and len(horse[k]) > 0
               for k in _PAST_RUN_KEYS)


class _PackStore:
    """Result-store substitute for margin completion: the model being
    built plus the packs already in ``out_dir`` — the same substitute
    the 2026-11-26 manual recovery used (the repository's own stored
    packs), resolved lazily per race so a clean day costs nothing."""

    def __init__(self, model: DayModel, out_dir: Path):
        self._model = model
        self._out_dir = out_dir
        self._cache: dict[str, Any] = {}

    def race(self, rid: Any) -> Any:
        rid = str(rid)
        if rid in self._cache:
            return self._cache[rid]
        detail = None
        own = self._model.details.get(rid)
        if isinstance(own, dict):
            detail = own
        else:
            path = self._out_dir / "race" / f"{rid}.json"
            if path.is_file():
                try:
                    body = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(body.get("detail"), dict):
                        detail = body["detail"]
                except Exception:
                    detail = None
        self._cache[rid] = detail
        return detail

    def day_ids(self, date: Any) -> list[str]:
        date = str(date)
        if date == self._model.date:
            return sorted(self._model.details.keys())
        path = self._out_dir / "day" / f"{date}.json"
        if path.is_file():
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
                return [str(r.get("id")) for r in (body.get("races") or [])
                        if isinstance(r, dict) and r.get("id")]
            except Exception:
                pass
        return []


def _decoration_impl():
    """Import the analyze stage's decoration procedure, or None.

    The transitive closure of ``race_intelligence.attach_evidence``
    and ``margin_completion.complete_detail_margins`` is stdlib-only
    (verified 2026-11-26: 20 modules, no third-party imports), so the
    pack lanes — which run this script with setup-python only, no pip
    install — can import it from the checkout by putting the repo root
    on sys.path.  Returns None when the package is not importable in
    this environment; the caller records that in the residual report
    instead of failing the build.
    """
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from arvexq.prediction.margin_completion import (
            complete_detail_margins,
        )
        from arvexq.prediction.race_intelligence import attach_evidence
    except Exception:
        return None
    return complete_detail_margins, attach_evidence


def heal_missing_research_evidence(model: DayModel, out_dir: Path) -> dict:
    """Final-stage self-heal for the observed research evidence.

    Runs the analyze stage's own decoration procedure (margin
    completion from the stored packs, then ``attach_evidence``) on
    every detail that still has horses without an evidence block, or
    with a block whose items are all unavailable, whichever lane
    produced the payload.  A block with available items is never
    rewritten (the procedure recomputes every block, so pre-existing
    ones are snapshotted and restored verbatim); an empty block is
    replaced only when the recompute yields at least one available
    item for it, and is otherwise kept verbatim so the horse surfaces
    in the residual report below with its original block intact.
    Forecast / result content is never touched.  Idempotent: a detail
    whose horses all carry blocks with available items is left
    completely alone, and re-running on a detail whose empty blocks
    could not be filled reproduces the identical detail.

    Afterwards, every horse whose evidence still has zero available
    items is written to ``<out_dir>/evidence-residual/<date>.json``
    (committed with the packs by both publish paths), echoed to
    stdout, and — when any residual exists or the heal could not
    run — surfaced as a workflow warning and a job-summary section.
    The report file is written on every build, with an explicit
    ``residualCount: 0`` on clean days.  Never raises: the build
    continues, but the abnormality cannot pass silently.
    """
    report: dict[str, Any] = {
        "version": EVIDENCE_RESIDUAL_VERSION,
        "date": model.date,
        "healStatus": "not-needed",
        "healedRaces": [],
        "healErrors": [],
        "residualCount": 0,
        "residual": [],
    }
    if not DATE_RE.match(model.date or ""):
        return report
    targets = []
    for rid, detail in model.details.items():
        if not isinstance(detail, dict):
            continue
        if any(isinstance(h, dict) and _horse_number(h) > 0
               and _evidence_available_count(h) <= 0
               for h in detail.get("horses") or []):
            targets.append(rid)
    if targets:
        impl = _decoration_impl()
        if impl is None:
            report["healStatus"] = "unavailable-import"
            print("STATIC_API_EVIDENCE_HEAL_UNAVAILABLE", model.date,
                  len(targets), sorted(targets))
        else:
            complete_detail_margins, attach_evidence = impl
            store = _PackStore(model, out_dir)
            report["healStatus"] = "ok"
            for rid in sorted(targets):
                detail = model.details[rid]
                saved: dict[int, tuple[Any, Any]] = {}
                for h in detail.get("horses") or []:
                    no = _horse_number(h)
                    if no > 0 and isinstance(h.get("researchEvidence"), dict):
                        saved[no] = (copy.deepcopy(h["researchEvidence"]),
                                     copy.deepcopy(h.get("careerCoverage")))
                saved_version = detail.get("researchEvidenceVersion")
                saved_provenance = copy.deepcopy(detail.get("biasProvenance"))
                try:
                    try:
                        complete_detail_margins(detail, store.race,
                                                store.day_ids)
                    except Exception as exc:  # margins never block evidence
                        print("STATIC_API_EVIDENCE_HEAL_MARGIN_WARN",
                              rid, repr(exc))
                    attach_evidence(detail)
                except Exception as exc:
                    report["healErrors"].append(
                        {"raceId": rid, "error": repr(exc)})
                    print("STATIC_API_EVIDENCE_HEAL_ERROR", rid, repr(exc))
                    continue
                for h in detail.get("horses") or []:
                    no = _horse_number(h)
                    if no not in saved:
                        continue
                    saved_block, saved_coverage = saved[no]
                    if _block_available_count(saved_block) > 0:
                        # A block with available items is never
                        # rewritten by the recompute.
                        h["researchEvidence"] = saved_block
                        if saved_coverage is not None:
                            h["careerCoverage"] = saved_coverage
                    elif _evidence_available_count(h) <= 0:
                        # The block was empty and the recompute could
                        # not fill it either: keep the original block
                        # (and its careerCoverage) verbatim instead of
                        # the equally empty recomputation, so nothing
                        # about the horse changes and the residual
                        # report below speaks for it.
                        h["researchEvidence"] = saved_block
                        if saved_coverage is not None:
                            h["careerCoverage"] = saved_coverage
                    # Otherwise the recompute filled a previously
                    # empty block: keep the recomputed block and its
                    # careerCoverage as the heal.
                if saved_version is not None:
                    detail["researchEvidenceVersion"] = saved_version
                if saved_provenance is not None:
                    detail["biasProvenance"] = saved_provenance
                count = sum(1 for h in detail.get("horses") or []
                            if _horse_number(h) > 0
                            and isinstance(h.get("researchEvidence"), dict))
                if count:
                    detail["researchEvidenceHorses"] = count
                report["healedRaces"].append(rid)
    errored = {e["raceId"] for e in report["healErrors"]}
    for rid in sorted(model.details.keys()):
        detail = model.details[rid]
        if not isinstance(detail, dict):
            continue
        for h in detail.get("horses") or []:
            no = _horse_number(h)
            if no <= 0:
                continue
            avail = _evidence_available_count(h)
            if avail > 0:
                continue
            if report["healStatus"] == "unavailable-import":
                reason = "heal-unavailable"
            elif rid in errored:
                reason = "heal-error"
            elif avail < 0:
                reason = "missing-block"
            elif _horse_has_past_runs(h):
                reason = "zero-available-despite-past-runs"
            else:
                reason = "no-past-runs-or-trial-record"
            report["residual"].append({
                "raceId": rid, "horseNumber": no,
                "name": h.get("name"), "reason": reason})
    report["residualCount"] = len(report["residual"])
    body = dict(report)
    body["generatedAt"] = datetime.now(JST).isoformat(timespec="seconds")
    try:
        out_path = out_dir / "evidence-residual" / f"{model.date}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_if_changed(out_path, body)
    except Exception as exc:
        print("STATIC_API_EVIDENCE_RESIDUAL_WRITE_FAILED", repr(exc))
    if report["healedRaces"]:
        print("STATIC_API_EVIDENCE_HEAL", model.date,
              len(report["healedRaces"]), sorted(report["healedRaces"]))
    print("STATIC_API_EVIDENCE_RESIDUAL", model.date,
          "residual", report["residualCount"],
          "heal_status", report["healStatus"])
    if report["residualCount"] or report["healStatus"] not in ("ok", "not-needed"):
        names = ", ".join(
            f"{r['raceId']}#{r['horseNumber']} {r.get('name') or ''} ({r['reason']})"
            for r in report["residual"][:20])
        print(f"::warning::researchEvidence residual "
              f"{report['residualCount']} horse(s) on {model.date} "
              f"(heal={report['healStatus']}): {names}")
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            try:
                with open(summary_file, "a", encoding="utf-8") as fh:
                    fh.write(f"\n### ⚠ researchEvidence residual: "
                             f"{report['residualCount']} horse(s) "
                             f"({model.date})\n\n")
                    fh.write(f"healStatus: {report['healStatus']}; "
                             f"healedRaces: {len(report['healedRaces'])}; "
                             f"detail: `evidence-residual/{model.date}.json` "
                             f"in the pack tree\n\n")
                    for r in report["residual"][:50]:
                        fh.write(f"- {r['raceId']} #{r['horseNumber']} "
                                 f"{r.get('name') or ''} — {r['reason']}\n")
            except Exception:
                pass
    return report


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _strip_stamps(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_stamps(v) for k, v in obj.items() if k != "generatedAt"}
    if isinstance(obj, list):
        return [_strip_stamps(v) for v in obj]
    return obj


def _write_if_changed(path: Path, body: dict) -> bool:
    """Writes body unless the existing file is canonically identical
    (ignoring generatedAt stamps at any depth).  Returns True when written."""
    if path.is_file():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            if _canonical(_strip_stamps(old)) == _canonical(_strip_stamps(body)):
                return False
        except Exception:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8")
    return True


def build(model: DayModel, out_dir: Path, generated_at: str,
          with_day_full: bool = False, prune_days: int | None = None) -> dict:
    if not DATE_RE.match(model.date or ""):
        raise ValueError(f"invalid or missing date: {model.date!r}")
    races = sorted(model.summaries.values(), key=_sort_key)
    race_ids = [str(r["id"]) for r in races]
    detail_ids = sorted(model.details.keys())
    missing = [rid for rid in race_ids if rid not in model.details]
    analysis_count = sum(1 for rid in detail_ids if model.analysis_ready.get(rid))
    complete = bool(races) and not missing
    changed = 0

    day_body = {
        "version": VERSION, "source": "static-json", "generatedAt": generated_at,
        "ok": True, "date": model.date, "races": races, "details": [],
        "raceCount": len(races), "detailCount": 0, "analysisCount": 0,
        "missing": [], "complete": bool(races), "displayComplete": bool(races),
    }
    if _write_if_changed(out_dir / "day" / f"{model.date}.json", day_body):
        changed += 1

    details_sorted = [model.details[rid] for rid in detail_ids]
    if with_day_full:
        full_body = {
            "version": VERSION, "source": "static-json", "generatedAt": generated_at,
            "ok": True, "date": model.date, "races": races, "details": details_sorted,
            "raceCount": len(races), "detailCount": len(details_sorted),
            "analysisCount": analysis_count, "missing": missing,
            "complete": complete, "displayComplete": complete,
            "analysisComplete": complete and analysis_count >= len(races),
        }
        if _write_if_changed(out_dir / "day-full" / f"{model.date}.json", full_body):
            changed += 1

    for rid in detail_ids:
        payload = copy.deepcopy(model.details[rid])
        # view=display strips this field server-side; mirror that exactly.
        payload.pop("massFeatureSnapshot", None)
        # The API's odds rows never carry the race id; strip it so the
        # static body matches the response shape field-for-field.
        odds_rows = [{k: v for k, v in o.items() if k not in ("race_id", "raceId")}
                     if isinstance(o, dict) else o for o in (model.odds.get(rid) or [])]
        race_body = {
            "version": VERSION, "source": "static-json", "generatedAt": generated_at,
            "ok": True, "race_id": rid,
            "summary": {"id": rid, "date": payload.get("date") or model.date,
                        "track": payload.get("track"),
                        "raceNumber": payload.get("raceNumber")},
            "detail": payload,
            "analysis_ready": bool(model.analysis_ready.get(rid)),
            "detail_updated_at": model.detail_updated_at.get(rid),
            "odds": odds_rows,
        }
        if _write_if_changed(out_dir / "race" / f"{rid}.json", race_body):
            changed += 1

    index_path = out_dir / "index.json"
    index = {"version": VERSION, "dates": {}}
    if index_path.is_file():
        try:
            old_index = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(old_index.get("dates"), dict):
                index = old_index
        except Exception:
            pass
    index["version"] = VERSION
    index["generatedAt"] = generated_at
    index["dates"][model.date] = {
        "raceCount": len(races), "detailCount": len(details_sorted),
        "generatedAt": generated_at, "raceIds": detail_ids,
    }
    pruned = 0
    if prune_days is not None:
        from datetime import date as _date, timedelta
        try:
            built = _date.fromisoformat(model.date)
            cutoff = (built - timedelta(days=prune_days)).isoformat()
            for old_date in sorted(list(index["dates"].keys())):
                if old_date >= cutoff or old_date == model.date:
                    continue
                entry = index["dates"].pop(old_date)
                for sub in ("day", "day-full"):
                    f = out_dir / sub / f"{old_date}.json"
                    if f.is_file():
                        f.unlink()
                        pruned += 1
                for rid in entry.get("raceIds") or []:
                    f = out_dir / "race" / f"{rid}.json"
                    if f.is_file():
                        f.unlink()
                        pruned += 1
        except ValueError:
            pass
    if _write_if_changed(index_path, index):
        changed += 1

    return {"date": model.date, "races": len(races), "details": len(details_sorted),
            "missing": missing, "skippedBanei": model.skipped_banei,
            "changedFiles": changed, "prunedFiles": pruned}


def fetch_model(api_base: str, date: str) -> DayModel:
    """Transitional read-back: mirrors the posting scripts' fetch_day."""
    def get(path: str) -> dict:
        req = urllib.request.Request(api_base.rstrip("/") + path, headers={
            "User-Agent": "Mozilla/5.0 (arvexq-static-api-build)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    day = get(f"/api/day?date={urllib.parse.quote(date)}&details=0")
    model = DayModel(date)
    for s in day.get("races") or []:
        if not isinstance(s, dict):
            continue
        row = _day_row_from_summary(s)
        rid = str(row.get("id") or "")
        if not rid:
            continue
        if _is_banei(rid, str(row.get("track") or "")):
            model.skipped_banei += 1
            continue
        model.summaries[rid] = row
    for rid in list(model.summaries.keys()):
        resp = get("/api/race/" + urllib.parse.quote(rid, safe=""))
        _add_detail(model, resp.get("detail"), odds=resp.get("odds"),
                    analysis_ready=resp.get("analysis_ready"),
                    updated_at=resp.get("detail_updated_at"))
    return model


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", help="payload JSON file (sync payload / official snapshot / full day response)")
    p.add_argument("--fetch-date", help="read the day back from the API instead of a file")
    p.add_argument("--api-base", default="https://kraiz-api.4b89h4fydd.workers.dev")
    p.add_argument("--out-dir", default="arvexq/ui/static/api-static")
    p.add_argument("--with-day-full", action="store_true",
                   help="also write day-full/<date>.json (local/audit use; too large to deploy)")
    p.add_argument("--prune-days", type=int, default=None,
                   help="drop packs older than N days (from the built date) out of the tree")
    p.add_argument("--merge-existing", action="store_true",
                   help="overlay the input on the packs already in --out-dir "
                        "for the same date (for delta payloads that carry "
                        "only updated races)")
    args = p.parse_args()

    generated_at = datetime.now(JST).isoformat(timespec="seconds")
    try:
        if args.fetch_date:
            model = fetch_model(args.api_base, args.fetch_date)
        elif args.input:
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
            model = detect_model(payload)
        else:
            p.error("one of --input or --fetch-date is required")
        if args.merge_existing and DATE_RE.match(model.date or ""):
            base = model_from_existing_packs(Path(args.out_dir), model.date)
            if base.summaries or base.details:
                model = merge_models(base, model)
        # A full (or tombstone-carrying delta) build must not strip
        # the sealed forecast blocks of races published by earlier
        # runs: carry them over from the existing packs first.
        carry_over_forecast_blocks(model, Path(args.out_dir))
        # Same rule for the observed research evidence: lane payloads
        # carry it only when the analyze stage decorated the race in
        # that run, so without this graft the first undecorated build
        # of the day erases the evidence for every race and the app
        # renders all horses as unevaluated.
        carry_over_research_evidence(model, Path(args.out_dir))
        # Same rule for the day rows' raceStatus: a build whose
        # payload summaries predate the races must not blank the
        # status the result lane already published for them.
        carry_over_day_statuses(model, Path(args.out_dir))
        # Final stage: a race no lane ever decorated has nothing for
        # carry-over to restore, so run the decoration procedure here,
        # at the one point every lane's packs pass through, and report
        # any horse that still ends up evidence-empty instead of
        # letting the day publish silently unevaluated.
        heal_missing_research_evidence(model, Path(args.out_dir))
    except Exception as e:  # fail soft: keep the last good packs deployed
        print(f"STATIC_API_INPUT_FAILED {e!r}")
        return 2

    try:
        result = build(model, Path(args.out_dir), generated_at,
                       with_day_full=args.with_day_full, prune_days=args.prune_days)
    except Exception as e:
        print(f"STATIC_API_BUILD_FAILED {e!r}")
        return 2
    print("STATIC_API_SAVED", result["date"], "races", result["races"],
          "details", result["details"], "missing", len(result["missing"]),
          "skipped_banei", result["skippedBanei"],
          "changed_files", result["changedFiles"],
          "pruned_files", result["prunedFiles"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
