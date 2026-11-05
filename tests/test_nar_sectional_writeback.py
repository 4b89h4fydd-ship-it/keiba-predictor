"""Sectional write-back repairs (2026-11-05 sectional collection audit).

1. The NAR official prior-result adapter could never fire for live-era
   primary career rows because they carry no raceNumber. It now resolves
   the number by a verified scan of that day's official pages: a candidate
   page counts only when its own finisher row for the horse agrees with
   the facts already on the row (real finishing place and/or recorded
   time). A name match alone never authorises a fill.
2. _merge_result_fields writes the finisher's own performance (last 3F
   above all) back onto the horse record as raceResult.
3. The NAR official result parser takes the race lap table into the
   result when the venue publishes one.
"""
from __future__ import annotations

import unittest

from arvexq.databanks.legacy_bridge import _nar_official_past_result_adapter
from arvexq.ingest.odds_results_merge import _merge_result_fields


def _adapter(pages, calls):
    def official(detail):
        calls.append(detail["raceNumber"])
        return pages.get(detail["raceNumber"])
    return _nar_official_past_result_adapter({"_nar_official_result_fast": official})


class MissingRaceNumberResolutionTests(unittest.TestCase):
    def test_scan_resolves_number_and_fills_last3f(self):
        pages = {
            5: {"finishers": [{"finish": 1, "name": "別馬", "timeSeconds": 50.9}]},
            6: {"finishers": [
                {"finish": 1, "name": "対象馬", "horseNumber": 4,
                 "timeSeconds": 51.4, "last3FSeconds": 37.1},
                {"finish": 2, "name": "他馬", "horseNumber": 7,
                 "timeSeconds": 52.0, "last3FSeconds": 37.0},
            ]},
        }
        calls = []
        fetch = _adapter(pages, calls)
        horse = {"name": "対象馬", "recentRaces": [{
            "date": "2026-10-15", "track": "園田", "finish": 1,
            "timeSeconds": 51.4, "horseNumber": 4,
        }]}
        out = fetch(horse, {"date": "2026-11-04"}, 5)
        self.assertEqual(calls, [1, 2, 3, 4, 5, 6])
        observed = out["recentRaces"][0]
        self.assertEqual(observed["raceNumber"], 6)
        self.assertEqual(observed["last3fSeconds"], 37.1)
        self.assertEqual(observed["timeBehindWinner"], 0.0)

    def test_scan_rejects_page_whose_row_disagrees(self):
        pages = {
            3: {"finishers": [
                {"finish": 3, "name": "対象馬", "horseNumber": 4,
                 "timeSeconds": 60.0, "last3FSeconds": 39.9},
            ]},
        }
        calls = []
        fetch = _adapter(pages, calls)
        horse = {"name": "対象馬", "recentRaces": [{
            "date": "2026-10-15", "track": "園田", "finish": 1,
            "timeSeconds": 51.4, "horseNumber": 4,
        }]}
        self.assertEqual(fetch(horse, {"date": "2026-11-04"}, 5), {})

    def test_scan_requires_positive_evidence_beyond_name(self):
        pages = {
            6: {"finishers": [
                {"finish": 1, "name": "対象馬", "horseNumber": 4,
                 "timeSeconds": 51.4, "last3FSeconds": 37.1},
            ]},
        }
        calls = []
        fetch = _adapter(pages, calls)
        # finish=0 is the unknown sentinel and no time was recorded:
        # the name (and post position) alone must not authorise a fill.
        horse = {"name": "対象馬", "recentRaces": [{
            "date": "2026-10-15", "track": "園田", "finish": 0,
            "horseNumber": 4,
        }]}
        self.assertEqual(fetch(horse, {"date": "2026-11-04"}, 5), {})

    def test_known_race_number_never_scans(self):
        pages = {6: {"finishers": [
            {"finish": 1, "name": "対象馬", "timeSeconds": 51.4,
             "last3FSeconds": 37.1},
            {"finish": 2, "name": "他馬", "timeSeconds": 52.0},
        ]}}
        calls = []
        fetch = _adapter(pages, calls)
        horse = {"name": "対象馬", "recentRaces": [{
            "date": "2026-10-15", "track": "園田", "raceNumber": 6,
            "finish": 1, "timeSeconds": 51.4,
        }]}
        out = fetch(horse, {"date": "2026-11-04"}, 5)
        self.assertEqual(calls, [6])
        self.assertEqual(out["recentRaces"][0]["last3fSeconds"], 37.1)

    def test_scan_pages_are_shared_across_horses(self):
        pages = {
            2: {"finishers": [
                {"finish": 1, "name": "甲馬", "timeSeconds": 51.4,
                 "last3FSeconds": 37.1},
                {"finish": 2, "name": "乙馬", "timeSeconds": 52.0},
            ]},
            3: {"finishers": [
                {"finish": 1, "name": "乙馬", "timeSeconds": 61.0,
                 "last3FSeconds": 38.5},
                {"finish": 2, "name": "丙馬", "timeSeconds": 61.5},
            ]},
        }
        calls = []
        fetch = _adapter(pages, calls)
        first = {"name": "甲馬", "recentRaces": [{
            "date": "2026-10-15", "track": "園田", "finish": 1,
            "timeSeconds": 51.4}]}
        fetch(first, {"date": "2026-11-04"}, 5)
        second = {"name": "乙馬", "recentRaces": [{
            "date": "2026-10-15", "track": "園田", "finish": 1,
            "timeSeconds": 61.0}]}
        out = fetch(second, {"date": "2026-11-04"}, 5)
        # Pages 1 and 2 were already probed for the first horse; only the
        # genuinely new page 3 is fetched for the second horse.
        self.assertEqual(calls, [1, 2, 3])
        self.assertEqual(out["recentRaces"][0]["raceNumber"], 3)


