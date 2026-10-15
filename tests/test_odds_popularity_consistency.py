"""Odds popularity must be derived from the same prices ultimately displayed."""
import unittest
from unittest.mock import patch
from app import _parse_nar_live_odds_html, _merge_live_market_rows


class OddsPopularityConsistencyTests(unittest.TestCase):
    def test_header_popularity_cannot_survive_a_different_final_price(self):
        html = """<table>
        <tr><th>馬番</th><th>単勝</th><th>人気</th></tr>
        <tr><td>1</td><td>9.9</td><td>1</td></tr>
        <tr><td>2</td><td>2.0</td><td>2</td></tr>
        </table>"""
        parsed = _parse_nar_live_odds_html(html)
        self.assertEqual(parsed[1]["winOdds"], 9.9)
        self.assertEqual(parsed[1]["popularity"], 2)
        self.assertEqual(parsed[2]["popularity"], 1)

    def test_flat_second_pass_replaces_first_pass_rank(self):
        html = """<table>
        <tr><th>馬番</th><th>単勝</th><th>人気</th></tr>
        <tr><td>1</td><td>2.1</td><td>1</td></tr>
        <tr><td>2</td><td>7.3</td><td>2</td></tr>
        </table><table>
        <tr><td>1</td><td>1</td><td>甲</td><td>8.0</td></tr>
        <tr><td>2</td><td>2</td><td>乙</td><td>1.8</td></tr>
        </table>"""
        parsed = _parse_nar_live_odds_html(html)
        self.assertEqual(parsed[1]["winOdds"], 8.0)
        self.assertEqual(parsed[2]["winOdds"], 1.8)
        self.assertEqual((parsed[1]["popularity"], parsed[2]["popularity"]), (2, 1))

    def test_changed_price_invalidates_old_rank_without_new_rank(self):
        saved = {"horses": [
            {"horseNumber": 1, "winOdds": 8.9, "popularity": 1},
            {"horseNumber": 2, "winOdds": 2.4, "popularity": 2},
        ]}
        with patch("app.RACEDB.odds_latest", return_value=[]):
            rows = _merge_live_market_rows("nar-test", [{"horseNumber": 1, "winOdds": 3.0}], saved)
        self.assertEqual(rows[0]["winOdds"], 3.0)
        self.assertNotIn("popularity", rows[0])
        self.assertEqual(rows[1]["popularity"], 2)
        with patch("app.RACEDB.odds_latest", return_value=[]):
            rows = _merge_live_market_rows("nar-test", [{"horseNumber": 1, "winOdds": 3.0, "popularity": 2}], saved)
        self.assertEqual(rows[0]["popularity"], 2)


if __name__ == "__main__":
    unittest.main()
