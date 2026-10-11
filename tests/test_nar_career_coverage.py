"""No early five-run stop; no evidence from after the target race date."""
import unittest
from arvexq.ingest.nar_career_coverage import pre_race_reported_starts,official_history_complete


class NarCareerCoverageTests(unittest.TestCase):
    def test_five_runs_never_proves_long_career(self):
        coverage={"counts":{"A":5,"B":5},"totalHorses":2,"horsesWith5Plus":2}
        self.assertFalse(official_history_complete(coverage,{"A":81,"B":7}))
        self.assertFalse(official_history_complete(coverage,{"A":5}))
        self.assertFalse(official_history_complete(coverage,{}))
        self.assertTrue(official_history_complete({"counts":{"A":81,"B":7}},
                                                  {"A":81,"B":7}))
        self.assertFalse(official_history_complete({"counts":{"A":82,"B":7}},
                                                   {"A":81,"B":7}),
                         "extra starts indicate an identity/count conflict, not proof")
    def test_date_bound_reported_starts_only(self):
        detail={"horses":[
            {"name":"A","careerStartEvidence":{"starts":81,"asOfRaceDate":"2026-10-11"}},
            {"name":"B","_careerHistoryAudit":{"reportedStarts":7,"requestedAtRaceDate":"2026-10-11"}},
            {"name":"C","careerStartEvidence":{"starts":6,"asOfRaceDate":"2026-10-12"}},
            {"name":"D","careerStartEvidence":{"starts":4,"asOfRaceDate":"2026-10-11","conflict":True}},
            {"name":"E","careerStartEvidence":{"starts":0,"asOfRaceDate":"2026-10-11"}},
        ]}
        self.assertEqual(pre_race_reported_starts(detail,"2026-10-11",
                                                  ["A","B","C","D","E"]),
                         {"A":81,"B":7,"E":0})
    def test_unknown_not_declared_complete(self):
        self.assertFalse(official_history_complete({"counts":{"A":5}},{}))
        self.assertFalse(official_history_complete({"counts":{"A":4}},
                                                  {"A":5}))
        self.assertFalse(official_history_complete({"counts":{}},{}))
    def test_ambiguous_identity_ignored(self):
        details={"horses":[
           {"name":"A","careerStartEvidence":{"starts":5,"asOfRaceDate":"2026-10-11"}},
           {"name":"A","careerStartEvidence":{"starts":6,"asOfRaceDate":"2026-10-11"}}]}
        self.assertEqual(pre_race_reported_starts(details,"2026-10-11",["A"]),{})


if __name__=="__main__":
    unittest.main()
