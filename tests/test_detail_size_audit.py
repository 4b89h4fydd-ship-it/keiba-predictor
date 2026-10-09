"""Regression tests for bounded, privacy-safe D1 detail size diagnostics."""
import io
import unittest
from contextlib import redirect_stdout
from scripts.arvexq_detail_size_audit import encoded_size, summarize_detail, print_size_audit


class DetailSizeAuditTest(unittest.TestCase):
    def test_counts_large_duplicate_fields_without_values(self):
        h={"name":"PRIVATE HORSE", "horseNumber":1,
           "allPastRuns":[{"date":"2026-09-09","sourceBlob":"x"*190000}],
           "recentRaces":[{"date":"2026-09-09"}],
           "careerArchive":{"payload":"X"*160000},
           "integratedEvaluation":{"longField":"z"*150000}}
        d={"id":"race-1","horses":[h],"title":"PRIVATE RACE"}
        result=summarize_detail(d)
        self.assertEqual(result["horses"],1)
        self.assertEqual(result["totalBytes"],encoded_size(d))
        self.assertGreater(result["allPastRunsBytes"],190000)
        self.assertGreater(result["historyArchiveBytes"],160000)
        self.assertGreater(result["analysisBytes"],150000)
        output=io.StringIO()
        with redirect_stdout(output):
            print_size_audit(d,max_detail_bytes=200000)
        log=output.getvalue()
        self.assertIn("D1_DETAIL_SIZE_BREAKDOWN",log)
        self.assertNotIn("PRIVATE HORSE",log)
        self.assertNotIn("PRIVATE RACE",log)
        self.assertNotIn("xxxxxx",log)
        self.assertNotIn("XXXXXX",log)
        self.assertNotIn("zzzzzz",log)

    def test_small_detail_is_silent(self):
        stream=io.StringIO()
        with redirect_stdout(stream):
            report=print_size_audit({"id":"a","horses":[]})
        self.assertEqual(stream.getvalue(),"")
        self.assertEqual(report["horses"],0)


if __name__=="__main__":
    unittest.main()
