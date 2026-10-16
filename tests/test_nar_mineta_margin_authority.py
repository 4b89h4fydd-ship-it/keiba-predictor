import copy
import unittest
from arvexq.prediction.final_marks import apply_core_marks
from arvexq.prediction.observed_model import MODEL_VERSION, apply_nar_marks, rank_nar
from arvexq.research.mineta_field_proxy import score_race
from arvexq.research.margin_abcde_candidate import score as margin_score


def race():
    horses = []
    for no in range(1, 7):
        runs = []
        for i, day in enumerate((1, 8, 15, 22, 29)):
            runs.append({
                "date": f"2026-09-{day:02d}", "track": "園田", "raceNumber": i + 1,
                "distance": 1400, "surface": "ダート", "fieldSize": 10,
                "finish": min(no + i % 3, 10), "opponentLevel": 0.6,
                "cornerPositions": [min(no, 10), min(no + i % 2, 10)],
                "timeBehindWinner": round((no - 1) * .15 + i * .01, 2),
            })
        horses.append({"name": f"馬{no}", "horseNumber": no,
                       "frameNumber": no, "recentRaces": list(reversed(runs))})
    return {"id": "nar-2026-10-12-園田-01", "circuit": "地方",
            "date": "2026-10-12", "track": "園田",
            "surface": "ダート", "distance": 1400, "horses": horses}


class NarAuthorityTests(unittest.TestCase):
    def test_blend_is_exactly_60_40_of_observed_inputs(self):
        d = race()
        rows = rank_nar(d["horses"], d)
        self.assertEqual(len(rows), len(d["horses"]))
        positions = score_race(d["horses"], d)
        for row in rows:
            h = row["horse"]
            no = h["horseNumber"]
            margin = margin_score(h, d)
            self.assertAlmostEqual(row["score"], .60 * positions[no] + .40 * margin["score"] + .12 * row["historicalRates"]["winEvidence"] + .06 * row["historicalRates"]["top2Evidence"] + .04 * row["historicalRates"]["top3Evidence"])

    def test_new_marks_replace_old_fields_and_leave_seal_untouched(self):
        d = race()
        d["morningMarkSnapshot"] = {"fixedAt": "2026-10-12T09:00:00+09:00",
                                    "horses": [{"horseNumber": 1, "mark": "○"}]}
        original = copy.deepcopy(d["morningMarkSnapshot"])
        for h in d["horses"]:
            h["integratedEvaluation"] = {"mark": "注", "factorEvidence": {"old": 1},
                                          "multiHead": True}
        apply_core_marks(d)
        self.assertEqual(d["predictionModelVersion"], MODEL_VERSION)
        self.assertEqual(d["factorRanking"][0]["horseNumber"], 1)
        self.assertEqual(d["horses"][0]["integratedEvaluation"]["mark"], "◎")
        self.assertNotIn("factorEvidence", d["horses"][0]["integratedEvaluation"])
        self.assertNotIn("multiHead", d["horses"][0]["integratedEvaluation"])
        self.assertEqual(d["morningMarkSnapshot"], original)

    def test_missing_margins_never_get_legacy_scores(self):
        d = race()
        for run in d["horses"][5]["recentRaces"]:
            run.pop("timeBehindWinner")
        apply_nar_marks(d)
        self.assertFalse(d["observedModelCoverage"]["allObserved"])
        self.assertEqual(d["observedModelCoverage"]["fullyObserved"], 5)
        self.assertEqual(d["horses"][5]["integratedEvaluation"]["mark"], "")
        self.assertNotEqual(d["predictionStatus"], "ready")

    def test_zero_winner_margin_is_valid(self):
        d = race()
        self.assertEqual(d["horses"][0]["recentRaces"][0]["timeBehindWinner"], .04)
        self.assertEqual(d["horses"][0]["recentRaces"][-1]["timeBehindWinner"], 0.)
        self.assertIsNotNone(margin_score(d["horses"][0], d))
        self.assertIsNotNone(rank_nar(d["horses"], d))

    def test_local_evidence_exposes_only_new_two_axes(self):
        from arvexq.prediction.race_intelligence import attach_evidence
        d = apply_nar_marks(race())
        attach_evidence(d)
        factors = d["horses"][0]["researchEvidence"]["factors"]
        self.assertEqual(factors["version"], MODEL_VERSION)
        self.assertEqual([(x["key"], x["weight"]) for x in factors["items"]],
                         [("mineta", .60), ("margin", .40)])
        self.assertNotIn("trueRun", [x["key"] for x in factors["items"]])

    def test_star_mark_requires_independent_race_pace_evidence(self):
        from unittest.mock import patch
        d = race()
        # Runner #5 can advance strongly from a wide/late position when three
        # competitors have displayed early pace. This is not a rank-five rule.
        d["horses"][4]["recentRaces"][-1].update(
            finish=2, cornerPositions=[8, 8, 8], timeBehindWinner=.2)
        scores = (.90, .83, .75, .69, .66, .58)
        rows = [
            {"horse": h, "score": scores[i], "sample": 5,
             "factors": {"mineta": .60, "margin": scores[i]},
             "marginCoverage": .8, "modelVersion": MODEL_VERSION, "rank": i + 1}
            for i, h in enumerate(d["horses"])
        ]
        with patch("arvexq.prediction.observed_model.rank_observed", return_value=rows):
            apply_nar_marks(d)
        marks = [h["integratedEvaluation"]["mark"] for h in d["horses"]]
        self.assertEqual(marks, ["◎", "○", "注", "▲", "☆", "△"])
        # Actual pre-off evidence may supersede the original third/fourth
        # scored roles, but never overwrites the ◎○ model leaders.
        self.assertEqual(len([m for m in marks if m == "☆"]), 1)
        self.assertEqual(len([m for m in marks if m == "注"]), 1)

    def test_central_dispatch_never_uses_nar_model(self):
        with self.assertRaises(ValueError):
            apply_nar_marks({"circuit": "中央", "date": "2026-10-12", "horses": []})


if __name__ == "__main__":
    unittest.main()
