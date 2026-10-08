import unittest
from unittest.mock import patch

from arvexq.ingest.official_changes import parse_nar_changes, collect_nar_changes
from scripts.arvexq_live_sync import apply_official_scratch_changes, merge_live, horse_live_rows

OFFICIAL_HTML = """<html><h2>2026年10月8日（木） 園田競馬 当日メニュー</h2>
<table><tr><th>競走</th><th>発走時刻</th><th>変更</th></tr>
<tr><td>5R</td><td>12:40</td><td>有</td></tr></table>
<h3>変更情報</h3><table><tr>
<th>競走</th><th>馬番</th><th>馬名</th><th>変更区分</th><th>変更理由</th><th>変更内容</th>
</tr><tr><td>5R</td><td>4</td><td>ミルトコルサ</td><td>出走取消</td>
<td>馬体故障</td><td></td></tr>
<tr><td>2R</td><td>11</td><td>別の馬</td><td>騎手変更</td><td>負傷</td><td></td></tr>
<tr><td>10R</td><td>7</td><td>テスト除外馬</td><td>競走除外</td><td>事故</td><td></td></tr>
</table></html>"""


class OfficialScratchTests(unittest.TestCase):
    def test_race_list_uses_race_and_horse_numbers_separately(self):
        self.assertEqual(parse_nar_changes(OFFICIAL_HTML), {
            5: {4: "出走取消"}, 10: {7: "競走除外"}
        })

    def test_unavailable_venue_does_not_drop_other_venues(self):
        with patch("arvexq.ingest.official_changes.fetch_track_changes",
                   side_effect=lambda date, track, code: (
                       {5: {4: "出走取消"}} if track == "園田" else
                       (_ for _ in ()).throw(RuntimeError("down")))):
            found = collect_nar_changes("2026-10-08", {"園田": "27", "大井": "20"})
        self.assertEqual(found, {"nar-2026-10-08-園田-05": {4: "出走取消"}})

    def test_cancel_overrides_stale_odds_without_erasing_history(self):
        base = {
            "id": "nar-2026-10-08-園田-05",
            "horses": [
                {"horseNumber": 4, "name": "ミルトコルサ",
                 "winOdds": 5.4, "popularity": 3,
                 "recentRaces": [{"finish": 2}]},
                {"horseNumber": 5, "name": "稼働馬", "winOdds": 3.0}
            ],
            "preparedMeta": {"diagnosisReady": True},
            "preRacePrediction": {"locked": True},
        }
        updated, applied = apply_official_scratch_changes(base, {4: "出走取消"})
        self.assertEqual(applied, [4])
        self.assertEqual(updated["horses"][0]["status"], "出走取消")
        self.assertTrue(updated["horses"][0]["scratched"])
        self.assertIsNone(updated["horses"][0]["winOdds"])
        self.assertEqual(updated["horses"][0]["recentRaces"], [{"finish": 2}])
        self.assertEqual(updated["preRacePrediction"], base["preRacePrediction"])
        self.assertIsNone(base["horses"][0].get("scratched"))

        payload = horse_live_rows(updated)
        self.assertEqual(payload[0]["horse_status"], "出走取消")
        after = merge_live(updated, {"horses": [{"horseNumber": 4, "scratched": False,
                                                 "status": "", "winOdds": 9.9}]},
                           None, False)
        self.assertTrue(after["horses"][0]["scratched"])
        self.assertEqual(after["horses"][0]["status"], "出走取消")


if __name__ == "__main__":
    unittest.main()
