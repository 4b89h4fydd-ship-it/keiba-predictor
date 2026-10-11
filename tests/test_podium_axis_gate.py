import unittest
from unittest.mock import patch
from arvexq.prediction.honmei_gate import evaluate_honmei_gate
from arvexq.prediction.final_marks import apply_core_marks

def sample(no, rank, finish, strength, pillars, families=(2,3,2,2)):
    dates=[f"2026-09-{i+10:02d}" for i in range(len(finish))]
    horse = {"horseNumber":no, "name":"Horse"+str(no),
             "recentRaces":[{"date":d,"finish":v,"fieldSize":10} for d,v in zip(dates,finish)],
             "_careerHistoryAudit":{"version":"arvexq-career-coverage-v1","requestedAtRaceDate":"2026-10-09","reportedStarts":len(finish),"observedRuns":len(finish),"paginationComplete":True,"complete":True,"reportedStartsSource":"test","failedProviders":[]}}
    return {"horse":horse, "rank":rank, "sample":len(finish),
            "multiHead":{"strengthRank":rank,"strengthScore":strength,"winRank":rank},
            "pillarRanks":{x:rank for x in ("ability","record","suitability","pace")},
            "evidenceFamilyCounts":dict(zip(("ability","record","suitability","pace"),families)),
            "ability":pillars[0],"record":pillars[1],"suitability":pillars[2],"pace":pillars[3],
            "pairwiseWins":3-rank,"pairwiseLosses":rank-1,"pairwiseTies":0,
            "supportTieBreakWins":0,"dominanceScore":80,"pillarScores":{},
            "evidenceCounts":{},"metricRelative":{},"raw":{},"primaryPillarCoverage":4}

class PodiumAxisTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            sample(1,1,[1,8,9,9,8],.76,(.82,.82,.80,.85)),
            sample(2,2,[2,2,3,2,4],.75,(.80,.79,.78,.77)),
            sample(3,3,[7,8,8,7,9],.40,(.45,.42,.48,.39))]
        self.summary = {"winnerHorseNumber":1,"winnerGap":.1}
    def test_stable_podium_runner_can_differ_from_winner_head(self):
        result=evaluate_honmei_gate(self.rows,self.summary,{"circuit":"地方","date":"2026-10-09"})
        self.assertTrue(result["eligible"],result)
        self.assertEqual(result["horseNumber"],2)
    def test_no_forced_axis_without_runs(self):
        for row in self.rows:
            row["horse"]["recentRaces"]=[]
        result=evaluate_honmei_gate(self.rows,self.summary,{"circuit":"地方","date":"2026-10-09"})
        self.assertFalse(result["eligible"])
        self.assertIn("historicalPodium",result["failed"])
    def test_central_does_not_have_a_blanket_ban(self):
        self.assertTrue(evaluate_honmei_gate(self.rows,self.summary,{"circuit":"中央","date":"2026-10-09"})["eligible"])
    def test_server_marks_independent_axis(self):
        with patch("arvexq.prediction.final_marks.rank_factor_model",return_value=self.rows),\
             patch("arvexq.prediction.final_marks.attach_multi_head_signals",return_value=self.summary):
            detail=apply_core_marks({"horses":[r["horse"] for r in self.rows],"circuit":"地方","date":"2026-10-09"})
        marks={h["horseNumber"]:h["integratedEvaluation"]["mark"] for h in detail["horses"]}
        self.assertEqual(marks[2],"◎")
        self.assertEqual(marks[1],"○")
        self.assertEqual(list(marks.values()).count("◎"),1)
        self.assertEqual(detail["honmeiDecision"]["confidenceGrade"],"A")
        self.assertTrue(detail["honmeiDecision"]["fixedAxisAllowed"])
        self.assertEqual(detail["horses"][1]["integratedEvaluation"]["honmeiRole"],"axis")

    def test_relative_honmei_is_shown_but_cannot_be_fixed_without_podium_evidence(self):
        rows = [
            sample(1, 1, [7, 8, 9, 8, 9], .76, (.82, .82, .80, .85)),
            sample(2, 2, [8, 9, 9, 9, 9], .75, (.80, .79, .78, .77)),
            sample(3, 3, [9, 9, 9, 9, 9], .40, (.45, .42, .48, .39)),
        ]
        with patch("arvexq.prediction.final_marks.rank_factor_model", return_value=rows), \
             patch("arvexq.prediction.final_marks.attach_multi_head_signals",
                   return_value={"winnerHorseNumber":1,"winnerGap":.12}):
            detail = apply_core_marks({"horses":[r["horse"] for r in rows],
                                       "circuit":"地方","date":"2026-10-09"})
        marks=[h["integratedEvaluation"]["mark"] for h in detail["horses"]]
        self.assertEqual(marks.count("◎"),1)
        self.assertFalse(detail["honmeiDecision"]["eligible"])
        self.assertEqual(detail["honmeiDecision"]["confidenceGrade"],"C")
        self.assertFalse(detail["honmeiDecision"]["fixedAxisAllowed"])
        self.assertEqual(detail["horses"][0]["integratedEvaluation"]["honmeiGrade"],"C")


if __name__=="__main__":
    unittest.main()
