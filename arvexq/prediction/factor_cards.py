"""14 inspectable pre-off evidence categories. Not an unvalidated scoring replacement."""
from __future__ import annotations

from typing import Any
from copy import deepcopy
from arvexq.prediction.factor_model import collect_horse_raw_metrics

VERSION = "arvexq-fourteen-factor-evidence-v1"

# Existing measurements are intentionally reused, with correlated features
# grouped under their evidence family rather than counted as independent votes.
FACTORS = (
    ("speed", "走破能力", ("ability_speed_index_median", "ability_clock_speed_median")),
    ("closing", "上がり・持続", ("ability_sectional", "ability_true_run")),
    ("early", "先行・隊列", ("pace_scenario", "pace_state")),
    ("finish", "着順実績", ("record_recent", "record_top3_rate")),
    ("class", "相手レベル", ("record_level", "record_class_edge")),
    ("form", "近況", ("record_form_research", "record_recent")),
    ("distance", "距離適性", ("suit_distance_history", "suit_distance_model")),
    ("track", "コース適性", ("suit_track_history", "suit_track_model")),
    ("going", "馬場適性", ("suit_going_history", "suit_going_model")),
    ("surface", "芝・ダート適性", ("suit_surface_history", "suit_surface_model")),
    ("pedigree", "血統", ("support_pedigree_research", "support_pedigree")),
    ("connections", "騎手・厩舎", ("support_connections", "support_jockey", "support_trainer")),
    ("weight", "斤量・馬体", ("support_carried_weight", "support_body", "support_body_change")),
    ("draw", "枠順・条件変化", ("support_draw", "support_condition_change")),
)


def evidence_card(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    # The cards and the frozen challenger cannot access a run on or after the
    # race's scheduled date, even if a later cache merged new history into it.
    cutoff = str(race.get("date") or "")
    safe_horse = deepcopy(horse)
    if cutoff:
        for key in ("allPastRuns", "recentRaces"):
            if isinstance(safe_horse.get(key), list):
                safe_horse[key] = sorted([
                    row for row in safe_horse[key]
                    if isinstance(row, dict)
                    and str(row.get("date") or row.get("raceDate") or "")
                    and str(row.get("date") or row.get("raceDate") or "") < cutoff
                ], key=lambda row: str(row.get("date") or row.get("raceDate") or ""), reverse=True)[:5]
    else:
        safe_horse["allPastRuns"] = []
        safe_horse["recentRaces"] = []
    raw = collect_horse_raw_metrics(safe_horse, race)
    items = []
    for key, label, fields in FACTORS:
        available = [{"key": f, "value": raw[f]} for f in fields
                     if isinstance(raw.get(f), (float, int)) and raw[f] == raw[f]]
        items.append({
            "key": key, "label": label, "measurements": available,
            "available": bool(available), "derivedFrom": "saved-prerace-evidence",
        })
    return {
        "version": VERSION, "items": items,
        "evidenceCoverage": sum(z["available"] for z in items) / len(items),
        "weighting": "既存4本柱の計算は変更しません。14項目は重複補正前の根拠開示であり的中確率ではありません。",
        "calibrated": False,
    }


def weighted_experiment(card: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]:
    """Record user-specified weights; never pretend unscaled raw metrics are probabilities."""
    checked = {}
    for name, value in weights.items():
        if name not in {f[0] for f in FACTORS}:
            raise ValueError("unknown factor")
        w = float(value)
        if not 0 <= w <= 1 or w != w:
            raise ValueError("invalid factor weight")
        checked[name] = w
    return {
        "version": "arvexq-factor-experiment-v1",
        "weights": checked,
        "factorEvidenceVersion": card.get("version"),
        "predictiveScore": None,
        "status": "requires-preoff-walkforward-calibration",
    }
