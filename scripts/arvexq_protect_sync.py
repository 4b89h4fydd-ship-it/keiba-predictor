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
                # The legacy race route may be absent while the same D1
                # race_details table is still readable from its dedicated
                # display view. Never treat this as "no previous evidence"
                # until the existing read-only view has been checked.
                display_url = (base.rstrip("/") + "/api/race/" +
                    urllib.parse.quote(rid, safe="") +
                    "?view=display&sealguard=" + str(time.time_ns()))
                try:
                    display_req = urllib.request.Request(
                        display_url, headers={"accept":"application/json",
                                              "user-agent":"ARVEXQ-SealGuard/1"}
                    )
                    with urllib.request.urlopen(display_req, timeout=25) as display_resp:
                        display = json.loads(display_resp.read().decode("utf-8"))
                    if not isinstance(display, dict):
                        raise RuntimeError("D1 display response must be object")
                    candidate = display.get("detail")
                    if isinstance(candidate, dict):
                        if str(candidate.get("id") or "") != rid:
                            raise RuntimeError("D1 display returned mismatched race")
                        return candidate
                    if display.get("ok") is not False:
                        raise RuntimeError("D1 display returned no verifiable detail")
                except urllib.error.HTTPError as display_exc:
                    if display_exc.code != 404:
                        raise RuntimeError("D1 seal-guard display lookup failed closed") from display_exc
                # Both full-detail routes explicitly returned 404.
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
            if _projection_tombstone(item):
                # The projection stripped this race's forecast blocks
                # because its stored status is not exactly "ready".
                # The dedicated display view restores the blocks from
                # the sealed pre-off archive server-side; read the
                # stored state through it instead. Fail closed when
                # even the display view cannot produce the forecast:
                # protecting against a tombstone would write the
                # tombstone into storage.
                return _fetch_display_restored(base, rid)
            return item
    if data.get("ok") is False:
        raise RuntimeError("D1 returned failure")
    # The provider explicitly reports no detail; no historical snapshot to merge.
    if not data.get("detail") and not data.get("race") and not data.get("id"):
        return None
    raise RuntimeError("D1 returned a mismatched race")


def _fetch_display_restored(base: str, rid: str) -> dict[str, Any]:
    """Read a tombstoned race's stored detail through the display view.

    The worker's ?view=display route restores the forecast blocks
    from the sealed pre-off archive before serving, so its detail is
    the stored publication, not the projection tombstone. Any
    failure — transport, shape, identity, or a detail that is still
    tombstoned — fails closed: the caller must not protect a sync
    write against state it cannot actually read.
    """
    url = (base.rstrip("/") + "/api/race/" + urllib.parse.quote(rid, safe="")
           + "?view=display&sealguard=" + str(time.time_ns()))
    req = urllib.request.Request(
        url, headers={"accept": "application/json",
                      "user-agent": "ARVEXQ-SealGuard/1"})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            display = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            "D1 seal-guard display restore failed closed: " + str(exc)) from exc
    if not isinstance(display, dict):
        raise RuntimeError("D1 display response must be object")
    candidate = display.get("detail")
    if not isinstance(candidate, dict):
        raise RuntimeError("D1 display returned no verifiable detail")
    if str(candidate.get("id") or "") != rid:
        raise RuntimeError("D1 display returned mismatched race")
    if _projection_tombstone(candidate):
        if _compact_tombstone_stub(candidate):
            # The display view faithfully returned the stored state:
            # the nightly compact left this race as a stub in storage
            # itself, so there is no forecast to restore. Return the
            # stub so the caller judges the write against the real
            # stored state; protect_detail re-checks the same
            # predicate and admits only a result-only write over it.
            return candidate
        raise RuntimeError(
            "D1 display view could not restore the tombstoned forecast: "
            + rid)
    return candidate


