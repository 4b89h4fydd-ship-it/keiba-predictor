"""Birth-year filter fallback in the verified netkeiba career
resolver.

Regression context (2026-11-25 production pack): シュテフィ
（名古屋10R 10番） carried five past runs in the same day's netkeiba
speed-index material, yet every career provider resolved nothing
(audit status "missing", no sourceHorseId) and she was published
with abilityScore null. The resolver searches by exact name and
then filters candidates by the birth year implied by the entry
sheet's age; when that filter empties the list, a horse whose exact
name exists exactly once in the whole database was still rejected.

The fallback keeps that single candidate — identity stays
unambiguous — and the pre-existing verification (complete listing
whose own career total equals its listed starts, all dates before
the race) binds the career exactly as before. Two or more
namesakes, or a same-year namesake, behave exactly as before.
"""
from __future__ import annotations

import unittest

from arvexq.databanks import netkeiba_career as nk

NAME = "テスト馬"
RACE = {"date": "2026-10-11", "circuit": "地方", "track": "大井",
        "id": "nar-2026-10-11-大井-11"}
HEADERS = ["日付", "開催", "レース名", "頭 数", "着 順", "騎手", "斤量",
           "距離", "馬場", "タイム", "通過", "馬体重"]


def _row(date, finish=2):
    values = [date, "1大井2", "C2", "12", str(finish), "テスト", "55",
              "ダ1200", "良", "1:15.5", "3-4-4-3", "480(+0)"]
    return "<tr>" + "".join(f"<td>{v}</td>" for v in values) + "</tr>"


def _listing(count=4):
    dates = [f"2026/08/{i:02d}" for i in range(1, count + 1)]
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in HEADERS)
            + "</tr>" + "".join(_row(d) for d in dates) + "</table>")


def _horse_page(name, hid):
    return ('<html><head><title>' + name + ' (Test) | netkeiba</title>'
            '<link rel="canonical" href="https://db.netkeiba.com/horse/'
            + hid + '/" /></head></html>')


def _list_page(name, hids):
    rows = "".join(
        f'<tr><td><a href="https://db.netkeiba.com/horse/{hid}/">{name}</a></td></tr>'
        for hid in hids)
    return f"<html><body><table>{rows}</table></body></html>"


def _site(search_html, pages):
    def get(url):
        if "pid=horse_list" in url:
            return search_html
        for hid, (result_html, total) in pages.items():
            if url.endswith(f"/horse/result/{hid}/"):
                return result_html
            if url.endswith(f"/horse/{hid}/"):
                return f"<p>通算成績 {total}戦</p>"
        raise AssertionError(url)
    return get


class BirthYearFallbackTests(unittest.TestCase):
    def test_single_namesake_with_mismatched_year_resolves(self):
        # Entry sheet says age 3 in 2026 (born 2023); the only
        # exact-name horse in the database was born in 2022.
        hid = "2022100001"
        get = _site(_horse_page(NAME, hid), {hid: (_listing(4), 4)})
        actual = nk.fetch_verified_career(
            get, {"name": NAME, "age": 3}, RACE, 200)
        self.assertEqual(actual["careerStartEvidence"]["starts"], 4)
        self.assertEqual(len(actual["allPastRuns"]), 4)
        self.assertEqual(
            actual["careerStartEvidence"]["sourceHorseId"], hid)

    def test_two_namesakes_with_mismatched_years_resolve_nothing(self):
        hids = ["2022100001", "2022100002"]
        pages = {hid: (_listing(4), 4) for hid in hids}
        get = _site(_list_page(NAME, hids), pages)
        actual = nk.fetch_verified_career(
            get, {"name": NAME, "age": 3}, RACE, 200)
        self.assertEqual(actual, {})

    def test_same_year_namesake_still_preferred(self):
        # One 2023-born and one 2022-born namesake; age 3 in 2026
        # must resolve the 2023-born one, exactly as before.
        young, old = "2023100009", "2022100001"
        pages = {young: (_listing(4), 4), old: (_listing(6), 6)}
        get = _site(_list_page(NAME, [young, old]), pages)
        actual = nk.fetch_verified_career(
            get, {"name": NAME, "age": 3}, RACE, 200)
        self.assertEqual(
            actual["careerStartEvidence"]["sourceHorseId"], young)
        self.assertEqual(actual["careerStartEvidence"]["starts"], 4)


if __name__ == "__main__":
    unittest.main()
