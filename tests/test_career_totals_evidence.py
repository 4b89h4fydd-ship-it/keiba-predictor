"""Start-count evidence: parsing, identity, race-date binding, end-to-end state."""
from __future__ import annotations
import unittest
from arvexq.databanks import netkeiba_career as nk
from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities
from arvexq.ingest.fallback_enrichment import enrich_race_missing
from arvexq.ingest.full_career import audit_career
from arvexq.career_missing import build_career_analysis

RACE = {"date": "2026-10-10", "circuit": "地方"}


def run(month, day, finish=2):
    return {"date": f"2026-{month:02d}-{day:02d}", "track": "大井", "distance": 1200,
            "surface": "ダート", "condition": "良", "finish": finish, "fieldSize": 12}


def listing_html(rows):
    body = "".join(f"<tr><td>{d}</td><td>大井</td><td>{f}</td></tr>" for d, f in rows)
    return f"<table><tr><th>日付</th><th>開催</th><th>着順</th></tr>{body}</table>"


def top_html(total):
    return f"<html><head><title>テスト (Test) | 競走馬データ</title></head><body><td>通算成績</td><td>{total}戦2勝 [2-1-0-3]</td></body></html>"


def horse_page(hid, name="テスト"):
    return (f'<html><head><title>{name} (Test) | netkeiba</title>'
            f'<link rel="canonical" href="https://db.netkeiba.com/horse/{hid}/" /></head></html>')


def search_list(*items):
    rows = "".join(f'<tr><td></td><td><a href="https://db.netkeiba.com/horse/{h}/">{n}</a></td></tr>'
                   for h, n in items)
    return f"<table>{rows}</table>"


ROWS = [("2026/10/20", "1"), ("2026/09/01", "3"), ("2026/08/01", "取"),
        ("2026/07/01", "中"), ("2026/06/01", "5")]


class ParserTests(unittest.TestCase):
    def test_search_redirect_and_exact_name_filter(self):
        self.assertEqual(nk.parse_search(horse_page("2022100001"), "テスト")[0]["id"], "2022100001")
        self.assertEqual(nk.parse_search(horse_page("2022100001", "別馬"), "テスト"), [])
        found = nk.parse_search(search_list(("2022100001", "テスト"), ("2022100002", "テストα")), "テスト")
        self.assertEqual([c["id"] for c in found], ["2022100001"])

    def test_search_url_is_euc_jp(self):
        self.assertIn("%A5%C6", nk.search_url("テスト"))

    def test_total_matches_listing_and_binds_to_race_date(self):
        stats = nk.build_stats(nk.parse_listing(listing_html(ROWS)), nk.parse_total(top_html(4)),
                               "2026-10-10", "2022100001")
        self.assertEqual(stats["starts"], 3)  # 中止 counts, 取消 does not, future excluded
        self.assertEqual(stats["startDates"], ["2026-06-01", "2026-07-01", "2026-09-01"])
        self.assertEqual(stats["nonFinishStarts"], 1)
        self.assertEqual(stats["asOfRaceDate"], "2026-10-10")

    def test_total_mismatch_is_not_evidence(self):
        self.assertIsNone(nk.build_stats(nk.parse_listing(listing_html(ROWS)), 5, "2026-10-10", "x"))
        self.assertIsNone(nk.build_stats(nk.parse_listing(listing_html(ROWS)), None, "2026-10-10", "x"))

    def test_unreadable_row_or_duplicate_date_is_not_evidence(self):
        self.assertIsNone(nk.build_stats(nk.parse_listing(listing_html([("2026/09/01", "?")])), 1, "2026-10-10", "x"))
        dup = [("2026/09/01", "1"), ("2026/09/01", "2")]
        self.assertIsNone(nk.build_stats(nk.parse_listing(listing_html(dup)), 2, "2026-10-10", "x"))

    def test_missing_table_is_not_evidence(self):
        self.assertIsNone(nk.parse_listing("<p>no table</p>"))


def fake_site(candidates, pages):
    def get(url):
        if "pid=horse_list" in url:
            return candidates
        for hid, (listing, total) in pages.items():
            if url.endswith(f"/horse/result/{hid}/"):
                return listing
            if url.endswith(f"/horse/{hid}/"):
                return total
        raise AssertionError(url)
    return get