def _marker_timestamp(value: Any) -> Any:
    from datetime import datetime
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _rewrite_marker_fresh(stored: Any, incoming: Any) -> bool:
    """Whether an incoming rewritePublish marker may replace the stored one.

    The publish lane (scripts/arvexq_rewrite_publish.py) is the marker's
    only writer, and the marker is the ONLY canonical record of the
    published forecast's post-processing (blendApplied lives nowhere
    else; the lane's upgrade guards and freeze decision key on it).
    A marker-carrying write is a genuine advance of the publication
    only when one of these holds:

    - there is no stored marker yet (first publication);
    - the incoming marker belongs to a different model version than
      the stored one (version succession across lanes; the caller's
      own current-version check still gates acceptance);
    - it IS the stored marker (idempotent re-send of the same
      publication, e.g. a seeded detail round-tripping unchanged);
    - it advances the chain: publishedAt does not move backwards
      and, for a revision-stamped write, the revision links to the
      stored marker — previousReceiptSha256 equals the stored
      marker's receipt, revisionCount is exactly one higher, and
      firstPublishedAt still points at a timestamp of the stored
      publication (the lane stamps either the stored firstPublishedAt
      or, on roster/lane re-issues, the stored publishedAt);
    - over an UNREVISED stored marker, a revision-less write with a
      strictly later publishedAt (fresh re-publication the freeze
      lane does not recognise, e.g. over a retired version's marker
      of the same version string).

    Anything else — a prepared payload seeded before an upgrade being
    re-applied (Depth A rollback), a fast-diagnosis snapshot's
    lightweight preparedMeta (Depth B loss) — is stale and must not
    replace the stored publication.
    """
    if not isinstance(stored, dict):
        return True
    if not isinstance(incoming, dict):
        return False
    if incoming == stored:
        return True
    if (incoming.get("modelVersion")
            and incoming.get("modelVersion") != stored.get("modelVersion")):
        return True
    incoming_at = _marker_timestamp(incoming.get("publishedAt"))
    stored_at = _marker_timestamp(stored.get("publishedAt"))
    if incoming_at is None or stored_at is None or incoming_at < stored_at:
        return False
    revision = incoming.get("revision")
    stored_revision = stored.get("revision")
    if isinstance(revision, dict):
        stored_count = (stored_revision.get("revisionCount")
                        if isinstance(stored_revision, dict) else 0)
        if not isinstance(stored_count, int) or isinstance(stored_count, bool):
            stored_count = 0
        stored_firsts = {stored.get("publishedAt")}
        if stored.get("firstPublishedAt"):
            stored_firsts.add(stored.get("firstPublishedAt"))
        return (
            revision.get("previousReceiptSha256") is not None
            and revision.get("previousReceiptSha256")
            == stored.get("receiptSha256")
            and revision.get("revisionCount") == stored_count + 1
            and incoming.get("firstPublishedAt") in stored_firsts)
    if isinstance(stored_revision, dict):
        # A revision-less marker never succeeds a revised publication.
        return False
    return incoming_at > stored_at


_FORECAST_BLOCK_KEYS = ("predictionStatus", "predictionModelVersion",
                        "prediction", "predictionMarks", "recommendedBets")
_AUTHORIZED_MODEL_VERSIONS = frozenset((
    "arvexq-stage64-product-v1", "arvexq-rewrite-v1-uncalibrated-prior",
    "arvexq-rewrite-v2-elo-speed2", "arvexq-rewrite-v3-v9b"))
_MARK_LABELS = ("◎", "○", "▲", "△", "☆")


def _projection_tombstone(detail: dict[str, Any]) -> bool:
    """Whether this read carries the API worker's projection tombstone.

    The kraiz-api GET projection (publicRace / authorizedStage64)
    honours only a stored detail whose top-level predictionStatus is
    exactly "ready". Anything else is served as predictionStatus
    "disabled" / predictionModelVersion "arvexq-prediction-removed"
    with the prediction and predictionMarks blocks stripped. Those
    two fields are the projection's values, not the stored detail's.
    """
    return (detail.get("predictionStatus") == "disabled"
            and detail.get("predictionModelVersion")
            == "arvexq-prediction-removed")


_RESULT_ONLY_WRITE_KEYS = frozenset(("result", "resultCname", "payouts"))
_FORECAST_CONTENT_KEYS = ("unifiedForecast", "prediction", "predictionMarks",
                          "recommendedBets", "preoffStage64Archive")
_MISSING = object()


