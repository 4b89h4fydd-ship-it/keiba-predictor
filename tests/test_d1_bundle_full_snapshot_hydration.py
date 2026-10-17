"""D1 readback must restore the complete verified race snapshot."""
import unittest
from arvexq.ingest.full_snapshot_codec import pack_detail
from scripts.arvexq_fetch_d1_bundle import detail_from_response


class D1HydrationTests(unittest.TestCase):
    def test_restores_complete_career_from_full_envelope(self):
        detail = {'id': 'nar-test-01', 'date': '2026-10-17', 'horses': [
            {'horseNumber': 1, 'name': 'A', 'allPastRuns': [
                {'date': '2026-10-01', 'track': '園田', 'finish': 1},
                {'date': '2026-09-01', 'track': '園田', 'finish': 2},
            ]},
        ]}
        packed = pack_detail(detail)
        restored = detail_from_response({'detail': packed}, detail['id'])
        self.assertEqual(restored, detail)
        self.assertEqual(len(restored['horses'][0]['allPastRuns']), 2)

    def test_rejects_corrupted_archive(self):
        packed = pack_detail({'id': 'nar-test-02', 'horses': []})
        packed['arvexqFullPayload']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            detail_from_response({'detail': packed}, 'nar-test-02')

    def test_rejects_internal_identity_change(self):
        packed = pack_detail({'id': 'wrong', 'horses': []})
        packed['id'] = 'expected'
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            detail_from_response({'detail': packed}, 'expected')


if __name__ == '__main__':
    unittest.main()
