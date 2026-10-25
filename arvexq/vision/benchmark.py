"""Auditable tracking accuracy against independently labelled horse identities.

No annotation = no accuracy estimate. Anonymous ByteTrack IDs are NEVER
treated as horse numbers. The reference manifest is supplied separately
and explicitly declares independent human review. This code computes only
geometric and identity matching on provided time-stamped video frames.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite

VERSION = "arvexq-vision-ground-truth-benchmark-v1"


def _box(raw):
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError("bbox must have four pixel coordinates")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
           for v in raw):
        raise ValueError("invalid or non-finite bbox coordinate")
    x1, y1, x2, y2 = map(float, raw)
    if not x1 < x2 or not y1 < y2:
        raise ValueError("bbox has invalid area")
    return x1, y1, x2, y2


def _iou(a, b):
    l, t = max(a[0], b[0]), max(a[1], b[1])
    r, d = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, r - l) * max(0.0, d - t)
    aa = (a[2] - a[0]) * (a[3] - a[1])
    bb = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / (aa + bb - intersection)


def _optimal_pairs(weights):
    """Maximum weight bipartite assignment, pure Python Hungarian O(n^3).

    A zero-weight edge represents unmatched observations. Large cardinality
    reward ensures no valid geometric match gets traded away for high IoU.
    """
    nr = len(weights)
    nc = len(weights[0]) if nr else 0
    if not nr or not nc:
        return []
    size = max(nr, nc)
    padded = [[weights[i][j] if i < nr and j < nc else 0.0
               for j in range(size)] for i in range(size)]
    # Hungarian minimum cost assignment (negative weights).
    u, v = [0.] * (size + 1), [0.] * (size + 1)
    p, way = [0] * (size + 1), [0] * (size + 1)
    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minv = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], float("inf"), 0
            for j in range(1, size + 1):
                if used[j]:
                    continue
                cur = -padded[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j], way[j] = cur, j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    return [(p[j] - 1, j - 1) for j in range(1, size + 1)
            if 0 < p[j] <= nr and j <= nc and weights[p[j] - 1][j - 1] > 0]


def _seconds(row):
    value = row.get("seconds")
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError("non-negative finite frame timestamp required")
    return round(float(value), 3)


def _indexed_frames(frames, key, id_key):
    if not isinstance(frames, list) or not frames:
        raise ValueError("non-empty, frame-complete label lists required")
    entries, prev = {}, -1.
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("invalid frame")
        t = _seconds(frame)
        if t <= prev:
            raise ValueError("strict chronological nonduplicate timestamps required")
        prev = t
        objects = frame.get(key)
        if not isinstance(objects, list):
            raise ValueError("every frame must list its horses, including empty frames")
        seen = set()
        normalized = []
        for item in objects:
            if not isinstance(item, dict) or id_key not in item:
                raise ValueError("horse/track identity is required")
            identity = item[id_key]
            if id_key == "horseId":
                if not isinstance(identity, str) or not identity.strip():
                    raise ValueError("ground truth requires nonempty stable horseId")
            elif type(identity) is not int or identity < 0:
                raise ValueError("predicted trackId must be a nonnegative integer")
            if identity in seen:
                raise ValueError("duplicate identity within frame")
            seen.add(identity)
            normalized.append((identity, _box(item.get("bbox"))))
        entries[t] = normalized
    return entries


def evaluate_labels(predicted: dict, ground_truth: dict, *, min_iou=0.5) -> dict:
    if not isinstance(predicted, dict) or not isinstance(ground_truth, dict):
        raise ValueError("both prediction and independent truth manifests required")
    hashval = predicted.get("sourceVideoSha256")
    if not isinstance(hashval, str) or len(hashval) != 64 or (
        hashval != ground_truth.get("videoSha256")
    ):
        raise ValueError("video SHA256 mismatch between prediction and annotation")
    attestation = ground_truth.get("annotation") or {}
    if (attestation.get("method") != "independent-manual-review"
            or attestation.get("reviewed") is not True
            or not str(attestation.get("annotator") or "").strip()
            or not str(attestation.get("version") or "").strip()
            or attestation.get("usedModelPredictionsAsTruth") is not False):
        raise ValueError("independent human-reviewed annotations required")
    if not 0 < min_iou <= 1:
        raise ValueError("valid IoU threshold required")
    pred = _indexed_frames(predicted.get("observedFrames"), "tracks", "trackId")
    truth = _indexed_frames(ground_truth.get("frames"), "horses", "horseId")
    if pred.keys() != truth.keys():
        raise ValueError("annotations must cover exactly every sampled frame")
    num_gt = sum(len(h) for h in truth.values())
    num_pred = sum(len(h) for h in pred.values())
    if num_gt == 0:
        raise ValueError("no labelled horses, accuracy is not measurable")
    correlations = defaultdict(int)
    temporal_matches = defaultdict(list)
    matches = 0
    for fi, stamp in enumerate(pred):
        labelled, tracks = truth[stamp], pred[stamp]
        edges = [[100 + overlap if overlap >= min_iou else 0.0
                  for _, pb in tracks for overlap in [_iou(gb, pb)]]
                 for _, gb in labelled]
        pairs = _optimal_pairs(edges)
        matches += len(pairs)
        for row, col in pairs:
            horse_id, track_id = labelled[row][0], tracks[col][0]
            correlations[(horse_id, track_id)] += 1
            temporal_matches[horse_id].append((fi, track_id))
    horse_ids = sorted({h for h, _ in correlations})
    tracker_ids = sorted({t for _, t in correlations})
    idpairs = _optimal_pairs([[correlations[(h, t)] for t in tracker_ids]
                              for h in horse_ids])
    idtp = sum(correlations[(horse_ids[i], tracker_ids[j])] for i, j in idpairs)
    switches = 0
    for observations in temporal_matches.values():
        for (frame_a, old_track), (frame_b, new_track) in zip(
            observations, observations[1:]
        ):
            if frame_b == frame_a + 1 and old_track != new_track:
                switches += 1
    precision = matches / num_pred if num_pred else None
    recall = matches / num_gt
    idf1 = 2 * idtp / (num_gt + num_pred) if (num_gt + num_pred) else None
    return {
        "version": VERSION,
        "sourceVideoSha256": hashval,
        "independentLabelAttestation": attestation,
        "sampledFrames": len(truth),
        "truthHorseInstances": num_gt,
        "predictedTrackInstances": num_pred,
        "matchedHorseInstances": matches,
        "falsePositiveTrackInstances": num_pred - matches,
        "missedHorseInstances": num_gt - matches,
        "detectionPrecisionAtIou": round(precision, 5) if precision is not None else None,
        "detectionRecallAtIou": round(recall, 5),
        "iouThreshold": min_iou,
        "identityTruePositives": idtp,
        "identityF1": round(idf1, 5) if idf1 is not None else None,
        "adjacentMatchedIdentitySwitches": switches,
        "stableIdentityLabelsInTruth": len({h for frame in truth.values() for h, _ in frame}),
        "provenForJapan": False,
        "productionPredictionApplied": False,
        "notes": "Ground-truth-attested clip only; no Japanese racing or ROI conclusion.",
    }