class FetchTests(unittest.TestCase):
    def test_unique_identity_returns_stats_only(self):
        get = fake_site(horse_page("2022100001"), {"2022100001": (listing_html(ROWS), top_html(4))})
        out = nk.fetch_career_totals(get, {"name": "テスト", "recentRaces": [run(9, 1)]}, RACE)
        self.assertEqual(set(out), {"careerStartEvidence"})  # no runs: prediction inputs unchanged
        self.assertEqual(out["careerStartEvidence"]["starts"], 3)

    def test_ambiguous_identity_is_not_evidence(self):
        get = fake_site(search_list(("2022100001", "テスト"), ("2019100009", "テスト")),
                        {"2022100001": (listing_html(ROWS), top_html(4)),
                         "2019100009": (listing_html(ROWS), top_html(4))})
        self.assertEqual(nk.fetch_career_totals(get, {"name": "テスト"}, RACE), {})

    def test_birth_year_disambiguates(self):
        get = fake_site(search_list(("2022100001", "テスト"), ("2019100009", "テスト")),
                        {"2022100001": (listing_html(ROWS), top_html(4)),
                         "2019100009": (listing_html(ROWS), top_html(4))})
        out = nk.fetch_career_totals(get, {"name": "テスト", "age": "4"}, RACE)
        self.assertEqual(out["careerStartEvidence"]["sourceHorseId"], "2022100001")

    def test_known_run_absent_from_source_is_not_evidence(self):
        get = fake_site(horse_page("2022100001"), {"2022100001": (listing_html(ROWS), top_html(4))})
        self.assertEqual(nk.fetch_career_totals(get, {"name": "テスト", "recentRaces": [run(5, 5)]}, RACE), {})


def registry_with(runs, stats=None, *, evidence_error=False, second_stats=None):
    reg = DataBankRegistry()
    reg.register(DataSource(name="official_test", circuit="NAR", priority=1,
                            capabilities=SourceCapabilities(horse_history=True),
                            fetchers={"horse_history": lambda h, r, limit: {"allPastRuns": runs}}))

    def evidence(h, r, limit):
        if evidence_error:
            raise RuntimeError("evidence outage")
        return {"careerStartEvidence": stats} if stats else {}
    reg.register(DataSource(name="netkeiba_career_totals", circuit="both", priority=60,
                            capabilities=SourceCapabilities(horse_history=True),
                            fetchers={"horse_history": evidence}))
    if second_stats:
        reg.register(DataSource(name="other_totals", circuit="both", priority=70,
                                capabilities=SourceCapabilities(horse_history=True),
                                fetchers={"horse_history": lambda h, r, limit: {"careerStartEvidence": second_stats}}))
    return reg


def stats_for(dates, source="netkeiba_career_totals"):
    return {"starts": len(dates), "asOfRaceDate": "2026-10-10", "startDates": dates, "source": source}


