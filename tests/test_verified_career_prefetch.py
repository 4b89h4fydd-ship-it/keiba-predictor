"""Canonical heavy-lane career source replaces the old on-demand NAR scraper.

This suite deliberately exercises full listings, start verification, ambiguity,
missing measurements and cutoff safety, not a separate second fetcher.
"""
from __future__ import annotations
import unittest

from arvexq.databanks import netkeiba_career as nk
from arvexq.ingest.full_career import audit_career
from arvexq.ingest.fallback_enrichment import enrich_race_missing
from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities


NAME = "テスト馬"
HID = "2022100001"
RACE = {"date": "2026-10-11", "circuit": "地方", "track": "大井", "id": "nar-2026-10-11-大井-11"}


def row(date, finish=2, *, distance="ダ1200", track="1大井2", time="1:15.5"):
    values = [date, track, "C2", "12", str(finish), "テスト", "55",
              distance, "良", time, "3-4-4-3", "480(+0)"]
    return "<tr>" + "".join(f"<td>{v}</td>" for v in values) + "</tr>"


HEADERS = ["日付", "開催", "レース名", "頭 数", "着 順", "騎手", "斤量",
           "距離", "馬場", "タイム", "通過", "馬体重"]


def listing(count=16, *, future=False, sparse=False):
    dates = [f"2026/08/{i:02d}" for i in range(1, count+1)]
    content = "".join(row(x, distance="ダ1200" if not sparse else "", time="1:15.5" if not sparse else "")
                      for x in dates)
    if future:
        content += row("2026/10/12")
    return "<table><tr>" + "".join(f"<th>{h}</th>" for h in HEADERS) + "</tr>" + content + "</table>"


def source(name=NAME, hid=HID):
    return ('<html><head><title>'+name+' (Test) | netkeiba</title>'
            '<link rel="canonical" href="https://db.netkeiba.com/horse/'+hid+'/" /></head></html>')


def site(result_html, total, *, search=None, pages=None):
    pages = pages or {HID: (result_html,total)}
    def get(url):
        if "pid=horse_list" in url:
            return search if search is not None else source()
        for hid, pair in pages.items():
            if url.endswith(f"/horse/result/{hid}/"): return pair[0]
            if url.endswith(f"/horse/{hid}/"): return f"<p>通算成績 {pair[1]}戦</p>"
        raise AssertionError(url)
    return get


