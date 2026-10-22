import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.arvexq_resume_forecast_inputs import prepare, signature


class ResumeInputsTests(unittest.TestCase):
    def test_result_refresh_does_not_change_target_inputs_but_scratch_does(self):
        original = json.loads((Path(__file__).parent / 'fixtures/forecast_revision_transport.json').read_text())['detail']
        current = copy.deepcopy(original)
        current['result'] = {'status': '確定'}
        self.assertEqual(signature(json.dumps(original)), signature(json.dumps(current)))
        current['horses'][0]['scratched'] = True
        self.assertNotEqual(signature(json.dumps(original)), signature(json.dumps(current)))

    def test_changed_historical_input_refreshes_later_family_and_preserves_original_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = json.loads((Path(__file__).parent / 'fixtures/forecast_revision_transport.json').read_text())['detail']
            def race(rid, day, circuit='地方'):
                d = copy.deepcopy(fixture)
                d.update(id=rid, date=day, circuit=circuit)
                return d
            old = [race('old', '2026-10-12'), race('dependent', '2026-10-13'), race('central', '2026-10-13', '中央')]
            current = copy.deepcopy(old) + [race('added', '2026-10-14')]
            current[0]['horses'][0]['carriedWeight'] = 44
            for path, values in ((root / 'old.db', old), (root / 'current.db', current)):
                with sqlite3.connect(path) as db:
                    db.execute('CREATE TABLE race_details(race_id TEXT,payload TEXT)')
                    db.executemany('INSERT INTO race_details VALUES(?,?)', [(r['id'], json.dumps(r)) for r in values])
            with sqlite3.connect(root / 'revisions.sqlite3') as db:
                db.execute('CREATE TABLE revisions(race_id TEXT)')
                db.executemany('INSERT INTO revisions VALUES(?)', [(r['id'],) for r in old])
            data = b'original verified archive'
            with zipfile.ZipFile(root / 'official-nar-inputs.zip', 'w') as archive:
                archive.writestr('202610_race.zip', data)
            (root / 'rebuild-summary.json').write_text(json.dumps({'trainingLimit': 60,
                'officialNarArchiveSha256': {'/original/202610_race.zip': hashlib.sha256(data).hexdigest()}}))
            with patch('scripts.arvexq_resume_forecast_inputs.rebuild', return_value={'allSavedRebuilt': True, 'errors': [], 'revisions': 4}) as build:
                report = prepare(root / 'old.db', root / 'current.db', root)
            self.assertEqual(set(report['recalculatedRaceIds']), {'old', 'dependent', 'added'})
            self.assertTrue(build.call_args.kwargs['only_missing'])
            with sqlite3.connect(root / 'revisions-original.sqlite3') as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0], 3)
            with sqlite3.connect(root / 'revisions.sqlite3') as db:
                self.assertEqual(db.execute('SELECT race_id FROM revisions').fetchall(), [('central',)])
