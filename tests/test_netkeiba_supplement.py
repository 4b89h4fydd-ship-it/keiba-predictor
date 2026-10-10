"""Sparse-NAR netkeiba supplement: EUC-JP search, exact identity, spaced headers."""
import unittest
from unittest import mock
import app

HEAD = "<tr><th>日付</th><th>開催</th><th>頭 数</th><th>着 順</th><th>距離</th><th>馬場</th></tr>"


def table(rows):
    return "<table>" + HEAD + "".join(
        f"<tr><td>{d}</td><td>1大井2</td><td>12</td><td>{f}</td><td>ダ1200</td><td>良</td></tr>" for d, f in rows) + "</table>"


def site(search, pages):
    def get(url, *a):
        if "pid=horse_list" in url:
            assert "%A5%C6" in url, "query must be EUC-JP"
            return search
        for hid, html in pages.items():
            if url.endswith(f"/horse/result/{hid}/"):
                return html
        raise AssertionError(url)
    return get


def listing(*items):
    return "<table>" + "".join(
        f'<tr><td><a href="https://db.netkeiba.com/horse/{h}/">{n}</a></td></tr>' for h, n in items) + "</table>"


class NetkeibaSupplementTests(unittest.TestCase):
    def test_spaced_headers_and_cutoff(self):
        get = site(listing(("2022100001", "テスト")),
                   {"2022100001": table([("2026/10/12", "1"), ("2026/09/01", "3"), ("2026/08/01", "2")])})
        with mock.patch.object(app, "_netkeiba_get", get):
            r = app._netkeiba_db_horse_history("テスト", "2026-10-10", 5)
        self.assertEqual(r["_netkeibaHorseId"], "2022100001")
        self.assertEqual([x["date"] for x in r["recentRaces"]], ["2026-09-01", "2026-08-01"])
        self.assertEqual(r["recentRaces"][0]["fieldSize"], 12)

    def test_partial_name_is_not_a_candidate(self):
        get = site(listing(("2022100002", "テストα")), {})
        with mock.patch.object(app, "_netkeiba_get", get):
            self.assertEqual(app._netkeiba_db_horse_history("テスト", "2026-10-10", 5)["recentRaces"], [])

    def test_current_runner_beats_retired_namesake(self):
        old = table([(f"2010/0{m}/01", "1") for m in range(1, 9)])
        cur = table([("2026/09/01", "4")])
        get = site(listing(("2006100001", "テスト"), ("2022100001", "テスト")),
                   {"2006100001": old, "2022100001": cur})
        with mock.patch.object(app, "_netkeiba_get", get):
            self.assertEqual(app._netkeiba_db_horse_history("テスト", "2026-10-10", 5)["_netkeibaHorseId"], "2022100001")


if __name__ == "__main__":
    unittest.main()
