import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from rewrite.safety.contracts import Observation, Runner, RaceCard, Segment
from rewrite.safety.ledger import Ledger

NOW = datetime(2026, 10, 27, 10, tzinfo=timezone.utc)


def card():
    evidence = (Observation('official', NOW, NOW, 1.0),)
    return RaceCard('race1', '東京', Segment.JRA_FLAT, NOW + timedelta(hours=1), NOW,
                    2, (Runner('h1', 1, '馬一', False, evidence),
                        Runner('h2', 2, '馬二', False, evidence)))


class SafetyTests(unittest.TestCase):
    def test_complete_card(self):
        card().validate()

    def test_incomplete_and_duplicate_fields(self):
        c = card()
        for bad in (replace(c, declared_count=3), replace(c, runners=(c.runners[0],)*2),
                    replace(c, runners=(replace(c.runners[0], evidence=()), c.runners[1]))):
            with self.assertRaises(ValueError):
                bad.validate()

    def test_excluded_venue(self):
        for venue in ('帯広', '帯広ば', '帯広ばんえい', 'Obihiro', 'banei'):
            with self.assertRaises(ValueError):
                replace(card(), venue=venue).validate()

    def test_future_and_missing_provenance(self):
        for o in (Observation('official', NOW, NOW+timedelta(seconds=1), 1),
                  Observation('', NOW, NOW, 1), Observation('official', NOW, NOW, None),
                  Observation('official', NOW, NOW, float('nan'))):
            with self.assertRaises(ValueError):
                o.validate(NOW)
        Observation('official', NOW, NOW, None, 'not published').validate(NOW)

    def test_naive_or_post_start(self):
        for c in (replace(card(), cutoff=NOW.replace(tzinfo=None)),
                  replace(card(), starts_at=NOW)):
            with self.assertRaises(ValueError):
                c.validate()

    def test_immutable_roundtrip_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/'originals.db')
            payload = {'race_id': 'race1', 'horses': ['馬一', '馬二']}
            ledger.seal('race1', NOW, card().starts_at, payload)
            self.assertEqual(ledger.read('race1'), payload)
            with self.assertRaises(sqlite3.IntegrityError):
                ledger.seal('race1', NOW, card().starts_at, {'race_id':'race1'})
            for sql in ('DELETE FROM originals', "UPDATE originals SET sha256='bad'"):
                with self.assertRaises(sqlite3.IntegrityError):
                    with ledger.connection:
                        ledger.connection.execute(sql)
            report = ledger.backup(Path(directory)/'backup.db')
            self.assertTrue(report['restore_verified'])
            self.assertEqual(report['rows'], 1)
            with self.assertRaises(FileExistsError):
                ledger.backup(Path(directory)/'backup.db')
            ledger.close()

    def test_late_or_mixed_race_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/'originals.db')
            with self.assertRaises(ValueError):
                ledger.seal('race1', NOW, NOW, {'race_id':'race1'})
            with self.assertRaises(ValueError):
                ledger.seal('race1', NOW, card().starts_at, {'race_id':'race2'})
            ledger.close()


if __name__ == '__main__':
    unittest.main()
