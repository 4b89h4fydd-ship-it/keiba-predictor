"""Research-only race-group LightGBM ranking challenger; no production imports.

Use only the pre-race frozen mass-feature JSONL joined to settled results by
mass_training_store. Results are labels and never features. A rank score is not
an absolute probability or an expected return.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from math import isfinite
from pathlib import Path
from typing import Any

from arvexq.prediction.mass_feature_selection import snapshot_feature_allowed
from arvexq.research.ranking_feature_signals import MODES, enrich_frozen_features, history_coverage

VERSION = "arvexq-ranking-ability-ana-v1"
CIRCUITS = {"中央": "jra", "JRA": "jra", "jra": "jra",
            "地方": "nar", "NAR": "nar", "nar": "nar"}
HEADS = ("ability", "ana")
ALLOWED_PREFIXES = ("history::", "relative::", "static::", "category::", "delta::", "market::")
FORBIDDEN_PREFIXES = ("result::", "payout::", "after::", "postrace::", "label::", "target::", "prediction::")


def _iso_day(value: Any) -> str:
    day = str(value or "")
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("invalid race date")
    return day


def _rank_in_market(row: dict[str, Any]) -> int | None:
    raw = (row.get("features") or {}).get("market::popularity")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(value) if isfinite(value) and 1 <= value <= 30 and int(value) == value else None


def _features(row: dict[str, Any], head: str) -> dict[str, float]:
    features = {}
    for key, value in (row.get("features") or {}).items():
        name = str(key)
        if name.startswith(FORBIDDEN_PREFIXES) or not name.startswith(ALLOWED_PREFIXES) or not snapshot_feature_allowed(name):
            continue
        if head == "ability" and (name.startswith("market::") or name.startswith("relative::market::")):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        x = float(value)
        if isfinite(x):
            features[name] = x
    return features


def _relevance(finish: int, popularity: int | None, head: str) -> int:
    if head == "ability":
        return max(0, 4 - finish) if finish <= 3 else 0
    # The ANA task rewards only ACTUAL podium horses that beat their
    # pre-race market rank, not longshots that merely ran fourth or worse.
    if popularity is None or finish > 3:
        return 0
    return max(0, min(3, popularity - finish))


def prepare_races(rows: list[dict[str, Any]], circuit: str, head: str, *, mode: str = "baseline") -> list[dict[str, Any]]:
    """Produce complete, immutable race groups with sorted horse order.

    Fail closed on conflicting frozen hashes, dates, duplicate entries and
    incomplete podium labels. Missing market evidence excludes a whole ANA
    race, never just its individual horse (which would bias ranking groups).
    """
    if circuit not in ("jra", "nar") or head not in HEADS or mode not in MODES:
        raise ValueError("unsupported circuit/head/mode")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if CIRCUITS.get(str(row.get("circuit") or "")) != circuit:
            continue
        race_id = str(row.get("raceId") or "")
        if not race_id:
            raise ValueError("missing raceId")
        if "帯広" in race_id or str(row.get("track") or "") == "帯広":
            continue
        groups[race_id].append(row)

    output = []
    for race_id, members in groups.items():
        dates = {_iso_day(row.get("date")) for row in members}
        hashes = {str(row.get("featureHash") or "") for row in members}
        versions = {str(row.get("snapshotVersion") or "") for row in members}
        horses = [int(row.get("horseNumber") or 0) for row in members]
        finishes = [int(row.get("finish") or 0) for row in members]
        if len(dates) != 1 or len(hashes) != 1 or "" in hashes or len(versions) != 1 or "" in versions:
            raise ValueError(f"inconsistent frozen snapshot: {race_id}")
        if any(no <= 0 for no in horses) or len(set(horses)) != len(horses):
            raise ValueError(f"invalid horse roster: {race_id}")
        if any(place <= 0 for place in finishes) or len(set(finishes)) != len(finishes):
            # Dead heats need a distinct label policy; do not silently reorder.
            continue
        if len(members) < 4 or any(finishes.count(place) != 1 for place in (1, 2, 3)):
            continue
        ordered = sorted(members, key=lambda r: int(r["horseNumber"]))
        if head == "ana" and any(_rank_in_market(row) is None for row in ordered):
            continue
        ready = []
        for row in ordered:
            place = int(row["finish"])
            popularity = _rank_in_market(row)
            frozen = _features(row, head)
            features = enrich_frozen_features(frozen, head=head, mode=mode, field_size=len(ordered))
            ready.append({"horseNumber": int(row["horseNumber"]), "finish": place,
                          "popularity": popularity, "features": features,
                          "label": _relevance(place, popularity, head)})
        if not any(e["features"] for e in ready):
            continue
        output.append({"raceId": race_id, "date": next(iter(dates)), "rows": ready})
    return sorted(output, key=lambda race: (race["date"], race["raceId"]))


def split_races(races: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Chronological date blocks; one date can never cross train/valid/test."""
    days = sorted({race["date"] for race in races})
    if len(days) < 3:
        return {"train": [], "valid": [], "test": []}
    a = min(len(days) - 2, max(1, int(len(days) * .70)))
    b = min(len(days) - 1, max(a + 1, int(len(days) * .85)))
    blocks = {"train": set(days[:a]), "valid": set(days[a:b]), "test": set(days[b:])}
    return {key: [race for race in races if race["date"] in block]
            for key, block in blocks.items()}