class ResultWriteBackTests(unittest.TestCase):
    def test_finisher_performance_written_back_to_horse(self):
        detail = {"date": "2026-11-04", "track": "園田", "raceNumber": 1,
                  "horses": [{"horseNumber": 4, "name": "対象馬"}]}
        result = {"source": "NAR公式競走成績", "finishers": [{
            "horseNumber": 4, "finish": 1, "timeSeconds": 51.4,
            "last3FSeconds": 37.1, "cornerPositions": [1, 1],
            "winOdds": 4.7, "bodyWeight": 481, "bodyWeightChange": 2,
        }]}
        merged = _merge_result_fields(detail, result)
        horse = merged["horses"][0]
        # Pre-existing write-backs are untouched.
        self.assertEqual(horse["winOdds"], 4.7)
        self.assertEqual(horse["bodyWeight"], 481)
        record = horse["raceResult"]
        self.assertEqual(record["finish"], 1)
        self.assertEqual(record["timeSeconds"], 51.4)
        self.assertEqual(record["last3FSeconds"], 37.1)
        self.assertEqual(record["cornerPositions"], [1, 1])
        self.assertEqual(record["date"], "2026-11-04")
        self.assertEqual(record["track"], "園田")
        self.assertEqual(record["raceNumber"], 1)
        self.assertEqual(record["source"], "NAR公式競走成績")

    def test_no_performance_no_record(self):
        detail = {"date": "2026-11-04", "track": "園田", "raceNumber": 1,
                  "horses": [{"horseNumber": 4, "name": "対象馬"}]}
        result = {"source": "netkeiba", "finishers": [{
            "horseNumber": 4, "winOdds": 4.7}]}
        merged = _merge_result_fields(detail, result)
        self.assertNotIn("raceResult", merged["horses"][0])


class LapTableTests(unittest.TestCase):
    def test_lap_times_parsed_when_published(self):
        from bs4 import BeautifulSoup
        import app
        html = """
        <table><tr><td>ハロンタイム</td><td>2.3</td><td>12.0</td>
        <td>11.5</td><td>12.5</td><td>13.1</td></tr>
        <tr><td>通過タイム</td><td>2.3</td><td>14.3</td></tr></table>
        """
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(app._nar_race_lap_times(soup),
                         [2.3, 12.0, 11.5, 12.5, 13.1])

    def test_no_lap_table_returns_empty(self):
        from bs4 import BeautifulSoup
        import app
        soup = BeautifulSoup(
            "<table><tr><td>上がりタイム</td><td>49.1</td></tr></table>",
            "html.parser")
        self.assertEqual(app._nar_race_lap_times(soup), [])


if __name__ == "__main__":
    unittest.main()
