import base64
import gzip
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.arvexq_publish_saved_snapshots import publish


class RecoveryTest(unittest.TestCase):
    def test_originals_and_all_career_restore_without_database_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'cache'
            root.mkdir()
            db = root / 'prepared.sqlite3'
            d = {'id': 'race1', 'date': '2026-10-10', 'fieldSize': 2,
                 'horses': [{'horseNumber': n, 'name': str(n), 'allPastRuns': [{'date': '2025-01-01'}]*25} for n in [1, 2]],
                 'morningMarkSnapshot': {'fixedAt': '2026-10-09T21:00:00Z', 'horses': [{'mark': '◎'}]},
                 'preRaceBet': {'items': [{'kind': 'ワイド', 'combos': [[1, 2]]}]},
                 'result': {'status': '確定'}, 'internalFeature': 'keep'}
            raw = json.dumps(d, ensure_ascii=False)
            with sqlite3.connect(db) as c:
                c.execute('CREATE TABLE prepared_races(race_id,race_date,updated_at,payload)')
                c.execute('INSERT INTO prepared_races VALUES(?,?,?,?)', ('race1', d['date'], 1, raw))
            before = db.read_bytes()
            dest = Path(tmp) / 'static'
            report = publish(root, dest, d['date'])
            self.assertEqual(report['added'], 1)
            self.assertEqual(db.read_bytes(), before)
            manifest = json.loads((dest / (d['date']+'.json')).read_text())
            e = json.loads((dest / manifest['races']['race1']['file']).read_text())
            restored = gzip.decompress(base64.b64decode(e['gzipBase64']))
            self.assertEqual(restored.decode(), raw)
            self.assertEqual(hashlib.sha256(restored).hexdigest(), e['sha256'])
            manifest_original = (dest / (d['date']+'.json')).read_bytes()
            with sqlite3.connect(db) as c:
                c.execute('UPDATE prepared_races SET payload=?', (json.dumps({**d, 'preRaceBet': {'items': []}}),))
            self.assertEqual(publish(root, dest, d['date'])['added'], 0)
            self.assertEqual((dest / (d['date']+'.json')).read_bytes(), manifest_original)


if __name__ == '__main__':
    unittest.main()