def feature_manifest(train: list[dict[str, Any]], limit: int = 1000) -> list[str]:
    """Unsupervised feature filter fitted on TRAIN only, never on holdouts."""
    values: dict[str, list[float]] = defaultdict(list)
    total = sum(len(race["rows"]) for race in train)
    for race in train:
        for entry in race["rows"]:
            for key, value in entry["features"].items():
                values[key].append(value)
    qualified = []
    for key, observed in values.items():
        if len(observed) / max(1, total) < .01:
            continue
        mean = sum(observed) / len(observed)
        variance = sum((x - mean)**2 for x in observed) / len(observed)
        if variance > 1e-12:
            qualified.append((len(observed) / total * variance**.5, key))
    qualified.sort(key=lambda pair: (-pair[0], pair[1]))
    return [key for _, key in qualified[:limit]]


def make_matrix(races: list[dict[str, Any]], vectorizer: Any):
    sparse = vectorizer.transform([e["features"] for race in races for e in race["rows"]])
    labels = [e["label"] for race in races for e in race["rows"]]
    group = [len(race["rows"]) for race in races]
    return sparse, labels, group


def metrics(races: list[dict[str, Any]], predictions: list[float]) -> dict[str, Any]:
    from sklearn.metrics import ndcg_score
    pos, win1, win3, podium1, ndcgs = 0, 0, 0, 0, []
    market_win1 = market_win3 = 0
    outperformance = 0
    for race in races:
        entries = race["rows"]
        scores = predictions[pos:pos + len(entries)]
        if len(scores) != len(entries):
            raise ValueError("prediction length mismatch")
        pos += len(entries)
        order = sorted(range(len(entries)), key=lambda i: (-scores[i], entries[i]["horseNumber"]))
        winner = next(i for i, e in enumerate(entries) if e["finish"] == 1)
        win1 += int(order[0] == winner)
        win3 += int(winner in order[:3])
        podium1 += int(entries[order[0]]["finish"] <= 3)
        first = entries[order[0]]
        outperformance += int(first["popularity"] is not None and first["finish"] <= 3
                              and first["popularity"] > first["finish"])
        market = sorted(range(len(entries)), key=lambda i: (entries[i]["popularity"] or 999,
                                                            entries[i]["horseNumber"]))
        market_win1 += int(market[0] == winner)
        market_win3 += int(winner in market[:3])
        ndcgs.append(float(ndcg_score([[e["label"] for e in entries]], [list(scores)], k=3)))
    if pos != len(predictions):
        raise ValueError("unexpected prediction rows")
    count = len(races)
    return {"races": count, "winHitAt1": round(win1/count, 4) if count else None,
            "winnerHitAt3": round(win3/count, 4) if count else None,
            "top1PodiumRate": round(podium1/count, 4) if count else None,
            "outperformMarketAndPodiumAt1": round(outperformance/count, 4) if count else None,
            "ndcgAt3": round(sum(ndcgs)/count, 4) if count else None,
            "marketBaselineWinAt1": round(market_win1/count, 4) if count else None,
            "marketBaselineWinnerAt3": round(market_win3/count, 4) if count else None,
            "roi": None}


def _scorecards(races: list[dict[str, Any]], predictions: list[float]) -> list[dict[str, Any]]:
    pos, cards = 0, []
    for race in races:
        entries = []
        for runner in race["rows"]:
            entries.append({"horseNumber": runner["horseNumber"], "finish": runner["finish"],
                            "popularity": runner["popularity"], "label": runner["label"],
                            "score": float(predictions[pos])})
            pos += 1
        cards.append({"raceId": race["raceId"], "date": race["date"], "rows": entries})
    if pos != len(predictions):
        raise ValueError("scorecard length mismatch")
    return cards


