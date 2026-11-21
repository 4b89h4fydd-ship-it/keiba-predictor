import unittest
from arvexq.history import normalize_run
from arvexq.prediction.past_performance import observed_runs

class UpstreamCaseTests(unittest.TestCase):
    def test_jra_source_field_aliases(self):
        r={"date":"2026-10-10","finish":2,"fieldSize":9,"last3FRank":3,"last3FPercentile":0.8}
        n=normalize_run(r)
        self.assertEqual(n["last3fRank"],3)
        self.assertEqual(n["last3fPercentile"],0.8)
        h={"horseNumber":1,"recentRaces":[r]}
        self.assertAlmostEqual(observed_runs(h,{"date":"2026-10-14"})[0]["last3fRank"],3)
    def test_unobserved_still_unknown(self):
        r={"date":"2026-10-10","finish":2,"fieldSize":9}
        self.assertIsNone(normalize_run(r)["last3fRank"])

    def test_last3f_seconds_spellings_all_normalise(self):
        # B3 (2026-11-21): the stored records split across
        # spellings — the JRA official parser's last3FSeconds /
        # last3F and the long-form lastThreeFurlongs were
        # missing from normalize_run's alias list, so a run
        # carrying only those read as unmeasured here (and in
        # every consumer downstream of it).
        for field in ("last3FSeconds", "last3F", "lastThreeFurlongs"):
            r = {"date": "2026-10-10", "finish": 2, "fieldSize": 9,
                 field: 36.5}
            self.assertEqual(normalize_run(r)["last3f"], 36.5, field)

    def test_rewrite_past_run_spellings_all_normalise(self):
        # The publish lane's closing term reads past runs
        # through rewrite.data.normalize._past_run; it missed
        # last3F and lastThreeFurlongs.
        from rewrite.data.normalize import _past_run
        for field in ("last3FSeconds", "last3F", "lastThreeFurlongs",
                      "last3fSeconds", "last3f"):
            run = _past_run({field: 36.5}, "test")
            self.assertEqual(run.last3f_seconds.value, 36.5, field)

if __name__=="__main__":
    unittest.main()
