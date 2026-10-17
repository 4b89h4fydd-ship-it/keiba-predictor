import unittest
from arvexq.research.preoff_coverage_audit import audit_races


class CoverageAuditTests(unittest.TestCase):
    def test_missing_history_reported_without_fabrication(self):
        races=[{"date":"2026-10-14","circuit":"中央","horses":[
            {"horseNumber":1},
            {"horseNumber":2,"recentRaces":[
                {"date":"2026-10-10","finish":2,"fieldSize":8}]}]}]
        out=audit_races(races)
        self.assertEqual(out["overall"]["horses"],2)
        self.assertEqual(out["overall"]["withoutFiveRunEvidence"],1)
        self.assertEqual(out["overall"]["sectionalMissing"],2)
        self.assertEqual(out["overall"]["fiveRunComplete"],0)
        self.assertEqual(out["overall"]["fiveRunCoverageRate"],0.0)
        self.assertEqual(out["overall"]["noObservedRuns"],1)
        self.assertEqual(out["overall"]["missingAnyRunRate"],0.5)
        self.assertEqual(out["byCircuit"]["中央"]["fiveRunCoverageRate"],0.0)
        self.assertEqual(out["overall"]["sectionalMissingWithObservedFinish"],1)
        self.assertEqual(out["byCircuit"]["中央"]["races"],1)

if __name__=="__main__":
    unittest.main()