def _shared_cards(left: list[dict[str, Any]], right: list[dict[str, Any]]):
    left_by = {r["raceId"]: r for r in left}
    right_by = {r["raceId"]: r for r in right}
    joined = []
    for race_id in sorted(left_by.keys() & right_by.keys()):
        a, b = left_by[race_id], right_by[race_id]
        ar = {e["horseNumber"]: e for e in a["rows"]}
        br = {e["horseNumber"]: e for e in b["rows"]}
        if a["date"] != b["date"] or ar.keys() != br.keys() or any(
                ar[n]["finish"] != br[n]["finish"] or ar[n]["popularity"] != br[n]["popularity"]
                for n in ar):
            raise ValueError(f"paired races disagree on frozen roster/outcomes: {race_id}")
        joined.append((a, b))
    return joined


def _rank_pct(entries: list[dict[str, Any]]) -> dict[int, float]:
    order = sorted(entries, key=lambda e: (-e["score"], e["horseNumber"]))
    length = len(order)
    return {e["horseNumber"]: 1.0 - i / max(1, length - 1) for i, e in enumerate(order)}


def _blend_pair(pair, weight: float):
    ability, ana = pair
    ax, bx = _rank_pct(ability["rows"]), _rank_pct(ana["rows"])
    entries = [{"horseNumber": e["horseNumber"], "finish": e["finish"],
                "popularity": e["popularity"], "label": max(0, 4-e["finish"]),
                "features": {}}
               for e in ability["rows"]]
    scores = [weight*ax[e["horseNumber"]] + (1-weight)*bx[e["horseNumber"]]
              for e in ability["rows"]]
    return {"raceId": ability["raceId"], "date": ability["date"], "rows": entries}, scores


def _pair_metrics(pairs, weight: float) -> dict[str, Any]:
    objects = [_blend_pair(pair, weight) for pair in pairs]
    return metrics([obj[0] for obj in objects], [s for obj in objects for s in obj[1]])


def paired_report(ability: dict[str, Any], ana: dict[str, Any]) -> dict[str, Any]:
    """Same-race holdout. Tune blend ONLY on validation, never the test."""
    if ability["trainThrough"] != ana["trainThrough"]:
        raise ValueError("unmatched training period")
    valid = _shared_cards(ability["validation"], ana["validation"])
    test = _shared_cards(ability["test"], ana["test"])
    if len(valid) < 2 or len(test) < 2:
        return {"status": "insufficient-paired-races", "validationRaces": len(valid),
                "testRaces": len(test), "productionEligible": False}
    if max(v[0]["date"] for v in valid) >= min(t[0]["date"] for t in test):
        raise ValueError("time order violation: paired validation overlaps holdout")
    if ability["trainThrough"] >= min(v[0]["date"] for v in valid):
        raise ValueError("training overlaps paired validation")
    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    # Tie-break toward Ability-only, the simpler model, to avoid noise-seeking.
    candidates = [(_pair_metrics(valid, w), w) for w in weights]
    best_m, best_w = max(candidates, key=lambda item: (item[0]["winHitAt1"],
                                                       item[0]["winnerHitAt3"], item[1]))
    return {"status": "evaluated-research-only", "productionEligible": False,
            "validationRaces": len(valid), "testRaces": len(test),
            "trainThrough": ability["trainThrough"], "blendAbilityWeight": best_w,
            "validationMetrics": best_m, "ability": _pair_metrics(test, 1.0),
            "ana": _pair_metrics(test, 0.0), "blended": _pair_metrics(test, best_w),
            "v9b": None, "note": "V9b requires aligned frozen original predictions; ROI needs paid-out tickets."}