class EndToEndTests(unittest.IsolatedAsyncioTestCase):
    async def enrich(self, reg):
        out = await enrich_race_missing({"date": "2026-10-10", "circuit": "地方",
                                         "horses": [{"horseNumber": 1, "name": "テスト"}]},
                                        bank_registry=reg, history_limit=1000)
        return out["horses"][0]

    async def test_matching_source_total_makes_career_complete(self):
        runs = [run(6, 1), run(7, 1), run(9, 1)]
        h = await self.enrich(registry_with(runs, stats_for(["2026-06-01", "2026-07-01", "2026-09-01"])))
        self.assertTrue(h["_careerHistoryAudit"]["complete"])
        self.assertEqual(h["_careerHistoryAudit"]["reportedStartsSource"], "netkeiba_career_totals")
        a = build_career_analysis(h, RACE)
        self.assertEqual(a["career_state"], "complete")
        self.assertEqual(a["data_limitation"], "complete")

    async def test_source_lists_more_starts_is_partial(self):
        runs = [run(7, 1), run(9, 1)]
        h = await self.enrich(registry_with(runs, stats_for(["2026-06-01", "2026-07-01", "2026-09-01"])))
        self.assertEqual(h["_careerHistoryAudit"]["unobservedDates"], ["2026-06-01"])
        self.assertEqual(build_career_analysis(h, RACE)["career_state"], "partially-acquired")

    async def test_same_count_different_dates_is_not_complete(self):
        runs = [run(6, 2), run(7, 1), run(9, 1)]
        h = await self.enrich(registry_with(runs, stats_for(["2026-06-01", "2026-07-01", "2026-09-01"])))
        self.assertFalse(h["_careerHistoryAudit"]["complete"])
        self.assertNotEqual(build_career_analysis(h, RACE)["acquisition_status"], "complete")

    async def test_conflicting_sources_are_not_evidence(self):
        runs = [run(7, 1), run(9, 1)]
        h = await self.enrich(registry_with(runs, stats_for(["2026-07-01", "2026-09-01"]),
                                            second_stats=stats_for(["2026-06-01", "2026-07-01", "2026-09-01"], "other_totals")))
        self.assertTrue(h["careerStartEvidence"]["conflict"])
        self.assertIsNone(h["_careerHistoryAudit"]["reportedStarts"])
        self.assertEqual(build_career_analysis(h, RACE)["acquisition_status"], "unverified")

    async def test_evidence_outage_is_unverified_and_retried(self):
        h = await self.enrich(registry_with([run(9, 1)], evidence_error=True))
        audit = h["_careerHistoryAudit"]
        self.assertEqual(audit["failedProviders"], [])
        self.assertEqual(audit["failedEvidenceProviders"], ["netkeiba_career_totals"])
        self.assertEqual(build_career_analysis(h, RACE)["acquisition_status"], "unverified")

    async def test_stats_for_other_race_date_ignored(self):
        other = dict(stats_for(["2026-09-01"]), asOfRaceDate="2026-09-30")
        h = await self.enrich(registry_with([run(9, 1)], other))
        self.assertNotIn("careerStartEvidence", h)
        self.assertEqual(h["_careerHistoryAudit"]["status"], "unverified")

    async def test_evidence_does_not_change_prediction_input_hash(self):
        from arvexq.pipeline.fingerprints import analysis_input_hash
        runs = [run(6, 1), run(7, 1), run(9, 1)]
        plain = await self.enrich(registry_with(runs))
        proven = await self.enrich(registry_with(runs, stats_for(["2026-06-01", "2026-07-01", "2026-09-01"])))
        def h(x):
            return analysis_input_hash({"id": "r", "date": "2026-10-10", "horses": [x]})
        self.assertEqual(h(plain), h(proven))

    def test_legacy_unbound_career_stats_ignored(self):
        h = {"allPastRuns": [run(9, 1)], "careerStats": {"starts": 1}}
        self.assertIsNone(audit_career(h, "2026-10-10", 1000, ["x"])["reportedStarts"])


class WiringTests(unittest.TestCase):
    def test_adapter_only_runs_in_career_lane(self):
        from arvexq.databanks.legacy_bridge import _netkeiba_career_totals_adapter
        calls = []
        def getter(url, timeout, cache):
            calls.append(url)
            return horse_page("2022100001") if "pid=horse_list" in url else (
                listing_html(ROWS) if "/result/" in url else top_html(4))
        fetch = _netkeiba_career_totals_adapter({"_netkeiba_get": getter})
        self.assertEqual(fetch({"name": "テスト"}, RACE, 5), {})
        self.assertEqual(calls, [])
        self.assertEqual(fetch({"name": "テスト"}, RACE, 1000)["careerStartEvidence"]["starts"], 3)

    def test_adapter_can_be_disabled(self):
        import os
        from arvexq.databanks.legacy_bridge import _netkeiba_career_totals_adapter
        os.environ["ARVEXQ_NETKEIBA_CAREER_TOTALS"] = "0"
        try:
            self.assertIsNone(_netkeiba_career_totals_adapter({"_netkeiba_get": lambda *a: ""}))
        finally:
            del os.environ["ARVEXQ_NETKEIBA_CAREER_TOTALS"]

    def test_ui_coverage_attached_and_consistent(self):
        from arvexq.prediction.race_intelligence import career_coverage
        h = {"horseNumber": 1, "allPastRuns": [run(9, 1)]}
        c = career_coverage(h, RACE)
        a = build_career_analysis(h, RACE)
        self.assertEqual(c["state"], a["career_state"])
        self.assertEqual(c["state"], "acquisition-unverified")
        self.assertEqual(c["eligibleRuns"], 1)


if __name__ == "__main__":
    unittest.main()
