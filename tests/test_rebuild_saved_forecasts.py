from pathlib import Path
import json
import sqlite3
import tempfile
from unittest import TestCase
from arvexq.prediction.forecast_revisions import latest_revision
from scripts.arvexq_rebuild_saved_forecasts import rebuild
from test_learned_scenarios import training_race,target

class SavedForecastRebuildTests(TestCase):
    def test_all_saved_dates_resumption_and_strict_training_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.sqlite3'
            rows=[training_race('地方'),target('地方')]
            with sqlite3.connect(source) as db:
                db.execute('CREATE TABLE race_details(race_id TEXT,race_date TEXT,payload TEXT)')
                db.executemany('INSERT INTO race_details VALUES(?,?,?)',[(r['id'],r['date'],json.dumps(r)) for r in rows])
            report=rebuild(source,root/'out')
            self.assertTrue(report['allSavedRebuilt']);self.assertEqual(report['revisions'],2)
            with sqlite3.connect(root/'out/revisions.sqlite3') as db:
                first=db.execute('SELECT race_id,payload_json FROM revisions ORDER BY race_id').fetchall()
            again=rebuild(source,root/'out',only_missing=True)
            with sqlite3.connect(root/'out/revisions.sqlite3') as db:
                self.assertEqual(first,db.execute('SELECT race_id,payload_json FROM revisions ORDER BY race_id').fetchall())
            self.assertTrue(again['allSavedRebuilt'])
            for rid,raw in first:
                revision=json.loads(raw)
                self.assertFalse(revision['productionEligible'])
                self.assertTrue(latest_revision({'id':rid,'date':revision['raceDate'],'forecastRevisions':[revision],'currentForecastRevisionId':revision['revisionId']}))

    def test_publish_verifies_reload_and_resumes_without_rewriting(self):
        from io import BytesIO
        from unittest.mock import patch
        from hashlib import sha256
        from scripts.arvexq_rebuild_saved_forecasts import publish
        fixture=json.loads((Path(__file__).parent/'fixtures/forecast_revision_transport.json').read_text())['detail']
        revision=fixture['forecastRevisions'][0];raw=json.dumps(revision,ensure_ascii=False,separators=(',',':'))
        state={'revision':None,'posts':0,'corrupt':False}
        def transport(request,timeout):
            if request.data:
                body=json.loads(request.data);state['posts']+=1
                self.assertEqual(body['payloadSha256'],sha256(body['revisionRawJson'].encode()).hexdigest())
                state['revision']=json.loads(body['revisionRawJson'])
                result={'ok':True,'original_tables_modified':False}
            else:
                stored=state['revision'];pointer=stored['revisionId'] if stored else None
                if state['corrupt']:pointer='wrong'
                result={'ok':True,'forecastRevisions':[stored] if stored else [],'currentForecastRevisionId':pointer}
            return BytesIO(json.dumps(result).encode())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE revisions(race_id TEXT,revision_id TEXT,payload_json TEXT,payload_sha256 TEXT)')
                db.execute('INSERT INTO revisions VALUES(?,?,?,?)',(revision['raceId'],revision['revisionId'],raw,sha256(raw.encode()).hexdigest()))
            with patch('urllib.request.urlopen',side_effect=transport):
                self.assertTrue(publish(path,'https://test','token')['allPublished'])
                self.assertTrue(publish(path,'https://test','token',only_ids={revision['raceId']})['allPublished'])
                self.assertFalse(publish(path,'https://test','token',only_ids={'absent'})['allPublished'])
                self.assertEqual(state['posts'],1)
                state['corrupt']=True
                failed=publish(path,'https://test','token')
                self.assertFalse(failed['allPublished']);self.assertEqual(len(failed['failures']),1)

    def test_official_archive_repairs_missing_history_without_future_or_namesake(self):
        import zipfile
        from copy import deepcopy
        from test_nar_official_csv import encode,race,horse
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        from scripts.arvexq_rebuild_saved_forecasts import enrich_official_history
        source={'id':'nar-2026-10-08-大井-04','date':'2026-10-08','track':'大井','raceNumber':4,'circuit':'地方',
                'preRacePrediction':{'original':'keep'},'horses':[{'horseNumber':10,'name':'サンプル','recentRaces':[]}]}
        original=deepcopy(source)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'official.zip'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('racelist.csv',encode([race('20260930'),race('20261008'),race('20261012')]))
                z.writestr('horselist.csv',encode([horse(),horse(dob='20200101',number=8),horse(date='20261008'),horse(date='20261012')]))
            repaired=enrich_official_history(source,NarOfficialArchive([path]))
        self.assertEqual(source,original)
        self.assertEqual(repaired['preRacePrediction'],original['preRacePrediction'])
        self.assertEqual(repaired['horses'][0]['birthDate'],'2018-03-10')
        self.assertEqual([r['date'] for r in repaired['horses'][0]['allPastRuns']],['2026-09-30'])

    def test_training_labels_and_each_history_are_strictly_earlier(self):
        import zipfile
        from test_nar_official_csv import encode,race,horse
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        from scripts.arvexq_rebuild_saved_forecasts import official_training_races
        races=[];horses=[]
        for day in ('20260925','20260930','20261008','20261012'):
            row=race(day);row[26]='3';races.append(row)
            for no in (1,2,3):
                entry=horse(name='馬'+str(no),number=no,date=day);entry[31]=str(no);horses.append(entry)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'official.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('racelist.csv',encode(races));z.writestr('horselist.csv',encode(horses))
            training=official_training_races(NarOfficialArchive([path]),'2026-10-08','flat',1)
        self.assertEqual(len(training),1);self.assertEqual(training[0]['date'],'2026-09-30')
        for h in training[0]['horses']:self.assertEqual([r['date'] for r in h['allPastRuns']],['2026-09-25'])
