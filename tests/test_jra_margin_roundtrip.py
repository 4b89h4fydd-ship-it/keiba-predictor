import asyncio
import base64
import copy
import unittest
from unittest.mock import Mock
from arvexq.databanks.legacy_bridge import _jra_official_prior_result_adapter
from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities
from arvexq.ingest.career_transport import pack_horse, recover_horse
from arvexq.ingest.fallback_enrichment import enrich_race_missing

class JraMarginRoundtrip(unittest.TestCase):
    def test_all_five_runs_including_zero_and_normal_limit(self):
        runs=[{'date':f'2026-09-{i:02d}','track':'東京','finish':1 if i==1 else 2,
               'raceId':'jraresult-'+base64.urlsafe_b64encode(str(i).encode()).decode().rstrip('='),
               'fieldSize':10,'cornerPositions':[3,2]} for i in range(1,6)]
        def result(cname, base):
            return {**base,'raceNumber':1,'resultCname':cname,'result':{'finishers':[
                {'name':'対象馬' if cname=='1' else '勝馬','finish':1,'timeSeconds':95.1},
                {'name':'別馬' if cname=='1' else '対象馬','finish':2,'timeSeconds':95.5}]}}
        fetch=_jra_official_prior_result_adapter({'_jra_parse_result':result})
        out=fetch({'name':'対象馬','recentRaces':runs},{'date':'2026-10-12'},5)
        self.assertEqual(len(out['allPastRuns']),5)
        self.assertEqual(out['allPastRuns'][-1]['timeBehindWinner'],0.0)
        for row in out['allPastRuns']:
            e=row['marginEvidence']
            self.assertAlmostEqual(e['horseTimeSeconds']-e['winnerTimeSeconds'],row['timeBehindWinner'])

    def test_missing_links_resolved_and_mismatching_start_rejected(self):
        result={'date':'2026-09-01','track':'東京','distance':1600,'raceNumber':2,
                'resultCname':'official','result':{'finishers':[
                    {'name':'勝馬','finish':1,'timeSeconds':95.1},
                    {'name':'対象馬','finish':2,'timeSeconds':95.5}]}}
        resolve=Mock(return_value=result)
        fetch=_jra_official_prior_result_adapter({'_jra_parse_result':Mock(),
                                                   '_jra_resolve_prior_results':resolve})
        horse={'name':'対象馬','recentRaces':[{'date':'2026-09-01','track':'東京',
                      'distance':1600,'finish':2,'timeSeconds':95.5}]}
        self.assertEqual(fetch(horse,{'date':'2026-10-12'},5)['recentRaces'][0]['timeBehindWinner'],.4)
        for key,value in [('date','2026-10-13'),('track','阪神'),('distance',2000),('finish',3),('timeSeconds',96.5)]:
            bad=copy.deepcopy(horse);bad['recentRaces'][0][key]=value
            self.assertEqual(fetch(bad,{'date':'2026-10-12'},5),{})

    def test_complete_corner_history_still_requeries_missing_margins_jra_only(self):
        row={'date':'2026-09-01','finish':2,'fieldSize':10,'cornerPositions':[3,2]}
        rows=[{**row,'date':f'2026-09-{i:02d}'} for i in range(1,6)]
        get=Mock(return_value={'recentRaces':[{**r,'timeBehindWinner':0.0} for r in rows]})
        reg=DataBankRegistry();reg.register(DataSource(name='jra_official_prior_results',circuit='JRA',priority=1,
             capabilities=SourceCapabilities(horse_history=True),fetchers={'horse_history':get}))
        d={'date':'2026-10-12','circuit':'JRA','horses':[{'name':'対象馬','recentRaces':rows,
                   'pedigree':{'sire':'父'},'jockeyStats':{'n':1},'trainerStats':{'n':1}}]}
        out=asyncio.run(enrich_race_missing(d,bank_registry=reg))
        get.assert_called_once();self.assertEqual(out['horses'][0]['recentRaces'][0]['timeBehindWinner'],0)
        get.reset_mock();d['circuit']='NAR';asyncio.run(enrich_race_missing(d,bank_registry=reg));get.assert_not_called()

    def test_d1_visible_rows_and_lossless_archive_keep_seconds_and_proof(self):
        run={'date':'2026-09-01','track':'東京','finish':1,'fieldSize':10,
             'timeBehindWinner':0.0,'marginText':'','marginEvidenceSource':'JRA official',
             'marginEvidence':{'horseName':'対象馬','winnerTimeSeconds':95.1,'horseTimeSeconds':95.1}}
        h=pack_horse({'recentRaces':[run]},'2026-10-12')
        self.assertEqual(h['recentRaces'][0]['timeBehindWinner'],0.0)
        self.assertEqual(h['recentRaces'][0]['marginEvidence'],run['marginEvidence'])
        self.assertEqual(recover_horse(h,'2026-10-12')['allPastRuns'][0]['timeBehindWinner'],0.0)

if __name__=='__main__':unittest.main()
