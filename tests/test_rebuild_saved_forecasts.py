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
            again=rebuild(source,root/'out')
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
                self.assertTrue(publish(path,'https://test','token')['allPublished'])
                self.assertEqual(state['posts'],1)
                state['corrupt']=True
                failed=publish(path,'https://test','token')
                self.assertFalse(failed['allPublished']);self.assertEqual(len(failed['failures']),1)