def train_one(rows: list[dict[str, Any]], circuit: str, head: str, out: Path,
              *, min_train_races: int = 40, mode: str = "baseline") -> dict[str, Any]:
    """Train one isolated research head; do not load in production runtime."""
    import joblib
    import lightgbm as lgb
    from sklearn.feature_extraction import DictVectorizer

    races = prepare_races(rows, circuit, head, mode=mode)
    blocks = split_races(races)
    if (len(blocks["train"]) < min_train_races or len(blocks["valid"]) < 2
            or len(blocks["test"]) < 2):
        raise ValueError(f"insufficient independent frozen races for {circuit}/{head}")
    train = blocks["train"]
    features = feature_manifest(train)
    if not features:
        raise ValueError("no varying pre-race training features")
    allowed = set(features)
    for block in blocks.values():
        for race in block:
            for entry in race["rows"]:
                entry["features"] = {k: v for k, v in entry["features"].items() if k in allowed}
    v = DictVectorizer(sparse=True)
    v.fit([entry["features"] for race in train for entry in race["rows"]])
    x, y, group = make_matrix(train, v)
    xv, yv, gv = make_matrix(blocks["valid"], v)
    if not any(y) or not any(yv):
        raise ValueError("ranking objective has no graded labels in train/validation")
    model = lgb.LGBMRanker(objective="lambdarank", metric="ndcg", n_estimators=200,
                          learning_rate=.03, num_leaves=15, min_child_samples=10,
                          label_gain=[0, 1, 3, 7], random_state=20261111, verbosity=-1)
    model.fit(x, y, group=group, eval_set=[(xv, yv)], eval_group=[gv], eval_at=[1, 3],
              callbacks=[lgb.early_stopping(25, verbose=False)])
    xt, _, _ = make_matrix(blocks["test"], v)
    test_predictions = list(model.predict(xt))
    valid_predictions = list(model.predict(xv))
    result = {"version": VERSION, "circuit": circuit, "head": head, "featureMode": mode,
              "experimentFeatureCoverage": history_coverage(races),
              "researchOnly": True, "productionEligible": False,
              "featureCount": len(v.feature_names_), "trainRaces": len(train),
              "validationRaces": len(blocks["valid"]), "testRaces": len(blocks["test"]),
              "trainThrough": max(r["date"] for r in train),
              "testFrom": min(r["date"] for r in blocks["test"]),
              "metrics": metrics(blocks["test"], test_predictions),
              "warning": "Ranking scores are not calibrated probabilities; ROI requires actual settled payouts."}
    dest = out / ("" if mode == "baseline" else mode) / circuit / head
    dest.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(dest / "ranker.txt"))
    joblib.dump(v, dest / "vectorizer.joblib")
    (dest / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (dest / "holdout_scores.json").write_text(json.dumps({
        "trainThrough": result["trainThrough"], "featureMode": mode,
        "validation": _scorecards(blocks["valid"], valid_predictions),
        "test": _scorecards(blocks["test"], test_predictions),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Train isolated Ability/ANA ranking challengers (no publish)")
    p.add_argument("frozen_jsonl", help="Output of export_mass_training_dataset.py")
    p.add_argument("output_dir")
    p.add_argument("--min-train-races", type=int, default=40)
    p.add_argument("--mode", choices=MODES, default="baseline")
    p.add_argument("--paired", action="store_true", help="Use the same race cohort to compare Ability/ANA/blend")
    args = p.parse_args()
    rows = [json.loads(line) for line in Path(args.frozen_jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    reports = []
    pair_reports = []
    for circuit in ("jra", "nar"):
        circuit_rows = rows
        if args.paired:
            group_ids = {r["raceId"] for r in prepare_races(rows, circuit, "ability", mode=args.mode)} & \
                        {r["raceId"] for r in prepare_races(rows, circuit, "ana", mode=args.mode)}
            circuit_rows = [r for r in rows if r.get("raceId") in group_ids]
        complete = True
        for head in HEADS:
            try:
                reports.append(train_one(circuit_rows, circuit, head, Path(args.output_dir),
                                         min_train_races=args.min_train_races, mode=args.mode))
            except ValueError as exc:
                complete = False
                reports.append({"circuit": circuit, "head": head, "status": "insufficient-data",
                                "reason": str(exc), "productionEligible": False})
        if args.paired and complete:
            root = Path(args.output_dir) / ("" if args.mode == "baseline" else args.mode) / circuit
            ability = json.loads((root / "ability" / "holdout_scores.json").read_text(encoding="utf-8"))
            ana = json.loads((root / "ana" / "holdout_scores.json").read_text(encoding="utf-8"))
            result = paired_report(ability, ana)
            (root / "paired_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            pair_reports.append({"circuit": circuit, **result})
    print(json.dumps({"version": VERSION, "featureMode": args.mode, "productionChanged": False,
                      "reports": reports, "paired": pair_reports},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())