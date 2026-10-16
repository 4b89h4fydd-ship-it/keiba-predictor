"""Cross-runtime prediction checks and independent ticket event calculations."""
import copy
import itertools
import json
import math
import subprocess
import unittest
from tests.test_unified_jra_nar_observed_authority import race
from arvexq.ingest.career_transport import pack_horse
from arvexq.prediction.observed_model import apply_observed_marks, rank_observed

class BrowserParityTests(unittest.TestCase):
    def replay(self, details):
        result = subprocess.run(['node','scripts/arvexq_observed_replay.js'],
                                input=json.dumps(details),text=True,capture_output=True,check=True)
        return json.loads(result.stdout)

    def test_full_career_and_archive_scopes_match_browser(self):
        details=[]
        for circuit in ('中央','地方'):
            d=race(circuit)
            for h in d['horses']:
                # Older valid starts must contribute to rates, never to the five-run form window.
                h['allPastRuns']=copy.deepcopy(h['recentRaces'])+[
                    dict(h['recentRaces'][0], date='2026-08-01',finish=8)]
                h.update(pack_horse(h,d['date']))
            details.append(d)
        for d, js in zip(details,self.replay(details)):
            py={r['horse']['horseNumber']:r for r in rank_observed(d['horses'],d)}
            apply_observed_marks(d)
            marks={h['horseNumber']:h['integratedEvaluation']['mark'] for h in d['horses']}
            for row in js['rows']:
                self.assertAlmostEqual(row['score'],py[row['no']]['score'])
                self.assertEqual(row['rates']['starts'],6)
                self.assertEqual(row['mark'],marks[row['no']])

    def test_career_rates_never_replace_missing_position(self):
        d=race('地方')
        for q in d['horses'][0]['recentRaces']:
            q['cornerPositions']=[]
        js=self.replay([d])[0]
        row=next(z for z in js['rows'] if z['no']==1)
        self.assertIsNone(row['score'])
        self.assertEqual(row['mark'],'')
        self.assertFalse(js['plan']['items'])

    def test_ten_tickets_are_unique_highest_joint_probability_events(self):
        d=race('地方')
        for h in d['horses']:
            for q in h['recentRaces']:
                q['marginSeconds']=0 if h['horseNumber']==1 else 2
                q['finish']=1 if h['horseNumber']==1 else min(12,h['horseNumber']+2)
        js=self.replay([d])[0]
        plan=js['plan']
        tri=next(x for x in plan['items'] if x['kind']=='3連単')
        combos=[tuple(c) for c in tri['combos']]
        self.assertEqual(len(combos),10)
        self.assertEqual(len(set(combos)),10)
        rows=js['rows'];peak=max(z['score'] for z in rows)
        w={z['no']:math.exp((z['score']-peak)/.15) for z in rows};total=sum(w.values())
        def probability(t):
            a,b,c=t
            return w[a]/total*w[b]/(total-w[a])*w[c]/(total-w[a]-w[b])
        included=[probability(c) for c in combos]
        omitted=[probability(c) for c in itertools.permutations(w,3) if c not in combos]
        self.assertGreaterEqual(min(included)+1e-12,max(omitted))
        for c,p in zip(combos,tri['comboProbabilities']):
            self.assertAlmostEqual(p,probability(c)*100,delta=.0051)
        self.assertLessEqual(plan['trifectaOccurrenceProbability'],100)

    def test_current_tickets_cannot_fall_back_to_old_original(self):
        d=race('地方');d['date']='2099-01-10';d['startTime']='23:00';d['id']='nar-2099-01-10-園田-01'
        d['preRaceBet']={'raceId':d['id'],'raceDate':d['date'],'fixedAt':'2099-01-10T00:00:00+09:00',
                         'items':[{'kind':'単勝','combos':[[99]]}],'engineVersion':'retired-engine'}
        js=self.replay([d])[0]
        self.assertNotEqual(js['plan']['engineVersion'],'retired-engine')
        self.assertNotIn(99,[no for item in js['plan']['items'] for combo in item['combos'] for no in combo])
