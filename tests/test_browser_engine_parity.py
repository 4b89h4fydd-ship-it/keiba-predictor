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


if __name__ == "__main__":
    unittest.main()
