import unittest
from arvexq.prediction.career_readiness import assess_career_readiness

def run(date): return {"date": date, "finish": 2, "fieldSize": 10}
def horse(no, dates, reported=None, complete=True, status=""):
    rows=[run(d) for d in dates]; h={"horseNumber":no,"name":f"馬{no}","status":status,"allPastRuns":rows}
    if reported is not None: h["_careerHistoryAudit"]={"version":"arvexq-career-coverage-v1","requestedAtRaceDate":"2026-10-10","reportedStarts":reported,"observedRuns":len(rows),"paginationComplete":True,"complete":complete,"reportedStartsSource":"test","failedProviders":[]}
    return h
class CareerReadinessTests(unittest.TestCase):
    def race(self, horses): return {"id":"race-1","date":"2026-10-10","horses":horses}
    def test_complete(self): self.assertTrue(assess_career_readiness(self.race([horse(1,["2026-09-01"],1),horse(2,["2026-08-01"],1)]))["ready"])
    def test_without_audit_is_blocked(self): self.assertFalse(assess_career_readiness(self.race([horse(1,["2026-09-01"]),horse(2,["2026-08-01"],1)]))["ready"])
    def test_short_is_blocked(self): self.assertFalse(assess_career_readiness(self.race([horse(1,["2026-09-01"],2,False),horse(2,["2026-08-01"],1)]))["ready"])
    def test_debut(self): self.assertTrue(assess_career_readiness(self.race([horse(1,[],0),horse(2,[],0)]))["ready"])
    def test_scratch_ignored(self): self.assertTrue(assess_career_readiness(self.race([horse(1,["2026-09-01"],1),horse(2,["2026-08-01"],1),horse(3,[],status="出走取消")]))["ready"])
if __name__=='__main__': unittest.main()
