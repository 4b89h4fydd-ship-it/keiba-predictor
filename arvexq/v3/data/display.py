"""Neutral factual display projection, independent of prediction/marks/tickets."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from arvexq.ingest.full_career import merge_career
from arvexq.v3.data.quality import build_data_status

RACE_FIELDS = ("id", "date", "circuit", "track", "raceNumber", "title",
               "surface", "distance", "condition", "weather", "startTime",
               "fieldSize")
RUNNER_FIELDS = ("horseNumber", "frameNumber", "name", "sex", "age",
                 "carriedWeight", "jockey", "trainer", "affiliation", "status",
                 "scratched", "withdrawn", "bodyWeight", "bodyWeightChange",
                 "winOdds", "placeOdds", "popularity")


def factual_display(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Render only observed racing information from the supplied saved detail.

    Never include forecasts, model outputs or historical frozen betting tickets.
    Separate current observed race results from strictly earlier horse history.
    """
    source = detail if isinstance(detail, dict) else {}
    horses = [h for h in (source.get("horses") or []) if isinstance(h, dict)]
    rows = []
    for horse in horses:
        row = {key: deepcopy(horse[key]) for key in RUNNER_FIELDS if key in horse}
        row["pastRuns"] = merge_career(
            horse.get("allPastRuns"), horse.get("recentRaces"), source.get("date")
        )
        rows.append(row)

    def key(row):
        try:
            return int(row.get("horseNumber") or 99999)
        except (ValueError, TypeError, OverflowError):
            return 99999

    result = source.get("result") if isinstance(source.get("result"), dict) else {}
    return {
        "schema": "arvexq-v3-factual-display-1",
        "race": {field: deepcopy(source[field]) for field in RACE_FIELDS if field in source},
        "runners": sorted(rows, key=key),
        "result": deepcopy(result),
        "quality": build_data_status(source),
    }
