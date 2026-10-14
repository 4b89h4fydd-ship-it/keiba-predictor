"""Python engine and actual app.js must compute the same staged pre-race scores."""
import json
import subprocess
import unittest
from pathlib import Path

from arvexq.prediction.factor_model import rank_factor_model

ROOT = Path(__file__).resolve().parents[1]
JS = """
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const first=source.indexOf('function arvexqFactorValues(');
const end=source.indexOf('\\nfunction arvexqRacePolicy(',first);
if(first<0||end<0)throw new Error('missing model implementation');
const score=vm.runInNewContext('('+source.slice(first,end)+')');
const race=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(race.horses.map(h=>({no:h.horseNumber,...score({horse:h},race)}))));
"""


class EngineBrowserParity(unittest.TestCase):
    def test_same_observed_five_runs_both_engines(self):
        race = {"date": "2026-10-14", "distance": 1400, "surface": "ダート",
                "horses": [
                    {"horseNumber": 1, "recentRaces": [
                        {"date": "2026-10-12", "finish": 1, "fieldSize": 10,
                         "distance": 1400, "surface": "ダート"},
                        {"date": "2026-10-10", "finish": 5, "fieldSize": 10,
                         "distance": 1200, "surface": "芝"},
                        {"date": "2026-10-08", "finish": 3, "fieldSize": 10,
                         "distance": 1400, "surface": "ダート"}]},
                    {"horseNumber": 2, "recentRaces": [
                        {"date": "2026-10-11", "finish": 2, "fieldSize": 11,
                         "distance": 1400, "surface": "芝"}]},
                    {"horseNumber": 3, "recentRaces": []},
                ]}
        rank = rank_factor_model(race["horses"], race)
        expected = {int(z["horse"]["horseNumber"]): z for z in rank}
        p = subprocess.run(["node", "-e", JS], cwd=ROOT, input=json.dumps(race),
                           text=True, capture_output=True, check=True, timeout=30)
        browser = json.loads(p.stdout)
        self.assertEqual(len(expected), len(browser))
        for z in browser:
            model = expected[z["no"]]
            self.assertAlmostEqual(z["score"], model["score"], places=12)
            self.assertEqual(z["coverage"], model["primaryPillarCoverage"])
            self.assertIsNone(z.get("sectional"))


    def test_zero_distance_does_not_count_as_matching_condition(self):
        race = {"date": "2026-10-14", "distance": 0, "surface": "ダート",
                "horses": [{"horseNumber": 1, "recentRaces": [
                    {"date": "2026-10-13", "finish": 2, "fieldSize": 10,
                     "distance": 0, "surface": "ダート"}]}]}
        python_row = rank_factor_model(race["horses"], race)[0]
        result = subprocess.run(["node", "-e", JS], cwd=ROOT,
                                input=json.dumps(race), text=True,
                                capture_output=True, check=True, timeout=30)
        browser_row = json.loads(result.stdout)[0]
        self.assertIsNone(python_row["factors"]["conditionForm"])
        self.assertIsNone(browser_row["conditionForm"])
        self.assertEqual(browser_row["coverage"], python_row["primaryPillarCoverage"])
        self.assertAlmostEqual(browser_row["score"], python_row["score"], places=12)


    def test_jra_and_nar_have_independent_scoring_paths(self):
        dates = ["2026-10-12", "2026-10-10", "2026-10-08",
                 "2026-10-06", "2026-10-04"]
        horses = [{"horseNumber": 1, "recentRaces": [
            {"date": day, "finish": finish, "fieldSize": 12, "distance": 1400,
             "surface": "ダート", "track": "園田" if i != 2 else "笠松"}
            for i, (day, finish) in enumerate(zip(dates, [1, 2, 5, 6, 8]))]},
                  {"horseNumber": 2, "recentRaces": [
                      {"date": dates[i], "finish": finish, "fieldSize": 12,
                       "distance": 1400, "surface": "ダート", "track": "笠松"}
                      for i, finish in enumerate([3, 5, 3, 5, 3])]}]
        scores = {}
        for circuit, track, expected_version in (
                ("中央", "東京", "arvexq-jra-momentum-condition-stage-v1"),
                ("地方", "園田", "arvexq-nar-track-condition-stage-v1")):
            race = {"date": "2026-10-14", "circuit": circuit, "track": track,
                    "distance": 1400, "surface": "ダート", "horses": horses}
            p = subprocess.run(["node", "-e", JS], cwd=ROOT, input=json.dumps(race),
                               text=True, capture_output=True, check=True, timeout=30)
            browser = json.loads(p.stdout)
            ranking = rank_factor_model(horses, race)
            by_no = {int(row["horse"]["horseNumber"]): row for row in ranking}
            for row in browser:
                py = by_no[row["no"]]
                self.assertEqual(row["modelVersion"], expected_version)
                self.assertEqual(py["modelVersion"], expected_version)
                self.assertAlmostEqual(row["score"], py["score"], places=12)
            scores[circuit] = by_no[1]["score"]
        self.assertNotEqual(scores["中央"], scores["地方"],
                            "circuit-specific scores must not be aliases")


if __name__ == "__main__":
    unittest.main()
