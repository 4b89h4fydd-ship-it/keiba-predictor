import copy
from datetime import datetime
import sqlite3
import tempfile
import unittest

from rewrite.selection.market import observation, open_store, append_observation, digest, parse_nar_wide
from rewrite.selection.policy import evaluate, POLICY


def detail():
    return {"id":"nar-2026-11-11-川崎-01","date":"2026-11-11","raceNumber":1,
            "track":"川崎","startTime":"15:00","scheduledStartTime":"15:00",
            "horses":[{"horseNumber":n} for n in range(1,6)],
            "unifiedForecast":{"modelVersion":"arvexq-rewrite-v3-v9b","modelHash":"m",
              "capturedAt":"2026-11-11T14:35:00+09:00","receiptSha256":"r",
              "diagnosis":[{"horseNumber":n} for n in range(1,6)]}}


def market(d=None, quotes=None):
    return observation(d or detail(),quotes or [{"combo":[1,2],"oddsLow":2.0,"oddsHigh":2.5}],
      kind="wide",observed_at="2026-11-11T14:40:00+09:00",fetched_at="2026-11-11T14:40:10+09:00",
      source="NAR公式ワイド",source_url="https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsWide",
      source_body_sha256="a"*64)


class MarketPolicyTest(unittest.TestCase):
    def test_record_keeps_old_source_time(self):
        r=market();self.assertNotEqual(r["observedAt"],r["fetchedAt"])

    def test_no_retroactive_market(self):
        with self.assertRaisesRegex(ValueError,"preoff"):
            observation(detail(),[],kind="wide",observed_at="2026-11-11T15:01:00+09:00",
                        fetched_at="2026-11-11T15:01:01+09:00",source="x",source_url="x",source_body_sha256="a"*64)

    def test_predicted_duplicate_unknown_and_nan_quotes_refused(self):
        for q in ([{"combo":[1,6],"oddsLow":2}],
                  [{"combo":[1,2],"oddsLow":float('nan')}],
                  [{"combo":[1,2],"oddsLow":2,"forecast":True}],
                  [{"combo":[1,2],"oddsLow":2},{"combo":[2,1],"oddsLow":2}]):
            with self.subTest(q=q),self.assertRaises(ValueError): market(quotes=q)

    def test_append_only_and_idempotent(self):
        with tempfile.NamedTemporaryFile() as f:
            db=open_store(f.name);r=market();append_observation(db,r);append_observation(db,r)
            self.assertEqual(db.execute('select count(*) from market_observations').fetchone()[0],1)
            for sql in ('delete from market_observations','update market_observations set kind="win"'):
                with self.assertRaises(sqlite3.IntegrityError):db.execute(sql)
            tampered=copy.deepcopy(r);tampered['quotes'][0]['oddsLow']=900
            with self.assertRaisesRegex(ValueError,'hash'):append_observation(db,tampered)
            db.close()

    def test_official_wide_parser_does_not_parse_payouts(self):
        html='<table><tr><th>組合せ</th><th>オッズ</th><th>人気</th></tr><tr><td>2-8</td><td>1.3 -1.6</td><td>1</td></tr><tr><td>2-8</td><td>330円</td><td>2人気</td></tr></table>'
        self.assertEqual(parse_nar_wide(html),[{'combo':[2,8],'oddsLow':1.3,'oddsHigh':1.6}])

    def approved(self):
        return {'status':'approved-out-of-sample','modelHash':'m','policySha256':digest(POLICY),
                'validatedThrough':'2026-11-10','evidenceSha256':'test-fixture-only'}

    def test_unvalidated_policy_never_selects_even_with_profitable_quotes(self):
        r=evaluate(detail(),market(),outcomes={(1,2,3):1},decided_at='2026-11-11T14:41:00+09:00')
        self.assertFalse(r['selected']);self.assertIn('ticket-probability-and-policy-unvalidated',r['reasons'])

    def test_union_probability_not_sum_and_no_quota(self):
        m=market(quotes=[{'combo':[1,2],'oddsLow':10},{'combo':[1,3],'oddsLow':10}])
        r=evaluate(detail(),m,outcomes={(1,2,3):.6,(3,4,5):.4},validation=self.approved(),
                   decided_at='2026-11-11T14:41:00+09:00')
        self.assertFalse(r['selected'],'overlapping .6/.6 tickets cover .6, not 1.2')

    def test_qualified_exact_ticket_not_rank_rule(self):
        r=evaluate(detail(),market(),outcomes={(1,2,3):.8,(3,4,5):.2},validation=self.approved(),
                   decided_at='2026-11-11T14:41:00+09:00')
        self.assertTrue(r['selected']);self.assertEqual(r['items'][0]['combo'],[1,2])

    def test_stale_market_old_forecast_same_day_validation_and_roster_changes(self):
        for change in ['market','forecast','validation','roster','receipt']:
            d,m,v=detail(),market(),self.approved()
            if change=='market':at='2026-11-11T14:51:00+09:00'
            else:at='2026-11-11T14:41:00+09:00'
            if change=='forecast':d['unifiedForecast']['capturedAt']='2026-11-11T10:00:00+09:00'
            if change=='validation':v['validatedThrough']='2026-11-11'
            if change=='roster':d['unifiedForecast']['diagnosis'].pop()
            if change=='receipt':d['unifiedForecast']['receiptSha256']='other'
            with self.subTest(change=change):
                self.assertFalse(evaluate(d,m,outcomes={(1,2,3):1},validation=v,decided_at=at)['selected'])


if __name__=='__main__':unittest.main()
