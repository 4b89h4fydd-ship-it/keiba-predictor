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