class VerifiedCareerTests(unittest.TestCase):
    def test_whole_history_is_fetched_before_race_with_five_visible(self):
        get = site(listing(future=True), 17)
        actual = nk.fetch_verified_career(get, {"name":NAME}, RACE, 200)
        self.assertEqual(actual["careerStartEvidence"]["starts"], 16)
        self.assertEqual(len(actual["allPastRuns"]), 16)
        self.assertEqual(len(actual["recentRaces"]), 5)
        self.assertEqual(actual["allPastRuns"][0]["date"], "2026-08-16")
        self.assertTrue(all(r["date"] < RACE["date"] for r in actual["allPastRuns"]))
        self.assertEqual(actual["allPastRuns"][0]["distance"],1200)
        self.assertEqual(actual["allPastRuns"][0]["track"],"大井")
        self.assertAlmostEqual(actual["allPastRuns"][0]["timeSeconds"],75.5)
        self.assertEqual(actual["allPastRuns"][0]["cornerPositions"],[3,4,4,3])
        horse = {"name":NAME,**actual}
        self.assertTrue(audit_career(horse, RACE["date"],200,[nk.SOURCE])["complete"])

    def test_verified_listing_keeps_observed_sectional_and_margin(self):
        heads = HEADERS + ["上り", "着差"]
        cells = ["2026/08/01", "1大井2", "C2", "12", "2", "テスト",
                 "55", "ダ1200", "良", "1:15.5", "3-4-4-3",
                 "480(+0)", "37.8", "クビ"]
        html = ("<table><tr>" + "".join("<th>"+v+"</th>" for v in heads) +
                "</tr><tr>" + "".join("<td>"+v+"</td>" for v in cells) +
                "</tr></table>")
        rows = nk.parse_verified_runs(html, RACE["date"], ["2026-08-01"])
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["last3fSeconds"], 37.8)
        self.assertEqual(rows[0]["marginText"], "クビ")
        self.assertNotIn("last3fRank", rows[0])
        self.assertNotIn("marginSeconds", rows[0])

    def test_japanese_racing_age_birth_year_identity(self):
        # A 4yo in 2026 was born in 2023, not 2022.
        self.assertEqual(nk._birth_year({"age": 4}, "2026-10-11"), 2023)
        self.assertEqual(nk._birth_year({"age": "牡4"}, "2026-10-11"), 2023)

    def test_partial_listing_with_verified_birth_year_retains_observed_runs(self):
        horse_id = "2023100001"
        actual = nk.fetch_verified_career(
            site(listing(5), 16, search=source(hid=horse_id),
                 pages={horse_id: (listing(5), 16)}),
            {"name": NAME, "age": 4}, RACE, 200)
        self.assertEqual(len(actual["recentRaces"]), 5)
        self.assertNotIn("careerStartEvidence", actual)
        self.assertTrue(all(r["date"] < RACE["date"] for r in actual["recentRaces"]))

    def test_missing_page_row_never_proves_entire_career(self):
        self.assertEqual(nk.fetch_verified_career(site(listing(15),16),
                         {"name":NAME},RACE,200),{})

    def test_name_collision_is_rejected(self):
        second="2022100002"
        search=("<table>"+ "".join(
                f'<tr><td><a href="https://db.netkeiba.com/horse/{h}/">{NAME}</a></td></tr>'
                for h in (HID,second))+"</table>")
        get=site(listing(),16,search=search,pages={HID:(listing(),16),second:(listing(),16)})
        self.assertEqual(nk.fetch_verified_career(get,{"name":NAME},RACE,200),{})

    def test_no_measurements_are_fabricated(self):
        raw=listing(3,sparse=True)
        # Dated totals remain evidence, but rows without distances must not
        # become synthetic speed/finish metrics.
        actual=nk.fetch_verified_career(site(raw,3),{"name":NAME},RACE,200)
        self.assertEqual(actual["careerStartEvidence"]["starts"],3)
        self.assertNotIn("allPastRuns",actual)

    def test_start_counts_not_forged_when_history_limit_is_five(self):
        actual=nk.fetch_verified_career(site(listing(),16),{"name":NAME},RACE,5)
        self.assertEqual(actual["careerStartEvidence"]["starts"],16)
        self.assertEqual(len(actual["allPastRuns"]),5)
        self.assertFalse(audit_career({"name":NAME,**actual},RACE["date"],5,[nk.SOURCE])["complete"])

    def test_existing_provider_retry_once_for_transient_http_failure(self):
        from arvexq.ingest.orchestrator import fetch_domain
        import asyncio
        attempts = []
        def temporarily_unavailable(horse, race, limit):
            attempts.append(limit)
            if len(attempts) == 1:
                raise TimeoutError("provider 503 timeout")
            return {"recentRaces": [{"date": "2026-09-01", "finish": 2}]}
        reg=DataBankRegistry()
        reg.register(DataSource(name="existing",circuit="NAR",priority=10,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history":temporarily_unavailable}))
        results=asyncio.run(fetch_domain("horse_history",
            {"horseNumber":1},RACE,100,circuit="NAR",bank_registry=reg))
        self.assertTrue(results[0].ok)
        self.assertEqual(len(attempts),2)
        self.assertEqual(results[0].data["recentRaces"][0]["finish"],2)

    def test_existing_provider_does_not_retry_invalid_or_empty_history(self):
        from arvexq.ingest.orchestrator import fetch_domain
        import asyncio
        calls=[]
        def empty_history(horse, race, limit):
            calls.append(1)
            return {}
        reg=DataBankRegistry()
        reg.register(DataSource(name="existing",circuit="NAR",priority=10,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history":empty_history}))
        results=asyncio.run(fetch_domain("horse_history",
            {"horseNumber":1},RACE,100,circuit="NAR",bank_registry=reg))
        self.assertTrue(results[0].ok)
        self.assertEqual(len(calls),1)
        self.assertEqual(results[0].data,{})

    def test_prefetch_pipeline_preserves_fixed_prediction_and_bets(self):
        rows=[{"date":f"2026-08-{i:02d}","track":"大井","distance":1200,
               "finish":2,"fieldSize":12} for i in range(1,7)]
        race={**RACE,"preRacePrediction":{"frozen":True,"items":[1]},
              "preRaceBet":{"fixedBeforePost":True,"items":["ワイド"]},
              "horses":[{"horseNumber":1,"name":NAME,"allPastRuns":rows[:2],"recentRaces":rows[:2]}]}
        provider=DataSource(name=nk.SOURCE,circuit="NAR",priority=50,
                            capabilities=SourceCapabilities(horse_history=True),
                            fetchers={"horse_history":lambda h,r,limit: nk.fetch_verified_career(
                                site(listing(),16),h,r,limit)})
        reg=DataBankRegistry()
        reg.register(provider)
        import asyncio
        out=asyncio.run(enrich_race_missing(race,bank_registry=reg,history_limit=200))
        h=out["horses"][0]
        self.assertEqual(len(h["allPastRuns"]),16)
        self.assertEqual(len(h["recentRaces"]),5)
        self.assertTrue(h["_careerHistoryAudit"]["complete"])
        self.assertEqual(out["preRacePrediction"],race["preRacePrediction"])
        self.assertEqual(out["preRaceBet"],race["preRaceBet"])
        self.assertEqual(len(race["horses"][0]["allPastRuns"]),2)


if __name__ == "__main__":
    unittest.main()
