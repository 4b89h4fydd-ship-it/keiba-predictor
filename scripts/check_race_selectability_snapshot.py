#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy

from arvexq.prediction.final_marks import apply_core_marks
from arvexq.selection.race_selectability_snapshot import (
    apply_race_selectability_fields,
    prepare_race_selectability_fields,
)
from arvexq.selection.race_selectability_training import frozen_selectability_training_row


def horse(no: int, finishes: list[int], speed: float) -> dict:
    runs = [
        {
            "finish": fin,
            "fieldSize": 12,
            "distance": 1600,
            "track": "T",
            "condition": "良",
            "speedIndex": speed - i,
            "cornerPositions": [max(1, fin + 2), max(1, fin + 1), fin],
        }
        for i, fin in enumerate(finishes)
    ]
    return {"horseNumber": no, "name": f"H{no}", "recentRaces": runs, "integratedEvaluation": {}}


detail = {
    "id": "test-race",
    "date": "2026-10-10",
    "circuit": "中央",
    "track": "T",
    "raceNumber": 1,
    "distance": 1600,
    "condition": "良",
    "horses": [
        horse(1, [1, 2, 1, 2, 1], 105),
        horse(2, [3, 3, 2, 4, 3], 95),
        horse(3, [5, 4, 5, 6, 4], 85),
    ],
}
apply_core_marks(detail)
detail["preRacePrediction"] = {
    "horses": [
        {
            "horseNumber": h["horseNumber"],
            "mark": h["integratedEvaluation"]["mark"],
        }
        for h in detail["horses"]
    ]
}
fields = prepare_race_selectability_fields(detail)
assert fields.get("raceSelectabilityHash"), fields
apply_race_selectability_fields(detail, fields)
original_hash = detail["raceSelectabilityHash"]
original_features = deepcopy(detail["raceSelectabilitySnapshot"]["features"])

# Final information must not rewrite frozen feature evidence.
detail["result"] = {
    "status": "確定",
    "finishers": [
        {"finish": 1, "horseNumber": 2},
        {"finish": 2, "horseNumber": 1},
        {"finish": 3, "horseNumber": 3},
    ],
    "payouts": [{"kind": "単勝", "amount": 999999}],
}
detail["winner"] = 2
detail["horses"][0]["popularity"] = 12
detail["horses"][1]["popularity"] = 1
fields2 = prepare_race_selectability_fields(detail)
apply_race_selectability_fields(detail, fields2)
assert detail["raceSelectabilityHash"] == original_hash
assert detail["raceSelectabilitySnapshot"]["features"] == original_features

training = frozen_selectability_training_row(detail)
assert training is not None
assert training["features"] == original_features
assert training["labels"]["honmeiWin"] == 0
assert training["labels"]["honmeiTop3"] == 1
assert training["labels"]["winnerCoreMark"] == 1

print("race-selectability-snapshot-ok", original_hash, training["labels"])
