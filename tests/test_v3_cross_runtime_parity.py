"""Cross-runtime factual opt-in parity on identical saved-only JRA/NAR inputs.

This checks explicitly shared fields, not source-specific coverage metadata or
the still-independent quote/odds subcontracts. Never connects to live D1.
"""
import json
from pathlib import Path
import subprocess

import pytest

from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen

ROOT = Path(__file__).resolve().parents[1]
NODE = """
import fs from 'node:fs';
import {factualProjection} from './workers/api_v3_facts.mjs';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(factualProjection(input,input.id)));
"""


@pytest.mark.parametrize("circuit,city", [("jra", "京都"), ("nar", "高知")])
def test_saved_runner_and_display_readiness_parity(circuit, city):
    data = {
        "id": f"{circuit}-2026-10-19-{city}-03",
        "date": "2026-10-19", "circuit": circuit.upper(),
        "track": city, "fieldSize": 2, "startTime": "12:15",
        "horses": [
            {"horseNumber": 2, "name": "保存二", "winOdds": 2.5,
             "placeOdds": "1.2-1.5", "popularity": 2,
             "allPastRuns": [
                 {"date": f"2026-10-{n:02d}", "finish": 3}
                 for n in range(1, 10)
             ],
             "recentRaces": [{"date": "2026-10-09", "track": city},
                             {"date": "2026-10-19", "finish": 1}],
             "preRaceBet": {"secret": True}},
            {"horseNumber": 1, "name": "保存一", "winOdds": 0,
             "placeOdds": None, "popularity": "01",
             "recentRaces": [{"date": "2026-10-19", "finish": 1}],
             "predictionScore": 100},
        ],
        "result": {"payouts": [{"kind": "単勝", "payout": 300}]},
    }
    py = factual_screen(factual_response(data))
    process = subprocess.run(
        ["node", "--input-type=module", "-e", NODE],
        input=json.dumps(data, ensure_ascii=False),
        text=True, capture_output=True, cwd=ROOT, check=True,
    )
    js = json.loads(process.stdout)
    assert py["schema"] == js["schema"]
    assert py["race"] == js["race"]
    assert py["rows"] == js["rows"]
    assert py["rows"][0]["readiness"]["basicFields"]["name"] == "observed"
    assert py["rows"][0]["readiness"]["basicFields"]["jockey"] == "missing"
    assert py["rows"][0]["readiness"]["basicFieldReasons"]["jockey"] == "absent"
    assert py["rows"][0]["readiness"]["basicFieldReasons"]["name"] == "saved-value"
    assert py["displayReadiness"] == js["displayReadiness"]
    assert all(py["oddsFields"][key] == js["oddsFields"][key]
               for key in ("win", "place", "popularity"))
    assert py["coverage"]["counts"]["observedPriorRuns"] == js["coverage"]["observedPriorRuns"]
    assert py["coverage"]["counts"]["runnersWithPriorRuns"] == js["coverage"]["runnersWithPriorRuns"]
    assert py["results"] is js["results"] is None
    assert py["marks"] is js["marks"] is None
    assert py["tickets"] is js["tickets"] is None
    assert py["predictionStatus"] == js["predictionStatus"] == "not-implemented"
    assert py["rows"][1]["readiness"]["quoteTimeState"] == "missing"
    assert py["rows"][1]["readiness"]["pastFieldStates"][0]["fields"]["track"] == "observed"
    assert py["rows"][1]["readiness"]["pastFieldStates"][0]["fields"]["finish"] == "observed"
    assert py["rows"][1]["observedPriorRunCount"] == 9
    assert len(py["rows"][1]["recentRaces"]) == 5


@pytest.mark.parametrize("circuit,city", [("jra", "京都"), ("nar", "高知")])
def test_basic_field_missing_reasons_parity_and_no_provenance_invention(circuit, city):
    data = {
        "id": f"{circuit}-2026-10-19-{city}-03",
        "date": "2026-10-19", "circuit": circuit.upper(),
        "horses": [{"horseNumber": 1, "name": "  ", "jockey": None,
                    "trainer": False, "carriedWeight": 55.0}],
    }
    py = factual_screen(factual_response(data))
    js = json.loads(subprocess.run(
        ["node", "--input-type=module", "-e", NODE],
        input=json.dumps(data, ensure_ascii=False),
        text=True, capture_output=True, cwd=ROOT, check=True,
    ).stdout)
    assert py["rows"] == js["rows"]
    reason = py["rows"][0]["readiness"]["basicFieldReasons"]
    assert reason == {"name": "placeholder", "jockey": "null",
                      "trainer": "invalid-type-or-number",
                      "carriedWeight": "saved-value"}
    response = factual_response(data)
    response["runnerReadiness"][0]["basicFieldReasons"]["jockey"] = "saved-value"
    with pytest.raises(ValueError, match="basic field evidence"):
        factual_screen(response)


@pytest.mark.parametrize("circuit,city", [("jra", "京都"), ("nar", "高知")])
def test_past_cells_and_quote_time_parity(circuit, city):
    data = {
        "id": f"{circuit}-2026-10-19-{city}-03",
        "date": "2026-10-19", "circuit": circuit,
        "horses": [{"horseNumber": 3, "oddsUpdatedAt": "2026-10-19T12:00:00+09:00",
                    "allPastRuns": [{"date": "2026-10-10", "track": city,
                                     "distance": None, "finish": False, "last3f": 38.2}]}],
    }
    py = factual_screen(factual_response(data))
    js = json.loads(subprocess.run(
        ["node", "--input-type=module", "-e", NODE],
        input=json.dumps(data, ensure_ascii=False), text=True,
        capture_output=True, cwd=ROOT, check=True,
    ).stdout)
    assert py["rows"] == js["rows"]
    readiness = py["rows"][0]["readiness"]
    assert readiness["quoteTimeState"] == "observed-unverified-timestamp"
    assert readiness["marketFreshnessVerified"] is False
    assert readiness["pastFieldStates"] == [
        {"date": "2026-10-10", "fields": {
            "track": "observed", "distance": "missing",
            "finish": "invalid", "last3f": "observed"}}]
