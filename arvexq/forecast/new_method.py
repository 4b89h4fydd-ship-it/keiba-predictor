"""ARVEXQ replacement forecaster: ability + INTERNAL video + race development -> probability -> marks -> tickets.

No Stage63/64 execution. No raw footage, camera images, or internal video metrics
are published. Model coefficients and scenario frequencies must be independently
trained and calibrated BEFORE the target race; absence fails closed.
"""
from __future__ import annotations

from datetime import date
from itertools import permutations
from math import exp, isfinite
from pathlib import Path
import json
import os

VERSION = "arvexq-three-analysis-vnext-1"
MARKS = ("◎", "○", "▲", "△", "☆")
FEATURES = ("form", "win_rate", "top3_rate", "distance_form", "margin",
            "early_position", "frame", "pace_pressure", "video_speed",
            "video_start", "video_extra_distance", "video_slowdowns",
            "video_missing")
CIRCUITS = ("中央", "地方")
SCENARIOS = ("baseline", "fast", "slow")


def number(x):
    if x is None or x == "":
        return None
    try:
        y = float(x)
        return y if isfinite(y) else None
    except (TypeError, ValueError):
        return None


def active(h):
    return (isinstance(h, dict) and type(h.get("horseNumber")) is int and
            not any(h.get(k) for k in ("scratched", "cancelled", "withdrawn")) and
            str(h.get("status") or "") not in ("出走取消", "競走除外", "取消", "除外"))


def history(h, cutoff):
    by_id = {}
    for field in ("recentRaces", "allPastRuns"):
        for r in h.get(field) or []:
            if not isinstance(r, dict):
                continue
            day = str(r.get("_raceDate") or r.get("date") or "")
            if len(day) != 10 or day >= cutoff:
                continue
            try:
                date.fromisoformat(day)
            except ValueError:
                continue
            if r.get("surface") in ("障害", "ばんえい"):
                continue
            key = (day, str(r.get("track") or ""), str(r.get("raceNumber") or ""))
            other = by_id.get(key)
            if other is not None and (other.get("finish") != r.get("finish")):
                raise ValueError("conflicting historical finish")
            if other is None or len(r) > len(other):
                by_id[key] = r
    return [by_id[k] for k in sorted(by_id, reverse=True)]


def _finish_quality(r):
    n, f = number(r.get("fieldSize")), number(r.get("finish"))
    return (n - f) / (n - 1) if n is not None and n > 1 and f is not None and 1 <= f <= n else None


def _mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _video_for(h, video):
    """Only permanently identified, verified HISTORICAL video feature records."""
    sid = h.get("id") or h.get("horseId")
    rec = (video or {}).get(str(sid)) if sid is not None else None
    if rec is None:
        return None
    if not isinstance(rec, dict) or rec.get("identityVerified") is not True or rec.get("geometryCalibrated") is not True:
        raise ValueError("video identity and meter-scale camera geometry unverified")
    if rec.get("coordinateUnit") != "meter":
        raise ValueError("pixel motion cannot be treated as meters")
    return rec