def _compact_tombstone_stub(detail: dict[str, Any]) -> bool:
    """Whether this detail is a nightly-compact tombstone IN STORAGE.

    The D1 nightly compact replaces a finished race's stored detail
    with a summary stub and stamps it ``predictionStatus="disabled"``
    / ``predictionModelVersion="arvexq-prediction-removed"`` — the
    same stamps the worker's read projection puts on a tombstoned
    read, but here the stored bytes themselves are the stub (the
    compact envelope unpacks to the stub; the original detail is
    gone).  The compact provenance (``compactedFrom``) plus the
    absence of the card and of every forecast block distinguish it
    from a projection tombstone of a live race, whose stored detail
    still carries horses and whose read never carries the compact
    markers.  A compact tombstone that kept a pre-off archive is NOT
    matched here: the archive-restore path owns it, as before.
    """
    if not isinstance(detail, dict) or not _projection_tombstone(detail):
        return False
    if not detail.get("compactedFrom"):
        return False
    if detail.get("horses"):
        return False
    return not any(detail.get(key) for key in _FORECAST_CONTENT_KEYS)


def _changed_keys(old: dict[str, Any], incoming: dict[str, Any]) -> set:
    changed = set()
    for key in set(old) | set(incoming):
        if old.get(key, _MISSING) != incoming.get(key, _MISSING):
            changed.add(key)
    return changed


def _compact_tombstone_result_write(old: dict[str, Any],
                                    incoming: dict[str, Any]) -> bool:
    """The single narrow exception to the tombstone fail-closed rule.

    A result-only repair write over a compact tombstone: the stored
    detail holds no forecast at all (no blocks, no archive), so there
    is nothing to restore and nothing a write could destroy; the
    write may change ONLY the result/payout fields.  Anything wider
    is refused here and fails closed in the caller, exactly like
    every other unverifiable tombstone.
    """
    if not _compact_tombstone_stub(old):
        return False
    return _changed_keys(old, incoming) <= _RESULT_ONLY_WRITE_KEYS


def _authorized_forecast(detail: dict[str, Any]) -> bool:
    """Python mirror of the worker's authorizedStage64 gate."""
    prediction = detail.get("prediction")
    if detail.get("predictionStatus") != "ready":
        return False
    if not isinstance(prediction, dict):
        return False
    if prediction.get("predictionStatus") != "ready":
        return False
    if prediction.get("productionEligible") is not True:
        return False
    if prediction.get("modelVersion") not in _AUTHORIZED_MODEL_VERSIONS:
        return False
    if prediction.get("raceId") != detail.get("id"):
        return False
    if prediction.get("date") != detail.get("date"):
        return False
    horses = detail.get("horses")
    marks = detail.get("predictionMarks")
    if not isinstance(horses, list) or not isinstance(marks, list):
        return False
    if len(marks) != 5:
        return False
    known = {h.get("horseNumber") for h in horses if isinstance(h, dict)}
    used: set[Any] = set()
    for index, row in enumerate(marks):
        if not isinstance(row, dict) or row.get("mark") != _MARK_LABELS[index]:
            return False
        number = row.get("horseNumber")
        if not isinstance(number, int) or isinstance(number, bool):
            return False
        if number not in known or number in used:
            return False
        used.add(number)
    return True


