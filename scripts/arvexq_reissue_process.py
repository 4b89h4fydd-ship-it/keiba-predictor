#!/usr/bin/env python3
"""Process slim reissue requests inside GitHub Actions.

The full publish lane (scripts/arvexq_rewrite_publish.py) re-evaluates
every race of a date on every run, so a single targeted re-issue used
to wait for a whole pipeline cycle (2026-11-09 env-repair: batches
landed at 14:22 / 14:51 / 14:57 for work scoped to minutes). This
processor is the slim path: it reads
arvexq/reissue_requests/requests.json, and for each pending entry it
runs the publish lane's OWN per-race machinery (fetch stored detail,
build_publish_detail, protect_detail, POST /api/sync, read-back
verification) for that one race only. Publishing still happens only
inside GitHub Actions with the existing SYNC_TOKEN secret; the
protect seam is untouched and no new credential exists.

Exactly-once discipline. The stored detail keeps only the LATEST
revision stamp in preparedMeta.rewritePublish.revision — a surgical
stamp (place-EV, ticket-R24) replaces the revision dict wholesale,
so an earlier stamp of another kind disappears from the detail
(2026-11-09: a place-ev stamp landing over an env-repair stamp made
the env-repair predicate read the race as never repaired and the
race was repaired twice). This processor therefore never decides
from the latest stamp alone:

  1. its own ledger (arvexq/reissue_requests/results.json) is
     consulted first — both the outcomes it recorded and the stamp
     OBSERVATIONS it snapshots before every decision form an
     append-only chain of record for everything this path has seen;
  2. the current stored detail is then read for ALL surviving
     evidence of the requested kind's terminal state (the latest
     stamp, marker-level facts such as blendApplied / abilityLane,
     and product-level state such as placeExpectedValues, the R24
     trifecta shape, or the env-repair probability-computation-time
     derivation the publish predicate itself uses);
  3. only when neither source shows the kind as applied does the
     publish build evaluate the race.

Entries are immutable once written; a processed entry is never
re-processed (file a new entry to re-request). Transient read
failures are recorded as error-retryable and stay pending for the
next triggered run, up to MAX_ATTEMPTS.

Usage:
  SYNC_TOKEN=... python3 scripts/arvexq_reissue_process.py [--dry-run-all]

--dry-run-all forces every pending entry to be evaluated in dry-run
mode (build + self-verify, never a POST), regardless of its mode.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REQUESTS_PATH = ROOT / "arvexq" / "reissue_requests" / "requests.json"
RESULTS_PATH = ROOT / "arvexq" / "reissue_requests" / "results.json"
JST = ZoneInfo("Asia/Tokyo")

# The revision kinds a request may name. lane-upgrade covers the
# lane-upgrade family (incl. the adoption-day reason); marksResync
# names the env-repair marks-resync state (the two stored marks
# blocks disagree after a repair) rather than a stamp of its own.
KNOWN_KINDS = ("lane-upgrade", "blend-upgrade", "place-ev-upgrade",
               "ticket-r24-upgrade", "env-repair-upgrade", "marksResync")
RACE_ID_RE = re.compile(r"^(jra|nar)-\d{4}-\d{2}-\d{2}-\S+-\d{1,2}$")
RACE_DATE_RE = re.compile(r"^\w+-(\d{4}-\d{2}-\d{2})-")
MAX_ATTEMPTS = 5
TERMINAL = ("applied", "applied-other", "already-applied",
            "not-applied", "failed", "dry-run-applied",
            "dry-run-not-applied", "dry-run-already-applied")


def validate_entry(entry) -> str | None:
    """Error string when a request entry is malformed, else None."""
    if not isinstance(entry, dict):
        return "entry is not an object"
    if not isinstance(entry.get("request_id"), str) \
            or not entry["request_id"]:
        return "request_id missing"
    race_id = entry.get("race_id")
    if not isinstance(race_id, str) or not RACE_ID_RE.match(race_id):
        return f"race_id malformed: {race_id!r}"
    if entry.get("revision_kind") not in KNOWN_KINDS:
        return f"revision_kind not known: {entry.get('revision_kind')!r}"
    if entry.get("mode", "apply") not in ("apply", "dry-run"):
        return f"mode not known: {entry.get('mode')!r}"
    if not isinstance(entry.get("reason"), str) or not entry["reason"]:
        return "reason missing"
    return None


def _marks_map(entries, *keys) -> dict:
    out = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        label = next((e.get(k) for k in keys if e.get(k)), None)
        if label:
            out[str(label)] = e.get("horseNumber")
    return out


def marks_blocks_agree(detail: dict) -> bool | None:
    """True when the two stored marks blocks name the same horses.

    Mirrors the publish lane's read-back condition: a disagreement
    exists when the unified block carries 5 marks and the stored
    predictionMarks differ from it. Returns None when either block
    is unreadable (no claim either way).
    """
    unified = detail.get("unifiedForecast")
    if not isinstance(unified, dict):
        return None
    pm = _marks_map(detail.get("predictionMarks"), "mark")
    uf = _marks_map(unified.get("marks"), "markSymbol", "mark")
    if not pm or not uf:
        return None
    if len(uf) == 5 and pm != uf:
        return False
    return pm == uf


def stamp_state(detail: dict) -> dict:
    """Snapshot of every stamp fact the exactly-once checks read."""
    marker = (detail.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return {"marker": None}
    revision = marker.get("revision")
    rev = None
    if isinstance(revision, dict):
        rev = {key: revision.get(key) for key in
               ("kind", "reason", "revisedAt", "revisionCount",
                "probabilityComputedAt", "marksResync", "surface")
               if revision.get(key) is not None}
    post = marker.get("postProcessing")
    return {
        "marker": {
            "abilityLane": marker.get("abilityLane"),
            "blendApplied": marker.get("blendApplied"),
            "postBlendApplied": (post.get("blendApplied")
                                 if isinstance(post, dict) else None),
            "firstPublishedAt": marker.get("firstPublishedAt"),
            "publishedAt": marker.get("publishedAt"),
            "receiptSha256": marker.get("receiptSha256"),
        },
        "revision": rev,
        "predictionStatus": detail.get("predictionStatus"),
    }


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


def goal_state(detail: dict, kind: str, pub) -> str | None:
    """Evidence that `kind`'s terminal state already holds, or None.

    Reads the FULL surviving stamp evidence, never the latest
    revision alone (see the module docstring for the overwrite
    hole this defends against).
    """
    if kind == "marksResync":
        # The goal state is a property of the two marks blocks
        # alone; no publish marker is required.
        agree = marks_blocks_agree(detail)
        if agree is True:
            return "the two stored marks blocks already agree"
        return None
    marker = (detail.get("preparedMeta") or {}).get("rewritePublish")
    if not isinstance(marker, dict):
        return None
    revision = marker.get("revision")
    rev_kind = None
    if isinstance(revision, dict):
        rev_kind = revision.get("kind") or revision.get("reason")
    if kind == "lane-upgrade":
        if marker.get("abilityLane") == pub.V9B_LANE:
            return "abilityLane is already v9b-cal-market"
        if rev_kind in ("lane-upgrade", "lane-upgrade-v9b-adoption"):
            return f"latest revision stamp is {rev_kind}"
        return None
    if kind == "blend-upgrade":
        if rev_kind == "blend-upgrade":
            return "latest revision stamp is blend-upgrade"
        blend = marker.get("blendApplied")
        if not isinstance(blend, bool):
            post = marker.get("postProcessing")
            if isinstance(post, dict):
                blend = post.get("blendApplied")
        if blend is True:
            return "blendApplied is true (blended state is final)"
        return None
    if kind == "place-ev-upgrade":
        if rev_kind == "place-ev-upgrade":
            return "latest revision stamp is place-ev-upgrade"
        unified = detail.get("unifiedForecast")
        plan = unified.get("ticketPlan") if isinstance(unified, dict) \
            else None
        if isinstance(plan, dict) and "placeExpectedValues" in plan:
            return "ticketPlan already carries placeExpectedValues"
        return None
    if kind == "ticket-r24-upgrade":
        if rev_kind == "ticket-r24-upgrade":
            return "latest revision stamp is ticket-r24-upgrade"
        mark_order = pub._stored_mark_order(detail)
        if mark_order is None or len(mark_order) < 3:
            return None
        from rewrite.analysis.tickets import formation_r24_selections
        trifecta = None
        for entry in detail.get("recommendedBets") or []:
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
        if stored and stored == set(formation_r24_selections(mark_order)):
            return "stored trifecta is already the R24 subset"
        return None
    if kind == "env-repair-upgrade":
        # The pipeline branch itself is scoped to one date; an
        # env stamp anywhere else is anomalous and never counts.
        id_match = RACE_DATE_RE.match(str(detail.get("id") or ""))
        race_date = id_match.group(1) if id_match \
            else str(detail.get("date") or "")
        if race_date != pub.ENV_REPAIR_DATE:
            return None
        if rev_kind == "env-repair-upgrade":
            return "latest revision stamp is env-repair-upgrade"
        # Mirror _env_repair_upgrade_info's computation-time
        # derivation: a forecast-recomputing revision sets the
        # probabilities' time; surgical revisions (place-EV,
        # ticket-R24) keep the stored probabilities, so with one of
        # those on top the probabilities date from first
        # publication. A race whose probabilities were computed at
        # or after the surface fix already ran with the live
        # surface — the repair's goal state.
        if rev_kind in ("blend-upgrade", "lane-upgrade",
                        "lane-upgrade-v9b-adoption", "roster-change"):
            computed_at = _parse_stamp(revision.get("revisedAt"))
        else:
            computed_at = _parse_stamp(
                marker.get("firstPublishedAt")
                or marker.get("publishedAt"))
        if computed_at is not None \
                and computed_at >= pub.ENV_REPAIR_FIX_LIVE_AT:
            return ("probabilities were computed at "
                    f"{computed_at.isoformat(timespec='seconds')}, "
                    "at/after the surface fix")
        return None
    return None


def applied_kinds(detail: dict, pub) -> list[str]:
    """Every known kind whose terminal state the detail shows."""
    return [kind for kind in KNOWN_KINDS
            if goal_state(detail, kind, pub) is not None]


def already_applied(race_id: str, kind: str, detail: dict,
                    ledger: dict, pub) -> tuple[str, str] | None:
    """(source, evidence) when the kind is already applied.

    The slim ledger is consulted before the stored detail: its
    outcomes and observations are the chain of record this path
    keeps precisely because the stored marker retains only the
    latest stamp.
    """
    results = ledger.get("results") or {}
    for outcome in results.values():
        if not isinstance(outcome, dict):
            continue
        if outcome.get("race_id") != race_id:
            continue
        if outcome.get("status") in ("applied", "applied-other") and (
                outcome.get("revision_kind") == kind
                or outcome.get("produced_kind") == kind):
            return ("slim-ledger",
                    f"request {outcome.get('request_id')} recorded "
                    f"{outcome.get('status')} for this race/kind")
    observations = (ledger.get("observations") or {}).get(race_id) or []
    for obs in observations:
        if isinstance(obs, dict) and kind in (obs.get("applied_kinds")
                                              or []):
            return ("slim-ledger-observation",
                    f"observed applied on {obs.get('observed_at')} "
                    f"(request {obs.get('request_id')})")
    evidence = goal_state(detail, kind, pub)
    if evidence is not None:
        return ("stored-stamps", evidence)
    return None


def _load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def _save_results(ledger: dict) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")


def process_entry(entry: dict, ledger: dict, token: str | None,
                  force_dry_run: bool, pub) -> dict:
    """Run one request through the publish lane's per-race path."""
    from arvexq.ingest.full_snapshot_codec import (
        pack_detail, unpack_detail)
    from arvexq.prediction.unified_product import (
        verified as verified_unified)

    request_id = entry["request_id"]
    race_id = entry["race_id"]
    kind = entry["revision_kind"]
    dry_run = force_dry_run or entry.get("mode", "apply") == "dry-run"
    now = datetime.now(JST)
    outcome = {
        "request_id": request_id, "race_id": race_id,
        "revision_kind": kind,
        "mode": "dry-run" if dry_run else "apply",
        "processed_at": now.isoformat(timespec="seconds"),
        "run_id": os.environ.get("GITHUB_RUN_ID") or "local",
    }

    resp = pub._get("/api/race/" + urllib.parse.quote(race_id, safe=""))
    old_raw = resp.get("detail") or {}
    if not old_raw or str(old_raw.get("id") or "") != race_id:
        outcome["status"] = "error-retryable"
        outcome["detail"] = "stored detail unreadable from the API"
        return outcome
    old = unpack_detail(old_raw)

    # Snapshot the stamp state BEFORE deciding: this observation is
    # the chain of record that survives later stamp overwrites.
    state = stamp_state(old)
    observations = ledger.setdefault("observations", {}) \
        .setdefault(race_id, [])
    observations.append({
        "observed_at": now.isoformat(timespec="seconds"),
        "request_id": request_id,
        "stamp": state,
        "applied_kinds": applied_kinds(old, pub),
    })

    prior = already_applied(race_id, kind, old, ledger, pub)
    if prior is not None:
        outcome["status"] = ("dry-run-already-applied" if dry_run
                             else "already-applied")
        outcome["detail"] = f"{prior[0]}: {prior[1]}"
        return outcome

    date_match = RACE_DATE_RE.match(race_id)
    race_date = date_match.group(1) if date_match else old.get("date")
    listing = pub._get(f"/api/races?date={race_date}")
    summaries = listing.get("races") or listing.get("summaries") or []
    summary = next(
        (s for s in summaries
         if (s.get("race_id") or s.get("id")) == race_id), None)
    if summary is None:
        outcome["status"] = "error-retryable"
        outcome["detail"] = f"race not in the {race_date} listing yet"
        return outcome

    new, receipt = pub.build_publish_detail(old_raw, summary,
                                            datetime.now(JST))
    if new is None:
        outcome["status"] = ("dry-run-not-applied" if dry_run
                             else "not-applied")
        outcome["detail"] = str(receipt)
        return outcome
    revision = ((new.get("preparedMeta") or {})
                .get("rewritePublish") or {}).get("revision")
    produced_kind = None
    if isinstance(revision, dict):
        produced_kind = revision.get("kind") or revision.get("reason")
        if kind == "marksResync" and revision.get("marksResync"):
            produced_kind = "marksResync"
    outcome["produced_kind"] = produced_kind
    outcome["receipt"] = str(receipt)[:12] + "…"

    check = verified_unified(dict(unpack_detail(old_raw),
                                  unifiedForecast=new["unifiedForecast"]))
    if check is None:
        outcome["status"] = "failed"
        outcome["detail"] = "product does not self-verify"
        return outcome
    if dry_run:
        outcome["status"] = "dry-run-applied"
        outcome["detail"] = ("build produced "
                              f"{produced_kind or 'a first publication'}; "
                              "not posted (dry-run)")
        return outcome
    if not token:
        outcome["status"] = "failed"
        outcome["detail"] = "SYNC_TOKEN missing for an apply-mode entry"
        return outcome

    protect_detail = pub._load_protect()
    final = protect_detail(old_raw, new)
    if isinstance(old_raw, dict) and "arvexqFullPayload" in old_raw:
        final = pack_detail(final)
    result = pub._post_sync(final, token)
    if not result.get("ok"):
        outcome["status"] = "failed"
        outcome["detail"] = f"sync rejected: {result}"
        return outcome
    back = pub._get("/api/race/" + urllib.parse.quote(race_id, safe=""))
    back_detail = back.get("detail") or {}
    stored = back_detail.get("unifiedForecast") or {}
    if stored.get("receiptSha256") != receipt:
        outcome["status"] = "failed"
        outcome["detail"] = "read-back receipt mismatch"
        return outcome
    built_pm = _marks_map(new.get("predictionMarks"), "mark")
    stored_pm = _marks_map(back_detail.get("predictionMarks"), "mark")
    stored_uf = _marks_map(stored.get("marks"), "markSymbol", "mark")
    if (len(built_pm) == 5 and stored_pm != built_pm) or (
            len(stored_uf) == 5 and stored_pm != stored_uf):
        outcome["status"] = "failed"
        outcome["detail"] = (
            f"read-back marks mismatch (stored predictionMarks "
            f"{stored_pm} vs built {built_pm} / stored unified "
            f"{stored_uf})")
        return outcome
    if kind == "marksResync":
        agree = marks_blocks_agree(back_detail)
        outcome["status"] = "applied" if agree else "failed"
        outcome["detail"] = ("marks blocks agree after the resync"
                              if agree else
                              "marks blocks still disagree after "
                              "the resync write")
        return outcome
    if produced_kind is None:
        outcome["status"] = "applied-other"
        outcome["detail"] = ("the race carried no frozen publication; "
                             "the build produced its first publication; "
                             "read-back verified")
    elif produced_kind == kind:
        outcome["status"] = "applied"
        outcome["detail"] = "read-back verified (receipt + marks blocks)"
    else:
        outcome["status"] = "applied-other"
        outcome["detail"] = (f"the pipeline produced {produced_kind} "
                             f"instead of the requested {kind}; "
                             "read-back verified")
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run-all", action="store_true")
    args = parser.parse_args()

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "arvexq_rewrite_publish",
        ROOT / "scripts" / "arvexq_rewrite_publish.py")
    pub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pub)

    requests_doc = _load_json(REQUESTS_PATH, {"version": 1,
                                              "requests": []})
    ledger = _load_json(RESULTS_PATH, {"version": 1, "results": {},
                                       "observations": {}})
    ledger.setdefault("results", {})
    ledger.setdefault("observations", {})
    token = os.environ.get("SYNC_TOKEN")

    counts = {"pending": 0, "failed": 0}
    for entry in requests_doc.get("requests") or []:
        error = validate_entry(entry)
        if error is not None:
            print(f"BAD-ENTRY {entry!r}: {error}")
            counts["failed"] += 1
            continue
        request_id = entry["request_id"]
        recorded = ledger["results"].get(request_id)
        if isinstance(recorded, dict) \
                and recorded.get("status") in TERMINAL:
            continue
        counts["pending"] += 1
        attempts = int((recorded or {}).get("attempts") or 0)
        try:
            outcome = process_entry(entry, ledger, token,
                                    args.dry_run_all, pub)
        except Exception as exc:  # per-entry isolation; report onward
            outcome = {
                "request_id": request_id,
                "race_id": entry["race_id"],
                "revision_kind": entry["revision_kind"],
                "mode": entry.get("mode", "apply"),
                "processed_at": datetime.now(JST).isoformat(
                    timespec="seconds"),
                "run_id": os.environ.get("GITHUB_RUN_ID") or "local",
                "status": "error-retryable",
                "detail": f"{type(exc).__name__}: {exc}",
            }
        outcome["attempts"] = attempts + 1
        if outcome["status"] == "error-retryable" \
                and outcome["attempts"] >= MAX_ATTEMPTS:
            outcome["status"] = "failed"
            outcome["detail"] += " (attempts exhausted)"
        ledger["results"][request_id] = outcome
        _save_results(ledger)
        print(f"{outcome['status'].upper()} {entry['race_id']} "
              f"({entry['revision_kind']}): {outcome.get('detail')}")
        if outcome["status"] == "failed":
            counts["failed"] += 1
    print(f"reissue requests: {counts}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
