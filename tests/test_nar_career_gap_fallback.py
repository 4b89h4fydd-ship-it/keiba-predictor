"""NAR fallback must detect lifetime gaps beyond the five-run display cap."""
from __future__ import annotations
import copy
import unittest
from unittest.mock import patch

from arvexq.ingest.nar_career_coverage import career_gap_candidates


def sample_run(month: int, day: int, source="official"):
    return {"date": f"2026-{month:02d}-{day:02d}", "track": "大井",
            "distance": 1200, "finish": 2, "fieldSize": 12,
            "timeSeconds": 75.5, "source": source}


class GapAwareSelectionTests(unittest.TestCase):
    def test_eighteen_out_of_seventy_four_is_repaired_despite_five_plus(self):
        coverage = {"counts": {"old": 18, "complete": 74, "unknown": 22,
                               "short": 3, "debut": 0}}
        required = {"old": 74, "complete": 74, "short": 8, "debut": 0}
        self.assertEqual(career_gap_candidates(
            coverage, required, ["old", "complete", "unknown", "short", "debut"]),
            ["old", "short", "debut", "unknown"])
        # The zero-start target is explicitly verified and must not be fetched.
        # The unknown-career 22-start horse is still unverified.

    def test_duplicates_not_fetched_by_name(self):
        self.assertEqual(career_gap_candidates(
            {"counts": {"A": 7, "B": 6}}, {"A": 74, "B": 40},
            ["A", "A", "B"]), ["B"])

    def test_sources_with_more_starts_than_declared_are_not_trusted(self):
        self.assertEqual(career_gap_candidates(
            {"counts": {"A": 8, "B": 4}}, {"A": 7, "B": 5},
            ["A", "B"]), ["B"])


class FullFallbackFetchTests(unittest.TestCase):
    @staticmethod
    def _history_page():
        heads = ["日付", "開催", "レース名", "頭数", "着順", "騎手",
                 "斤量", "距離", "馬場", "タイム", "通過", "馬体重"]
        rows = ["<tr>" + "".join(f"<th>{h}</th>" for h in heads) + "</tr>"]
        for day in range(1, 17):
            columns = [f"2026/08/{day:02d}", "大井", "C2", "12", "2",
                       "テスト", "55", "ダ1200", "良", "1:15.5",
                       "3-4-4-3", "480(+0)"]
            rows.append("<tr>" + "".join(f"<td>{v}</td>" for v in columns) + "</tr>")
        for day in ("2026/10/11", "2026/10/12"):
            columns = [day, "大井", "C2", "12", "1", "テスト", "55",
                       "ダ1200", "良", "1:13.3", "1-1-1-1", "480(+0)"]
            rows.append("<tr>" + "".join(f"<td>{v}</td>" for v in columns) + "</tr>")
        return "<table>" + "".join(rows) + "</table>"

    def test_history_parser_returns_all_preoff_starts_up_to_capacity(self):
        import app
        html = self._history_page()
        with patch("arvexq.databanks.netkeiba_career.search_url", return_value="search"), \
             patch("arvexq.databanks.netkeiba_career.parse_search",
                   return_value=[{"id": "1234567890"}]), \
             patch.object(app, "_netkeiba_get", side_effect=lambda url, *_: html):
            result = app._netkeiba_db_horse_history("テスト馬", "2026-10-11", 200)
            capped = app._netkeiba_db_horse_history("テスト馬", "2026-10-11", 7)
        self.assertEqual(len(result["allPastRuns"]), 16)
        self.assertEqual(len(result["recentRaces"]), 5)
        self.assertEqual(len(capped["allPastRuns"]), 7)
        self.assertNotIn("2026-10-11", [r["date"] for r in result["allPastRuns"]])
        self.assertNotIn("2026-10-12", [r["date"] for r in result["allPastRuns"]])

    def test_entire_fallback_merges_with_local_history_without_removing_locks(self):
        import app
        old_runs=[sample_run(7,day) for day in range(1,7)]
        extra_runs=[sample_run(7,day,"secondary") for day in range(4,10)]
        extra_runs+= [sample_run(8,day,"secondary") for day in range(1,7)]
        detail={"date":"2026-10-11", "circuit":"地方", "horses":[
            {"name":"テスト馬", "horseNumber":1, "allPastRuns":old_runs,
             "recentRaces":old_runs[-5:],
             "_careerHistoryAudit":{"complete":False,"reportedStarts":74}},
        ],"preRacePrediction":{"frozen":True}, "preRaceBet":{"fixedBeforePost":True}}
        previous=copy.deepcopy(detail)
        enriched=app._merge_enrichment(detail, {"netkeibaRows":[
            {"name":"テスト馬", "allPastRuns":extra_runs,
             "recentRaces":extra_runs[:5], "source":"netkeiba DB補完"}]})
        horse=enriched["horses"][0]
        self.assertEqual(len(horse["allPastRuns"]),15)
        self.assertEqual(len(horse["recentRaces"]),5)
        self.assertFalse(horse["_careerHistoryAudit"]["complete"])
        self.assertEqual(enriched["preRacePrediction"],previous["preRacePrediction"])
        self.assertEqual(enriched["preRaceBet"],previous["preRaceBet"])
        self.assertEqual(len(previous["horses"][0]["allPastRuns"]),6)

    def test_fallback_pool_passes_full_limit(self):
        import app
        calls=[]
        def fake_history(name, cutoff, limit):
            calls.append((name,cutoff,limit))
            return {"name":name,"recentRaces":[sample_run(8,16)],
                    "allPastRuns":[sample_run(8,d) for d in range(1,17)]}
        with patch.object(app,"_netkeiba_db_horse_history",side_effect=fake_history), \
             patch.dict(app._enrich_data,{},clear=True), \
             patch.dict(app._enrich_jobs,{},clear=True), \
             patch.dict("os.environ",{"NETKEIBA_DB_HISTORY_WORKERS":"1"},clear=False):
            count=app._supplement_sparse_nar_history("nar-2026-10-11-大井-01",
                                                      ["A"],"2026-10-11")
            cached=copy.deepcopy(app._enrich_data["nar-2026-10-11-大井-01"])
        self.assertEqual(count,1)
        self.assertGreater(calls[0][2],5)
        self.assertEqual(len(cached["netkeibaRows"][0]["allPastRuns"]),16)


if __name__ == "__main__":
    unittest.main()