def _marks_map(entries: Any, *keys: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(entries, list):
        return out
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        label = next((entry.get(k) for k in keys if entry.get(k)), None)
        if label:
            out[str(label)] = entry.get("horseNumber")
    return out


def _assert_publish_marks_consistent(detail: dict[str, Any]) -> None:
    """A publish write must carry ONE marks assignment.

    The detail carries the marks twice (predictionMarks for the entry
    list, unifiedForecast.marks for the race view). The blend-upgrade
    reissues of 2026-11-07/08 stored details whose two blocks named
    different horses (the first publication's predictionMarks beside
    the reissue's unifiedForecast), so the app showed two different
    ◎ for the same race. Both blocks derive from one forecast in the
    publish lane, so a disagreement means the write was assembled
    from two different publications: fail closed rather than store
    it. Only the five labelled marks are compared; attention-only
    overlay entries (empty mark) are not part of the assignment.
    """
    pm = _marks_map(detail.get("predictionMarks"), "mark")
    uf = _marks_map((detail.get("unifiedForecast") or {}).get("marks"),
                    "markSymbol", "mark")
    if len(pm) == 5 and len(uf) == 5 and pm != uf:
        raise RuntimeError(
            "publish write carries inconsistent marks blocks "
            "(predictionMarks vs unifiedForecast.marks) for "
            + str(detail.get("id") or ""))


def _archive_restored_detail(detail: dict[str, Any]) -> dict[str, Any] | None:
    """Rebuild the stored view of a tombstoned read from its archive.

    The sealed pre-off archive (preoffStage64Archive) inside the read
    carries the publication's forecast blocks verbatim. It is trusted
    only after the worker-equivalent verification: identity match
    against the race, the full authorization gate over the archived
    blocks with the race's current roster, and a bet list present.
    """
    archive = detail.get("preoffStage64Archive")
    if not isinstance(archive, dict):
        return None
    if archive.get("raceId") != detail.get("id"):
        return None
    if archive.get("raceDate") != detail.get("date"):
        return None
    if not isinstance(archive.get("recommendedBets"), list):
        return None
    candidate = dict(archive)
    candidate["id"] = detail.get("id")
    candidate["date"] = detail.get("date")
    candidate["horses"] = detail.get("horses")
    if not _authorized_forecast(candidate):
        return None
    restored = copy.deepcopy(detail)
    for key in _FORECAST_BLOCK_KEYS:
        if key in archive:
            restored[key] = copy.deepcopy(archive[key])
    return restored


_FORECAST_REVISION_VERSION = "arvexq-forecast-revision-v1"


def _forecast_revision_digest(value: Any) -> str:
    from hashlib import sha256
    return sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()


def _latest_forecast_revision(detail: dict[str, Any]) -> dict[str, Any] | None:
    revisions = detail.get("forecastRevisions") or []
    current = detail.get("currentForecastRevisionId")
    matches = [r for r in revisions
               if isinstance(r, dict) and r.get("revisionId") == current
               and r.get("version") == _FORECAST_REVISION_VERSION
               and r.get("raceId") == detail.get("id")
               and r.get("raceDate") == detail.get("date")]
    if len(matches) != 1:
        return None
    revision = matches[0]
    expected = _forecast_revision_digest(
        {k: v for k, v in revision.items()
         if k not in ("revisionId", "createdAt")})
    return revision if expected == current else None


def _preserve_forecast_revisions(previous: dict[str, Any],
                                 incoming: dict[str, Any]) -> dict[str, Any]:
    """Retain immutable revision history across writes; reject divergent chains.

    Inlined verbatim from the retired arvexq.prediction.forecast_revisions
    module: protect is the chain's last production reader, and its
    accept/reject behaviour here is unchanged (stage-2 differential
    corpus, 2026-11-10).
    """
    out = copy.deepcopy(incoming)
    old = previous.get("forecastRevisions") or []
    proposed = out.get("forecastRevisions") or []
    if proposed[:len(old)] != old:
        if proposed:
            raise ValueError("forecast revision history prefix changed")
        out["forecastRevisions"] = copy.deepcopy(old)
        if previous.get("currentForecastRevisionId"):
            out["currentForecastRevisionId"] = \
                previous["currentForecastRevisionId"]
    if (out.get("currentForecastRevisionId")
            and _latest_forecast_revision(out) is None):
        raise ValueError("current forecast revision pointer is invalid")
    return out


def protect_detail(old: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    if FULL_PAYLOAD_KEY in incoming:
        # Archive protection must edit the real original, then recompress it.
        # Editing only the compact index would leave the full original unprotected.
        return pack_full(protect_detail(unpack_full(old) if isinstance(old, dict) else old, unpack_full(incoming)))
    if isinstance(old, dict) and FULL_PAYLOAD_KEY in old:
        old = unpack_full(old)
    if isinstance(old, dict) and _projection_tombstone(old):
        # Restoring forecast blocks FROM a tombstoned read would write
        # the tombstone itself into storage: the projection's status
        # values would replace the stored ones and the stripped blocks
        # would be deleted from the incoming write. That is exactly
        # how nine races lost their stored prediction blocks on
        # 2026-11-05 after a projection-shaped write flipped their
        # stored status. Restore the stored view from the sealed
        # pre-off archive instead, or fail closed.
        restored = _archive_restored_detail(old)
        if restored is not None:
            old = restored
        elif not _compact_tombstone_result_write(old, incoming):
            raise RuntimeError(
                "stored forecast is tombstoned in the API projection "
                "and carries no verified pre-off archive; failing "
                "closed rather than restoring from the tombstone: "
                + str(old.get("id") or ""))
        # Otherwise the write is result-only over a compact tombstone
        # that holds no forecast blocks at all: keep the stub as `old`.
        # The generic protection below still restores every
        # forecast-shaped key from it (the stub shares only the status
        # stamps and text with the write) and the genuine-publish path
        # can never trigger, because the write's status is not "ready".
    out = copy.deepcopy(incoming)
    if not isinstance(old, dict):
        return out
    out = _preserve_forecast_revisions(old, out)
    # Forecast blocks are owned by the rewrite publish lane
    # (scripts/arvexq_rewrite_publish.py). Any other lane's write preserves
    # the stored forecast blocks verbatim and drops its own forecast fields;
    # only a genuine publish-lane write may replace them. (This replaces the
    # former first-receipt-wins rule that pinned forecasts to the retired
    # learned-scenarios model.)
    #
    # A genuine publish write is recognised by the lane's
    # preparedMeta.rewritePublish marker AND the complete forecast block
    # set: build_publish_detail always emits every block atomically. The
    # marker alone is NOT sufficient — lanes seeded from a stored detail
    # inherit preparedMeta (prefetch merges it by update), so a marker-only
    # check let display-compacted details (which pass through
    # arvexq.forecast.publication.public_race and lose the bet blocks)
    # overwrite the published forecast, leaving the app with
    # predictionStatus 'disabled' and no recommendedBets.
    from arvexq.prediction.unified_product import MODEL_VERSION as REWRITE_MODEL_VERSION
    forecast_keys = ('unifiedForecast', 'prediction', 'predictionMarks',
                     'recommendedBets', 'forecastText', 'predictionStatus',
                     'predictionModelVersion', 'preRaceBet')
    marker = ((out.get('preparedMeta') or {}).get('rewritePublish') or {})
    stored_marker = (old.get('preparedMeta') or {}).get('rewritePublish')
    # The marker check above is necessary but not sufficient: a detail
    # seeded from a stored publication inherits the marker verbatim, so
    # a stale seed re-applied after a revision (blend upgrade) carries
    # a complete, current-version marker over an OLD forecast and used
    # to roll the publication back to its first-published state. The
    # write must also ADVANCE the marker chain (see
    # _rewrite_marker_fresh). (2026-11-04: 13 races rolled back this
    # way; 4 more lost the marker entirely to a lightweight
    # preparedMeta overwrite — closed by the field merge below.)
    # Completeness is judged against the blocks the STORED detail
    # actually carries, not an absolute list: the stored product may
    # itself lack a block (preRaceBet is stripped before storage on
    # the current chain, so no stored detail carries it), and the
    # lane's surgical re-issues (place-EV upgrade) are built from the
    # stored detail and inherit that absence — reverting them for it
    # made every place-EV upgrade fail its read-back on 2026-11-04.
    # A write that DROPS a block the stored detail carries (the
    # display-compaction case above) is still not a publish write.
    # A genuine publish write also always carries the lane's own
    # top-level status: build_publish_detail stamps predictionStatus
    # "ready", and the surgical upgrades derive from a ready read.
    # A write whose status reads "unified-reference-ready" passed
    # through the Python delivery projection (public_race) on its way
    # here — a display-compacted seed, not a publication. Letting it
    # through as a publish write stores the projection's vocabulary
    # in D1, where the worker projection then tombstones the race
    # (2026-11-05 flip). Such writes go through the restore branch
    # below, which keeps the stored status and blocks.
    is_publish_write = (
        marker.get('modelVersion') == REWRITE_MODEL_VERSION
        and out.get('predictionStatus') == 'ready'
        and all(key in out for key in forecast_keys if key in old)
        and _rewrite_marker_fresh(stored_marker, marker))
    if is_publish_write:
        _assert_publish_marks_consistent(out)
    if not is_publish_write:
        for key in forecast_keys:
            if key in old:
                out[key] = copy.deepcopy(old[key])
            else:
                out.pop(key, None)
        # preparedMeta is field-merged, never replaced wholesale: the
        # incoming write stays the base (its own lane bookkeeping —
        # live updates, prefetch epochs — still lands), but the
        # rewritePublish marker is publish-lane property and is
        # carried over from the stored detail. blendApplied and the
        # revision chain exist only inside the marker, so losing it
        # unfreezes the race and blocks every marker-keyed guard.
        if isinstance(stored_marker, dict):
            merged_meta = dict(out.get('preparedMeta') or {})
            merged_meta['rewritePublish'] = copy.deepcopy(stored_marker)
            out['preparedMeta'] = merged_meta
    # The experimental 18-factor master sidecar belongs to the same
    # pre-off rewrite publish lane as the forecast. Prefetch/live/result
    # syncs often send thin details and must never erase its evidence,
    # timestamp, or signature. Nor may they inject a forged candidate.
    # The unified receipt and production marks are intentionally separate.
    if not is_publish_write:
        if 'masterAnalysis' in old:
            out['masterAnalysis'] = copy.deepcopy(old['masterAnalysis'])
        else:
            out.pop('masterAnalysis', None)
    elif 'masterAnalysis' in out:
        from hashlib import sha256
        sidecar = out['masterAnalysis']
        if not isinstance(sidecar, dict) or sidecar.get('version') != 'master-18-factor-shadow-v1':
            raise ValueError('invalid masterAnalysis publication identity')
        digest = sidecar.get('contentSha256')
        unsigned = {k: v for k, v in sidecar.items() if k != 'contentSha256'}
        expected = sha256(json.dumps(
            unsigned, sort_keys=True, separators=(',', ':'),
            ensure_ascii=False).encode('utf-8')).hexdigest()
        if (digest != expected or sidecar.get('capturedAt') !=
                (out.get('prediction') or {}).get('capturedAt')):
            raise ValueError('masterAnalysis signature or capture mismatch')
    elif 'masterAnalysis' in old:
        # A surgical publication may update only odds or a ticket
        # formation; retaining the prior research seal is preferable
        # to silently discarding the already captured comparison.
        out['masterAnalysis'] = copy.deepcopy(old['masterAnalysis'])
    # Kyoto G1 emergency learned candidate is an immutable pre-off research
    # artifact. Later odds/results or a failed full-day prefetch may not erase
    # or forge it. Ignore a changed challenger from the same race entirely.
    from arvexq.prediction.kikka_urgent import RACE_ID, candidate_marks
    if str(old.get('id') or '') == RACE_ID:
        original_marks = candidate_marks(old)
        if original_marks:
            # D1 retains the authentic before-off 'mark' originals, but the
            # display projection removes the legacy 'mark' key. Supply an
            # ADDITIVE markSymbol transport alias instead of overwriting the
            # real protected marks, model hash, capture time or source hash.
            original = copy.deepcopy(old['kikkaCandidate'])
            if isinstance(original.get('marks'), list):
                for row in original['marks']:
                    if isinstance(row, dict) and row.get('mark') and not row.get('markSymbol'):
                        row['markSymbol'] = row['mark']
            out['kikkaCandidate'] = original
            if candidate_marks(out) != original_marks:
                raise ValueError('Kikuka display symbol alias did not preserve original hash')
        elif 'kikkaCandidate' in old:
            # Oct 25 D1 had marks that LOST their literal "mark" key in an
            # old projection. It still preserves the authentic model/source
            # SHA256. Repair ONLY the exact same before-off original hash,
            # using newly generated, independently verified symbol fields.
            # Do not modify a legitimate original or admit arbitrary new tips.
            from arvexq.pipeline.persisted_inputs import may_create_prerace_prediction
            old_c = old['kikkaCandidate']
            new_c = out.get('kikkaCandidate')
            same_original = (isinstance(old_c, dict) and isinstance(new_c, dict)
                             and old_c.get('modelHash') == new_c.get('modelHash')
                             and old_c.get('sourceHash') == new_c.get('sourceHash')
                             and old_c.get('raceId') == new_c.get('raceId')
                             and old_c.get('capturedAt') and new_c.get('capturedAt'))
            if same_original and candidate_marks(out) and may_create_prerace_prediction(out):
                # Keep the first real model's original pre-off capture time.
                new_c['capturedAt'] = old_c['capturedAt']
                if candidate_marks(out) is None:
                    raise ValueError('Kikuka original capture timestamp invalid')
                out['kikkaCandidate'] = new_c
            else:
                # Preserve even the invalid original bytes instead of erasing
                # historic evidence or letting a foreign update overwrite it.
                out['kikkaCandidate'] = copy.deepcopy(old_c)
        elif 'kikkaCandidate' in out and candidate_marks(out) is None:
            raise ValueError('new Kikuka challenger cannot be verified')
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
    # Stored revision chains are preserved verbatim; a write that lacks
    # them never erases them. The former append allowances are retired
    # with their generators (stage 2, 2026-11-10): the official append
    # required a morning snapshot no writer has produced since the
    # 2026-10-28 cutover, the user-approved append is date-locked to
    # 2026-10-09 by its enable switch, and no stored detail carries
    # either chain (MotherDuck census 2026-11-10: 0 of 1,340 rows).
    previous_revisions = old.get("officialMarkRevisions")
    if isinstance(previous_revisions, list) and previous_revisions:
        out["officialMarkRevisions"] = copy.deepcopy(previous_revisions)
    previous_models = old.get("modelMarkRevisions")
    if isinstance(previous_models, list) and previous_models:
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


def _all_original_career_evidence_retained(expected: dict[str, Any],
                                           actual: dict[str, Any], race_date: str) -> bool:
    """Accept a concurrent *richer* archive only after full recovery and proof.

    Different SHA alone does not indicate lost data: another authorised writer
    can add older starts or previously absent fields after a successful sync.
    A compact five-run display, bad digest, changed original observation or
    removed historical start must still fail closed.
    """
    from arvexq.ingest.career_transport import recover_horse
    from arvexq.ingest.full_career import merge_career
    if not (isinstance(expected.get("careerArchive"), dict) and
            isinstance(actual.get("careerArchive"), dict) and race_date):
        return False
    try:
        lhs = recover_horse(expected, race_date)
        rhs = recover_horse(actual, race_date)
        previous = merge_career(lhs.get("allPastRuns"), lhs.get("recentRaces"), race_date)
        retained = merge_career(rhs.get("allPastRuns"), rhs.get("recentRaces"), race_date)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError):
        return False
    if not previous or len(retained) < len(previous):
        return False
    current_by_date = {r["date"]: r for r in retained}
    def contains(richer: Any, original: Any) -> bool:
        if isinstance(original, dict):
            return isinstance(richer, dict) and all(
                key in richer and contains(richer[key], value)
                for key, value in original.items())
        if isinstance(original, list):
            return isinstance(richer, list) and len(richer) >= len(original) and all(
                contains(richer[i], value) for i, value in enumerate(original))
        return richer == original
    return all(r["date"] in current_by_date and contains(current_by_date[r["date"]], r)
               for r in previous)


def _verify_one_published_detail(detail: dict[str, Any], actual: dict[str, Any] | None) -> None:
    rid = str(detail["id"])
    if isinstance(actual, dict):
        # The public horses array is only a compact index when the complete
        # saved original is carried in arvexqFullPayload. Verify that original
        # before comparing nested archive evidence.
        try:
            actual = unpack_full(actual)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise RuntimeError("D1_FULL_PAYLOAD_POST_VERIFY_INVALID " + rid) from exc
        if not isinstance(actual, dict) or str(actual.get("id") or "") != rid:
            raise RuntimeError("D1_RACE_ID_POST_VERIFY_MISMATCH " + rid)
    lock = sealed_lock(detail)
    revised = detail.get("modelMarkRevisions") or []
    feature_archive = detail.get("massFeatureArchive")
    horse_archives = {
        int(h.get("horseNumber") or 0): h["careerArchive"]
        for h in detail.get("horses") or []
        if isinstance(h, dict) and isinstance(h.get("careerArchive"), dict)
    }
    if lock:
        current = sealed_lock(actual or {})
        if not current or current != lock:
            raise RuntimeError("D1_SEAL_POST_VERIFY_MISMATCH " + rid)
        bet = detail.get("preRaceBet")
        if isinstance(bet, dict) and (actual or {}).get("preRaceBet") != bet:
            raise RuntimeError("D1_PRE_RACE_BET_POST_VERIFY_MISMATCH " + rid)
    from arvexq.prediction.unified_product import verified as verified_unified
    requested_unified = verified_unified(detail)
    if requested_unified:
        final_unified = verified_unified(actual or {})
        if (not final_unified or
                final_unified.get('receiptSha256') != requested_unified['receiptSha256']):
            raise RuntimeError('D1_UNIFIED_FORECAST_MARKS_POST_VERIFY_MISMATCH ' + rid)
    if revised and (actual or {}).get("modelMarkRevisions") != revised:
        raise RuntimeError("D1_MODEL_MARK_REVISION_POST_VERIFY_MISMATCH " + rid)
    if isinstance(feature_archive, dict):
        stored = (actual or {}).get("massFeatureArchive") or {}
        if (stored.get("sha256") != feature_archive.get("sha256")
                or stored.get("featureHash") != feature_archive.get("featureHash")
                or stored.get("encoding") != feature_archive.get("encoding")):
            raise RuntimeError("D1_MASS_ARCHIVE_POST_VERIFY_MISMATCH " + rid)
    if horse_archives:
        stored_horses = {int(h.get("horseNumber") or 0): h
                         for h in (actual or {}).get("horses") or [] if isinstance(h, dict)}
        for no, archive in horse_archives.items():
            stored = (stored_horses.get(no) or {}).get("careerArchive") or {}
            if stored.get("sha256") == archive.get("sha256") and stored.get("encoding") == archive.get("encoding"):
                continue
            expected_horse = next(
                (h for h in detail.get("horses") or []
                 if isinstance(h, dict) and int(h.get("horseNumber") or 0) == no), {})
            actual_horse = stored_horses.get(no) or {}
            if not _all_original_career_evidence_retained(
                    expected_horse, actual_horse, str(detail.get("date") or "")):
                raise RuntimeError("D1_CAREER_ARCHIVE_POST_VERIFY_MISMATCH "+rid+":"+str(no))
            print("D1_CAREER_ARCHIVE_RICHER_PRESERVED", rid, no,
                  "requested="+str(archive.get("storedRunCount")),
                  "actual="+str(stored.get("storedRunCount")))


def verify_published(body: dict[str, Any], *, base: str, read=fetch_current,
                     retry_delays: tuple[float, ...] = (0.5, 1.5),
                     sleeper=time.sleep) -> list[str]:
    """Verify server-authoritative archives with bounded D1 read-back retries.

    A successful D1 write may be briefly invisible to a different read replica.
    Only an actual hash/content match or a proven richer, lossless archive is
    accepted. A persistently stale/missing/replaced observation still fails.
    """
    verified: list[str] = []
    for item in body.get("details") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        detail = unpack_full(item)
        lock = sealed_lock(detail)
        revised = detail.get("modelMarkRevisions") or []
        feature_archive = detail.get("massFeatureArchive")
        horse_archives = [
            h for h in detail.get("horses") or []
            if isinstance(h, dict) and isinstance(h.get("careerArchive"), dict)
        ]
        if not lock and not revised and not feature_archive and not horse_archives and not detail.get('unifiedForecast'):
            continue
        rid = str(detail["id"])
        for attempt in range(len(retry_delays) + 1):
            actual = read(base, rid)
            try:
                _verify_one_published_detail(detail, actual)
                break
            except RuntimeError as exc:
                if attempt == len(retry_delays):
                    raise
                print("D1_POST_VERIFY_RETRY", rid, type(exc).__name__,
                      "attempt="+str(attempt + 1))
                sleeper(retry_delays[attempt])
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
