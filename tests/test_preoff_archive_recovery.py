import unittest
from arvexq.ingest.career_transport import pack_horse
from arvexq.prediction.past_performance import observed_runs


class ArchiveRecoveryTests(unittest.TestCase):
    def test_missing_visible_runs_are_recovered(self):
        race={"date":"2026-10-14"}
        runs=[{"date":f"2026-10-{day:02d}","finish":i+1,"fieldSize":10}
              for i,day in enumerate([12,10,8,6,4])]
        original={"horseNumber":1,"recentRaces":runs}
        packed=pack_horse(original,race["date"])
        packed["recentRaces"]=packed["recentRaces"][:1]
        packed["allPastRuns"]=packed["allPastRuns"][:1]
        recovered=observed_runs(packed,race,limit=5)
        self.assertEqual(len(recovered),5)
        self.assertEqual(recovered[0]["date"],"2026-10-12")

    def test_invalid_archive_does_not_invent_runs(self):
        race={"date":"2026-10-14"}
        runs=[{"date":"2026-10-12","finish":2,"fieldSize":8}]
        packed=pack_horse({"horseNumber":1,"recentRaces":runs},race["date"])
        packed["allPastRuns"]=[]
        packed["careerArchive"]["storedRunCount"]=5
        with self.assertRaises(ValueError):
            observed_runs(packed,race,limit=5)

if __name__=="__main__":
    unittest.main()