def extract(race, *, videos=None):
    """Three separate evidence boxes. video data never becomes a public output."""
    if not isinstance(race, dict) or race.get("circuit") not in CIRCUITS:
        raise ValueError("JRA/NAR circuit must be explicit")
    cutoff = str(race.get("date") or "")
    date.fromisoformat(cutoff)
    if race.get("track") in ("帯広", "帯広ば") or race.get("analysisMode") in ("障害", "ばんえい"):
        raise ValueError("unsupported discipline")
    if race.get("result"):
        raise ValueError("outcome-bearing race input is forbidden for live inference")
    horses = sorted((h for h in race.get("horses") or [] if active(h)), key=lambda h: h["horseNumber"])
    numbers = [h["horseNumber"] for h in horses]
    if len(numbers) < 3 or len(set(numbers)) != len(numbers):
        raise ValueError("invalid field")
    early = {}
    ability = {}
    video_summary = {}
    for h in horses:
        no = h["horseNumber"]
        rows = history(h, cutoff)
        qs = [_finish_quality(r) for r in rows]
        valid = [v for v in qs if v is not None]
        early_positions = []
        for r in rows:
            corners = r.get("cornerPositions") or r.get("passing") or []
            n = number(r.get("fieldSize"))
            p = number(corners[0]) if isinstance(corners, list) and corners else None
            if p is not None and n is not None and n > 1 and 1 <= p <= n:
                early_positions.append((p - 1) / (n - 1))
        early[no] = _mean(early_positions[:5])
        comparable = [r for r in rows if r.get("surface") == race.get("surface")
                      and abs((number(r.get("distance")) or 0) - (number(race.get("distance")) or 0)) <= 150]
        ability[no] = {
            "form": _mean(valid[:5]), "win_rate": sum(number(r.get("finish")) == 1 for r in rows) / len(rows) if rows else None,
            "top3_rate": sum(number(r.get("finish")) is not None and number(r.get("finish")) <= 3 for r in rows) / len(rows) if rows else None,
            "distance_form": _mean([_finish_quality(r) for r in comparable]),
            "margin": _mean([number(r.get("marginSeconds") if r.get("marginSeconds") is not None
                             else r.get("timeBehindWinner")) for r in comparable]),
        }
        v = _video_for(h, videos)
        if v is not None:
            days = v.get("sourceDates") or []
            if not days or any(not isinstance(d, str) or d >= cutoff for d in days):
                raise ValueError("future or unproven historic footage")
        video_summary[no] = v
    pressure = sum((v is not None and v <= 0.3) for v in early.values()) / len(numbers)
    features = {}
    for h in horses:
        no = h["horseNumber"]
        v = video_summary[no] or {}
        features[no] = {
            **ability[no],
            "early_position": early[no],
            "frame": (int(h.get("frameNumber") or no) - 1) / max(1, len(numbers) - 1),
            "pace_pressure": pressure,
            "video_speed": number(v.get("meanSpeedMps")),
            "video_start": number(v.get("initialSpeedMps")),
            "video_extra_distance": number(v.get("idealPathExcessMeters")),
            "video_slowdowns": number(v.get("slowdownCount")),
            "video_missing": 0.0 if v else 1.0,
        }
    return features


def load_model(circuit, folder=None):
    if circuit not in CIRCUITS:
        raise ValueError("unknown circuit")
    path = Path(folder or os.environ.get("ARVEXQ_NEW_MODEL_DIR", "")) / ("jra.json" if circuit == "中央" else "nar.json")
    if not (folder or os.environ.get("ARVEXQ_NEW_MODEL_DIR")) or not path.is_file():
        return None
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("circuit") != circuit or model.get("version") != VERSION:
        raise ValueError("wrong fitted model")
    return model


def validate_model(model, race):
    if not isinstance(model, dict) or model.get("circuit") != race.get("circuit") or model.get("version") != VERSION:
        raise ValueError("model version/circuit conflict")
    if not (model.get("trainedThrough") and model.get("calibratedThrough") and
            model["trainedThrough"] <= model["calibratedThrough"] < race["date"] and
            model.get("outOfSampleValidated") is True):
        raise ValueError("future-leaking or unvalidated probability model")
    weights = model.get("weights")
    if not isinstance(weights, dict) or set(weights) != set(FEATURES) or any(number(x) is None for x in weights.values()):
        raise ValueError("missing learned coefficients")
    temp = number(model.get("temperature"))
    if temp is None or temp <= 0:
        raise ValueError("uncalibrated temperature")
    sc = model.get("scenarioWeights")
    if not isinstance(sc, dict) or set(sc) != set(SCENARIOS) or any(number(x) is None or float(x) < 0 for x in sc.values()) or abs(sum(sc.values()) - 1) > 1.e-7:
        raise ValueError("scenario frequencies unavailable")
    if model.get("scenarioWeightsValidated") is not True:
        raise ValueError("scenario frequencies unvalidated")
    return weights, temp, sc


