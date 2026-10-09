"""Career ingestion/ranking invariants on synthetic historical starts."""
from __future__ import annotations
import unittest
from arvexq.ingest.full_career import merge_career, audit_career
from arvexq.prediction.career_profile import profile_career
from arvexq.prediction.past_performance import observed_runs, analyze_past_performance
from arvexq.prediction.factor_model import collect_horse_raw_metrics
from arvexq.databanks.registry import DataBankRegistry,DataSource,SourceCapabilities
from arvexq.ingest.fallback_enrichment import enrich_race_missing

RACE={"date":"2026-10-10","track":"大井","distance":1200,"surface":"ダート","condition":"良","circuit":"地方"}

def run(month, day, finish=2):
    return {"date":f"2026-{month:02d}-{day:02d}","track":"大井","raceNumber":2,
            "title":f"race {month}-{day}","distance":1200,"surface":"ダート",
            "condition":"良","finish":finish,"fieldSize":12,"cornerPositions":[2,2,2],
            "jockey":"騎手A","carriedWeight":56,"class":"C1"}

class CareerTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_fetch_recent_five_and_preoff(self):
        older=[run(6,1),run(6,12),run(6,23),run(7,1),run(7,12),
               run(7,23),run(8,1),run(8,12),run(9,1),run(9,20)]
        fresh=[run(9,20),run(10,10,1),run(10,11,1)]
        reg=DataBankRegistry()
        requested=[]
        def fetch(h,r,limit):
            requested.append(limit)
            return {"recentRaces":older[-5:],"allPastRuns":older+fresh}
        reg.register(DataSource(name="career_official_test",circuit="NAR",priority=1,
            capabilities=SourceCapabilities(horse_history=True),fetchers={"horse_history":fetch}))
        src={"horseNumber":1,"name":"sample","recentRaces":older[-5:]}
        detail={"date":"2026-10-10","circuit":"地方","horses":[src]}
        out=await enrich_race_missing(detail,bank_registry=reg,history_limit=1000)
        horse=out["horses"][0]
        self.assertEqual(requested,[1000])
        self.assertEqual(len(horse["allPastRuns"]),10)
        self.assertEqual(len(horse["recentRaces"]),5)
        self.assertNotIn("2026-10-10",[r["date"] for r in horse["allPastRuns"]])
        self.assertNotIn("2026-10-11",[r["date"] for r in horse["allPastRuns"]])
        self.assertEqual(horse["_careerHistoryAudit"]["status"],"unverified")
        self.assertFalse(horse["_careerHistoryAudit"]["complete"])
        self.assertEqual(len(observed_runs(horse,RACE,limit=None)),10)
        self.assertEqual(len(observed_runs(horse,RACE)),5)
        career=profile_career(horse,RACE)
        self.assertEqual(career["datedRuns"],10)
        self.assertEqual(career["comparableRuns"],10)
        self.assertEqual(career["recentRuns"],5)
        raw=collect_horse_raw_metrics(horse,RACE)
        self.assertEqual(raw["record_top3_rate"],1)
        self.assertEqual(analyze_past_performance(horse,RACE)["datedRuns"],5)
        self.assertEqual(len(src["recentRaces"]),5)
    async def test_no_dated_history_cannot_be_fabricated(self):
        source={"horseNumber":1,"name":"sample","recentRaces":[{"finish":1,"fieldSize":12}]}
        reg=DataBankRegistry()
        reg.register(DataSource(name="empty",circuit="NAR",priority=1,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history":lambda *_: {"allPastRuns":[run(10,11,1)]}}))
        out=await enrich_race_missing({"date":"2026-10-10","circuit":"地方","horses":[source]},
                                      bank_registry=reg,history_limit=1000)
        self.assertEqual(out["horses"][0].get("allPastRuns"),None)
        self.assertFalse(out["horses"][0]["_careerHistoryAudit"]["complete"])
        self.assertEqual(profile_career(out["horses"][0],RACE)["datedRuns"],0)
    async def test_prefetch_merge_preserves_all_career_when_diagnosis_is_thin(self):
        from scripts.arvexq_prefetch import _merge_detail
        prior=[run(6,1),run(6,12),run(6,23),run(7,1),
               run(7,12),run(7,23),run(8,1),run(8,12)]
        a={"date":"2026-10-10","id":"example","horses":[{
            "horseNumber":1,"name":"sample",
            "allPastRuns":prior,"recentRaces":prior[-5:]}]}
        b={"date":"2026-10-10","id":"example","horses":[{
            "horseNumber":1,"name":"sample","allPastRuns":prior[-5:],
            "recentRaces":prior[-5:],"integratedEvaluation":{"mark":"○"}}]}
        merged=_merge_detail(a,b)
        self.assertEqual(len(merged["horses"][0]["allPastRuns"]),8)
        self.assertEqual(len(merged["horses"][0]["recentRaces"]),5)
        self.assertEqual(merged["horses"][0]["integratedEvaluation"]["mark"],"○")

    async def test_history_repair_richer_roster_does_not_erase_career(self):
        from scripts.arvexq_history_repair import merge_history
        from unittest.mock import patch
        old={"id":"example","date":"2026-10-10","horses":[{
            "horseNumber":1,"name":"sample","allPastRuns":[run(6,1),run(6,12),run(7,1)],
            "recentRaces":[run(7,1)]}]}
        fresh={"id":"example","date":"2026-10-10","horses":[{
            "horseNumber":1,"name":"sample","recentRaces":[run(7,1)]}]}
        with patch("scripts.arvexq_history_repair.card_score", side_effect=[2,1]):
            merged=merge_history(old,fresh)
        self.assertEqual(len(merged["horses"][0]["allPastRuns"]),3)

    async def test_failed_full_fetch_retries_even_when_recent_five_look_complete(self):
        reg=DataBankRegistry()
        attempts=[]
        def flaky(h,r,limit):
            attempts.append(limit)
            if len(attempts)==1:
                raise RuntimeError("transient partner outage")
            return {"allPastRuns":[run(8,1),run(8,12),run(8,20)]}
        reg.register(DataSource(name="flaky",circuit="NAR",priority=1,
            capabilities=SourceCapabilities(horse_history=True),fetchers={"horse_history":flaky}))
        h={"horseNumber":1,"name":"sample","recentRaces":[run(9,x) for x in (1,7,12,18,24)]}
        info={"date":"2026-10-10","circuit":"地方","horses":[h]}
        first=await enrich_race_missing(info,bank_registry=reg,history_limit=1000)
        self.assertEqual(first["horses"][0]["_careerHistoryAudit"]["failedProviders"],["flaky"])
        second=await enrich_race_missing(first,bank_registry=reg,history_limit=1000)
        self.assertEqual(attempts,[1000,1000])
        self.assertEqual(len(second["horses"][0]["allPastRuns"]),8)
        self.assertEqual(second["horses"][0]["_careerHistoryAudit"]["failedProviders"],[])

    async def test_reported_missing_is_explicit(self):
        horse={"allPastRuns":[run(9,20),run(9,1)],
               "careerStats":{"starts":12}}
        audit=audit_career(horse,"2026-10-10",1000,["test"])
        self.assertEqual(audit["unobservedMinimum"],10)
        self.assertEqual(audit["status"],"incomplete")
        self.assertFalse(audit["complete"])
    async def test_older_success_changes_career_not_recent(self):
        recent=[run(9,25,8),run(9,20,7),run(9,15,9),run(9,10,8),run(9,5,8)]
        old=[run(6,day,1) for day in (1,5,10,15,20)]
        a={"recentRaces":recent}
        b={"recentRaces":recent,"allPastRuns":old+recent}
        self.assertEqual(analyze_past_performance(a,RACE)["top3"],analyze_past_performance(b,RACE)["top3"])
        self.assertGreater(profile_career(b,RACE)["top3Rate"],profile_career(a,RACE)["top3Rate"])
        self.assertGreater(collect_horse_raw_metrics(b,RACE)["record_top3_rate"],
                           collect_horse_raw_metrics(a,RACE)["record_top3_rate"])

if __name__=="__main__":
    unittest.main()
