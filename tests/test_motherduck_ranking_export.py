"""Guardrails for streaming the already archived, verified features."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.export_motherduck_frozen_ranking import export, transform_item


def snapshot(race_id='nar-2026-10-24-名古屋-01', *, verified=True):
    return {'id': race_id, 'date': '2026-10-24', 'circuit': '地方',
            'track': '名古屋', 'result': {'status': '確定', 'finishers': [{'horseNumber': 1, 'finish': 1}]},
            'massFeatureArchive': {'originHashVerified': verified,
                                   'originStatus': 'verified' if verified else 'legacy-unverified-not-for-training'},
            '_test_rows': [{'raceId': race_id, 'featureHash': race_id, 'circuit': '地方',
                            'horseNumber': 1, 'finish': 1, 'labelWin': 1,
                            'features': {'static::age': 4.0}}]}


class StreamArchiveSafety(unittest.TestCase):
    def test_rejects_invalid_identity_and_archive(self):
        detail = snapshot()
        self.assertEqual(transform_item('wrong-race', json.dumps(detail))[1], 'identity-mismatch')
        self.assertEqual(transform_item(detail['id'], json.dumps(snapshot(verified=False)))[1], 'unverified-archive')
        self.assertEqual(transform_item(detail['id'], '{')[1], 'invalid-json')

    def test_partial_results_do_not_shrink_frozen_query(self):
        detail = snapshot()
        detail['massFeatureArchive']['horseCount'] = 2
        with patch('scripts.export_motherduck_frozen_ranking.frozen_training_rows_from_detail',
                   return_value=detail['_test_rows']):
            self.assertEqual(transform_item(detail['id'],detail)[1], 'incomplete-frozen-roster')

    def test_banei_never_exported(self):
        detail = snapshot('nar-2026-10-24-帯広-01')
        self.assertEqual(transform_item(detail['id'], json.dumps(detail))[1], 'banei-excluded')

    def test_streams_and_deduplicates_race_hashes(self):
        detail = snapshot()
        class Cursor:
            def __init__(self):
                self.data = [(detail['id'], json.dumps(detail)),
                             (detail['id'], json.dumps(detail))]
            def fetchmany(self, n):
                if not self.data: return []
                result, self.data = self.data[:n], self.data[n:]
                return result
        with tempfile.TemporaryDirectory() as tmp:
            outfile = Path(tmp) / 'frozen.jsonl'
            with patch('scripts.export_motherduck_frozen_ranking.frozen_training_rows_from_detail',
                       side_effect=lambda d: d['_test_rows']):
                report = export(Cursor(), outfile)
            self.assertEqual(report['counts']['exported-races'], 1)
            self.assertEqual(report['counts']['missing-or-repeated-hash'], 1)
            self.assertEqual(len(outfile.read_text().splitlines()), 1)
            self.assertFalse(report['productionChanged'])


if __name__ == '__main__':
    unittest.main()
