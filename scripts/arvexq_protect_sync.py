#!/usr/bin/env python3
"""Protect existing server-authoritative pre-off forecasts in each D1 sync batch.

Run immediately before a Worker /api/sync write. Missing remote state is not
assumed empty: fail closed when a lookup fails, rather than erase an archive.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from arvexq.prediction.prerace_archive import pre_off, restore_seal, sealed_lock
from arvexq.ingest.full_snapshot_codec import KEY as FULL_PAYLOAD_KEY, pack_detail as pack_full, unpack_detail as unpack_full


def fetch_current(base: str, rid: str) -> dict[str, Any] | None:
    url = base.rstrip("/") + "/api/race/" + urllib.parse.quote(rid, safe="") + "?sealguard=" + str(time.time_ns())
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "ARVEXQ-SealGuard/1"})
    # Worker/D1 503s are sometimes transient. Retry boundedly, but never
    # treat a failed read as 'no previous archive' (that would allow erasure).
    failure = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                # No D1 race detail is expected at the start of a new day.
                # Require an independently successful date-scoped day response;
                # do not convert arbitrary 404s (bad routes/outages) to absence.
                match = re.search(r"20\d{2}-\d{2}-\d{2}", rid)
                if not match:
                    raise RuntimeError("D1 seal-guard cannot verify 404 without race date") from exc
                date = match.group(0)
                day_url = base.rstrip("/") + "/api/day?date=" + urllib.parse.quote(date) + "&details=0"
                try:
                    day_req = urllib.request.Request(
                        day_url, headers={"accept": "application/json", "user-agent": "ARVEXQ-SealGuard/1"}
                    )
                    with urllib.request.urlopen(day_req, timeout=25) as response:
                        day = json.loads(response.read().decode("utf-8"))
                    if not isinstance(day, dict) or not isinstance(day.get("races"), list):
                        raise ValueError("unverifiable D1 day response")
                    if day.get("date") and str(day["date"]) != date:
                        raise ValueError("D1 day date mismatch")
                except Exception as day_exc:
                    raise RuntimeError("D1 seal-guard 404 cannot be confirmed as a missing race") from day_exc
                return None
            failure = exc
        except Exception as exc:
            failure = exc
        if attempt == 4:
            raise RuntimeError("D1 seal-guard lookup failed closed: "+str(failure)) from failure
        time.sleep(min(5.0, 0.6*(2**attempt)))
    if not isinstance(data, dict):
        raise RuntimeError("invalid D1 response")
    for item in (data.get("detail"), data.get("race"), data):
        if isinstance(item, dict) and str(item.get("id") or "") == rid:
            return item
    if data.get("ok") is False:
        raise RuntimeError("D1 returned failure")
    # The provider explicitly reports no detail; no historical snapshot to merge.
    if not data.get("detail") and not data.get("race") and not data.get("id"):
        return None
    raise RuntimeError("D1 returned a mismatched race")


def protect_detail(old: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    if FULL_PAYLOAD_KEY in incoming:
        # Archive protection must edit the real original, then recompress it.
        # Editing only the compact index would leave the full original unprotected.
        return pack_full(protect_detail(unpack_full(old) if isinstance(old, dict) else old, unpack_full(incoming)))
    if isinstance(old, dict) and FULL_PAYLOAD_KEY in old:
        old = unpack_full(old)
    out = copy.deepcopy(incoming)
    if not isinstance(old, dict):
        return out
    # The full morning prediction is a permanent, first-published record.
    # It must survive a later live odds refresh, prefetch or result repair.
    baseline = old.get("morningMarkSnapshot")
    if isinstance(baseline, dict) and baseline.get("version") == "arvexq-morning-marks-v1":
        out["morningMarkSnapshot"] = copy.deepcopy(baseline)
    # Frozen mass-feature evidence is an immutable pre-off training record,
    # not a transient result. Convert a legacy raw snapshot to the lossless
    # archive on the next safe replace and keep the original feature hash.
    if old.get("massFeatureArchive") or old.get("massFeatureSnapshot"):
        from arvexq.prediction.mass_feature_transport import pack_mass_detail
        from arvexq.prediction.mass_prerace_bridge import FROZEN_MASS_KEYS
        frozen = (pack_mass_detail(old, preserve_unverified_legacy=True) if isinstance(old.get("massFeatureSnapshot"), dict)
                  and isinstance(old.get("preRacePrediction"), dict) else old)
        for key in FROZEN_MASS_KEYS:
            if key in frozen:
                out[key] = copy.deepcopy(frozen[key])
            else:
                out.pop(key, None)
    previous_revisions = old.get("officialMarkRevisions")
    if isinstance(previous_revisions, list) and previous_revisions:
        candidate = out.get("officialMarkRevisions")
        allow_append = False
        if isinstance(candidate, list) and len(candidate) > len(previous_revisions):
            # Same immutable historical prefix, plus a newly authenticated
            # pre-off revision justified by a real official source change.
            from datetime import datetime
            from arvexq.prediction.prerace_archive import JST
            from arvexq.prediction.official_course_revision import pre_off_change
            allow_append = (
                candidate[:len(previous_revisions)] == previous_revisions
                and len(candidate) == len(previous_revisions) + 1
                and bool(pre_off_change(old, old.get("officialCourseCondition"),
                                        out.get("officialCourseCondition"), datetime.now(JST)))
            )
        if not allow_append:
            out["officialMarkRevisions"] = copy.deepcopy(previous_revisions)
    # User-directed model revisions have a different trust origin from
    # official condition revisions. Only one valid append to the original
    # revision chain is allowed. Failed attempts never wipe earlier records.
    previous_models = list(old.get("modelMarkRevisions") or [])
    proposed_models = out.get("modelMarkRevisions")
    allow_new_model = False
    if isinstance(proposed_models, list) and len(proposed_models) == len(previous_models) + 1:
        if proposed_models[:-1] == previous_models:
            from datetime import datetime, timedelta
            from arvexq.prediction.prerace_archive import JST, post_at
            from arvexq.prediction.user_approved_model_revision import valid_revision, enabled
            at_now = datetime.now(JST)
            item = proposed_models[-1]
            post = post_at(old)
            if isinstance(item, dict) and valid_revision(old, item) and enabled(at_now):
                submitted = datetime.fromisoformat(str(item["revisedAt"]).replace("Z", "+00:00"))
                allow_new_model = (bool(post) and at_now < post and
                                   not sealed_lock(old) and
                                   not (isinstance(old.get("preRaceBet"), dict) and
                                        old["preRaceBet"].get("fixedAt")) and
                                   timedelta(0) <= at_now - submitted <= timedelta(minutes=8))
    if allow_new_model:
        out["modelMarkRevisions"] = copy.deepcopy(proposed_models)
    elif previous_models:
        out["modelMarkRevisions"] = copy.deepcopy(previous_models)
    else:
        out.pop("modelMarkRevisions", None)
    # A market/result-only sync must never replace a richer career archive
    # with five recent rows. This does not alter immutable prediction seals.
    previous_by_no = {int(h.get("horseNumber") or 0): h
                      for h in old.get("horses") or [] if isinstance(h, dict)}
    race_day = str(out.get("date") or old.get("date") or "")
    from arvexq.ingest.full_career import merge_career
    for current in out.get("horses") or []:
        if not isinstance(current, dict):
            continue
        historical = previous_by_no.get(int(current.get("horseNumber") or 0))
        if not isinstance(historical, dict):
            continue
        for key in ("careerArchive", "careerTransport", "_careerHistoryAudit", "careerStartEvidence"):
            if key in historical and key not in current:
                current[key] = copy.deepcopy(historical[key])
        from arvexq.ingest.career_transport import recover_horse, pack_horse
        old_full = recover_horse(historical, race_day) if historical.get("careerArchive") else historical
        new_full = recover_horse(current, race_day) if current.get("careerArchive") else current
        merged = merge_career(
            [*(old_full.get("allPastRuns") or []), *(old_full.get("recentRaces") or [])],
            [*(new_full.get("allPastRuns") or []), *(new_full.get("recentRaces") or [])], race_day)
        if merged:
            current["allPastRuns"] = merged
            current["recentRaces"] = merged[:5]
            if historical.get("careerArchive") or current.get("careerArchive"):
                # Rebuild the archive from the union. Copying only one sidecar
                # would silently lose observations added by the other feed.
                current.pop("careerArchive", None)
                rebuilt = pack_horse(current, race_day)
                current.clear()
                current.update(rebuilt)
        prior_eval = historical.get("integratedEvaluation") or {}
        current_eval = current.get("integratedEvaluation") or {}
        if isinstance(prior_eval, dict) and isinstance(current_eval, dict) and "careerProfile" in prior_eval:
            if "careerProfile" not in current_eval:
                current.setdefault("integratedEvaluation", {})["careerProfile"] = copy.deepcopy(prior_eval["careerProfile"])
    if sealed_lock(old):
        return restore_seal(old, out)
    prior = old.get("preRacePrediction")
    if isinstance(prior, dict) and pre_off(prior, old):
        incoming_lock = out.get("preRacePrediction")
        # Protect the first genuinely pre-off archived opinion after post.
        # A later, unverified "forecast" must never overwrite the prior record.
        from arvexq.prediction.prerace_archive import post_at, JST
        from datetime import datetime
        start = post_at(old)
        if start and datetime.now(JST) >= start:
            out["preRacePrediction"] = copy.deepcopy(prior)
        elif not isinstance(incoming_lock, dict):
            out["preRacePrediction"] = copy.deepcopy(prior)
    return out


def guard(body: dict[str, Any], read=fetch_current, *, base: str) -> dict[str, Any]:
    out = copy.deepcopy(body)
    updated = []
    for detail in out.get("details") or []:
        if not isinstance(detail, dict) or not detail.get("id"):
            continue
        old = read(base, str(detail["id"]))
        updated.append(protect_detail(old, detail))
    if out.get("details") is not None:
        out["details"] = updated
    return out


def verify_published(body: dict[str, Any], *, base: str, read=fetch_current) -> list[str]:
    """Detect a concurrent D1 sync that removed or rewrote a pre-race seal.

    This is not a substitute for an atomic Worker-side compare-and-swap,
    but it makes lost archives observable rather than silently claiming success.
    """
    verified: list[str] = []
    for detail in body.get("details") or []:
        if not isinstance(detail, dict) or not detail.get("id"):
            continue
        detail = unpack_full(detail)
        lock = sealed_lock(detail)
        revised = detail.get("modelMarkRevisions") or []
        feature_archive = detail.get("massFeatureArchive")
        horse_archives = {
            int(h.get("horseNumber") or 0): h["careerArchive"]
            for h in detail.get("horses") or []
            if isinstance(h, dict) and isinstance(h.get("careerArchive"), dict)
        }
        if not lock and not revised and not feature_archive and not horse_archives:
            continue
        rid = str(detail["id"])
        actual = read(base, rid)
        if lock:
            current = sealed_lock(actual or {})
            if not current or current != lock:
                raise RuntimeError("D1_SEAL_POST_VERIFY_MISMATCH " + rid)
            bet = detail.get("preRaceBet")
            if isinstance(bet, dict) and (actual or {}).get("preRaceBet") != bet:
                raise RuntimeError("D1_PRE_RACE_BET_POST_VERIFY_MISMATCH " + rid)
        if revised and (actual or {}).get("modelMarkRevisions") != revised:
            raise RuntimeError("D1_MODEL_MARK_REVISION_POST_VERIFY_MISMATCH " + rid)
        if isinstance(feature_archive, dict):
            stored = (actual or {}).get("massFeatureArchive") or {}
            if (stored.get("sha256") != feature_archive.get("sha256")
                    or stored.get("featureHash") != feature_archive.get("featureHash")
                    or stored.get("encoding") != feature_archive.get("encoding")):
                raise RuntimeError("D1_MASS_ARCHIVE_POST_VERIFY_MISMATCH " + rid)
        if horse_archives:
            stored_horses = {int(h.get("horseNumber") or 0):h
                             for h in (actual or {}).get("horses") or [] if isinstance(h,dict)}
            for no, archive in horse_archives.items():
                stored = (stored_horses.get(no) or {}).get("careerArchive") or {}
                if (stored.get("sha256") != archive.get("sha256") or
                        stored.get("encoding") != archive.get("encoding")):
                    raise RuntimeError("D1_CAREER_ARCHIVE_POST_VERIFY_MISMATCH "+rid+":"+str(no))
        verified.append(rid)
    return verified


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--verify-post", action="store_true")
    p.add_argument("--api-base", default=os.getenv("CLOUDFLARE_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev"))
    args=p.parse_args()
    path=Path(args.file)
    body=json.loads(path.read_text(encoding="utf-8"))
    if args.verify_post:
        verified = verify_published(body, base=args.api_base)
        print("D1_SEAL_POST_VERIFY_OK", len(verified), ",".join(verified[:10]))
        return 0
    changed=guard(body, base=args.api_base)
    # Atomic rewrite: never send a partially guarded batch.
    tmp=path.with_name(path.name+".sealed.tmp")
    tmp.write_text(json.dumps(changed,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    tmp.replace(path)
    print("D1_SEAL_GUARD",path.name,"details",len(changed.get("details") or []))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