def predict(race, model, *, videos=None, quoted_odds=None):
    weights, temperature, scenarios = validate_model(model, race)
    evidence = extract(race, videos=videos)
    if any(all(evidence[n][k] is None for k in ("form", "distance_form")) for n in evidence):
        raise ValueError("insufficient official history")
    if any(evidence[n]["video_missing"] == 1.0 for n in evidence) and model.get("missingVideoValidated") is not True:
        raise ValueError("missing video not validated for model")
    numbers = sorted(evidence)
    default = model.get("featureMeans") or {}
    if set(default) != set(FEATURES) or any(number(v) is None for v in default.values()):
        raise ValueError("unverified missing-value encodings")
    dist = {}
    for name, share in scenarios.items():
        # Early-position pressure is inferred from actual runners, not a hard
        # coded win bonus. The learned scenario coefficient is in the model.
        pace_effect = number(model.get("paceEffect"))
        if pace_effect is None:
            raise ValueError("pace effect not fitted")
        raw = {}
        for n in numbers:
            f = evidence[n]
            val = sum(weights[k] * (f[k] if f[k] is not None else default[k]) for k in FEATURES)
            front = 1.0 - (f["early_position"] if f["early_position"] is not None else default["early_position"])
            if name == "fast": val -= pace_effect * front
            if name == "slow": val += pace_effect * front
            raw[n] = val / temperature
        def probs(remaining):
            peak = max(raw[k] for k in remaining)
            z = {k: exp(raw[k] - peak) for k in remaining}
            total = sum(z.values())
            return {k: z[k] / total for k in remaining}
        first = probs(numbers)
        for a in numbers:
            rem = [n for n in numbers if n != a]
            second = probs(rem)
            for b in rem:
                third = probs([n for n in rem if n != b])
                for c, pc in third.items():
                    key = (a, b, c)
                    dist[key] = dist.get(key, 0.0) + share * first[a] * second[b] * pc
    if abs(sum(dist.values()) - 1) > 1.e-7:
        raise ValueError("broken joint probability mass")
    win = {n: 0.0 for n in numbers}
    top3 = {n: 0.0 for n in numbers}
    for (a, b, c), p in dist.items():
        win[a] += p
        for n in (a, b, c):
            top3[n] += p
    order = sorted(numbers, key=lambda n: (-win[n], -top3[n], n))
    marks = [{"horseNumber": n, "mark": MARKS[i], "winProbability": win[n],
              "top3Probability": top3[n]} for i, n in enumerate(order[:5])]
    # Only real, explicitly supplied PRE-OFF quotes are eligible. Never invent odds.
    tickets = []
    for row in quoted_odds or []:
        kind, combo, odd = row.get("kind"), tuple(row.get("horses") or ()), number(row.get("odds"))
        if kind not in ("3連単", "3連複") or len(combo) != 3 or len(set(combo)) != 3 or not set(combo).issubset(numbers) or odd is None or odd <= 0:
            continue
        prob = (dist.get(combo, 0.0) if kind == "3連単" else
                sum(p for trip, p in dist.items() if set(trip) == set(combo)))
        tickets.append({"kind": kind, "combos": [list(combo)], "points": 1,
                        "hitProbability": prob, "expectedReturn": prob * odd})
    tickets.sort(key=lambda x: (-x["expectedReturn"], -x["hitProbability"]))
    return {
        "modelVersion": VERSION, "raceId": race["id"], "date": race["date"], "circuit": race["circuit"],
        "predictionStatus": "ready", "productionEligible": True, "videoAnalyzedInternally": any(evidence[n]["video_missing"] == 0.0 for n in numbers),
        "probabilities": {"win": win, "top3": top3,
                          "trifecta": [{"combo": list(k), "probability": p} for k, p in dist.items()]},
        "marks": marks, "tickets": tickets,
        "forecastText": "能力と展開の統合モデルによる勝率・3着内率の推定。",
    }
