"""Full-career acquisition is proven separately from field completeness."""
import unittest
from arvexq.horse_detail import build_horse_detail
from arvexq.diagnosis import diagnose_horse
from arvexq.ingest.full_career import audit_career
from arvexq.ingest.career_transport import pack_horse, recover_horse

RACE = {'date': '2026-02-01'}


def run(day, **kw):
    r = {'date': f'2025-12-{day:02d}', 'finish': 1, 'fieldSize': 10,
         'surface': 'ダート', 'condition': '良', 'distance': 1200}
    r.update(kw)
    return r


def audited(rows, starts, providers=('test',), failed=(), cutoff='2026-02-01'):
    h = {'allPastRuns': rows, 'recentRaces': rows[:5]}
    if starts is not None:
        h['careerStats'] = {'starts': starts, 'asOfRaceDate': cutoff}
    a = audit_career(h, cutoff, 1000, list(providers))
    a['fetchAttempted'] = True
    a['failedProviders'] = list(failed)
    h['_careerHistoryAudit'] = a
    return h


def ca(h, race=RACE):
    return build_horse_detail(h, race)['careerAnalysis']


class AcquisitionTests(unittest.TestCase):
    def test_recent_five_only_is_not_complete(self):
        a = ca({'recentRaces': [run(d) for d in range(1, 6)]})
        self.assertEqual(a['field_completeness'], 'complete')
        self.assertEqual(a['acquisition_status'], 'unverified')
        self.assertFalse(a['career_complete'])
        self.assertEqual(a['data_limitation'], 'partial')
        self.assertEqual(a['career_state'], 'acquisition-unverified')

    def test_all_past_runs_name_is_not_evidence(self):
        a = ca({'allPastRuns': [run(d) for d in range(1, 12)]})
        self.assertEqual(a['acquisition_status'], 'unverified')
        self.assertEqual(a['acquisition_evidence']['reason'], 'no-acquisition-evidence')

    def test_audit_without_reported_starts_is_unverified(self):
        a = ca(audited([run(d) for d in range(1, 8)], None))
        self.assertEqual(a['acquisition_status'], 'unverified')
        self.assertNotEqual(a['data_limitation'], 'complete')

    def test_failed_provider_without_total_is_partial(self):
        a = ca(audited([run(d) for d in range(1, 8)], None, failed=['flaky']))
        self.assertEqual(a['acquisition_status'], 'partial')
        self.assertEqual(a['career_state'], 'partially-acquired')

    def test_pagination_incomplete_is_partial(self):
        h = audited([run(d) for d in range(1, 8)], 7)
        h['_careerHistoryAudit']['paginationComplete'] = False
        self.assertEqual(ca(h)['acquisition_status'], 'partial')

    def test_fewer_than_reported_is_partial(self):
        a = ca(audited([run(d) for d in range(1, 8)], 12))
        self.assertEqual(a['acquisition_status'], 'partial')
        self.assertFalse(a['career_complete'])

    def test_more_than_reported_is_not_complete(self):
        h = audited([run(d) for d in range(1, 8)], 6)
        self.assertFalse(h['_careerHistoryAudit']['complete'])
        self.assertEqual(h['_careerHistoryAudit']['status'], 'count-mismatch')
        self.assertEqual(ca(h)['acquisition_status'], 'unverified')

    def test_stale_audit_after_rows_changed_is_not_complete(self):
        h = audited([run(d) for d in range(1, 8)], 7)
        h['allPastRuns'] = h['allPastRuns'] + [run(20)]
        self.assertNotEqual(ca(h)['acquisition_status'], 'complete')

    def test_audit_for_other_race_date_is_not_reused(self):
        h = audited([run(d) for d in range(1, 8)], 7, cutoff='2026-01-15')
        a = ca(h)
        self.assertEqual(a['acquisition_status'], 'unverified')
        self.assertEqual(a['acquisition_evidence']['reason'], 'audit-not-bound-to-this-race-date')

    def test_verified_complete_and_clean(self):
        a = ca(audited([run(d) for d in range(1, 8)], 7))
        self.assertEqual(a['acquisition_status'], 'complete')
        self.assertTrue(a['career_complete'])
        self.assertEqual(a['data_limitation'], 'complete')
        self.assertEqual(a['career_state'], 'complete')
        self.assertEqual(a['analyzed_runs'], 7)

    def test_verified_complete_with_missing_fields(self):
        rows = [run(d) for d in range(1, 7)] + [run(7, fieldSize=None)]
        a = ca(audited(rows, 7))
        self.assertEqual(a['acquisition_status'], 'complete')
        self.assertTrue(a['career_complete'])
        self.assertEqual(a['field_completeness'], 'missing-fields')
        self.assertEqual(a['data_limitation'], 'partial')
        self.assertEqual(a['career_state'], 'complete-with-missing-fields')
        self.assertIn('field_size', a['missing_fields'])

    def test_debut_with_zero_reported_starts(self):
        a = ca(audited([], 0))
        self.assertEqual(a['acquisition_status'], 'complete')
        self.assertEqual(a['career_state'], 'complete-no-starts')
        self.assertEqual(a['data_limitation'], 'no_runs')

    def test_no_history_without_evidence(self):
        a = ca({})
        self.assertEqual(a['career_state'], 'no-history')
        self.assertEqual(a['acquisition_status'], 'unverified')

    def test_history_present_but_unusable(self):
        a = ca({'recentRaces': [run(1, finish=None)]})
        self.assertEqual(a['career_state'], 'history-present-but-unusable')

    def test_future_same_day_undated_excluded_not_counted_as_gap(self):
        rows = [run(d) for d in range(1, 8)]
        h = audited(rows, 7)
        h['allPastRuns'] = rows + [run(1, date='2026-02-01'), run(1, date='2026-03-01'),
                                   run(1, date=None)]
        a = ca(h)
        self.assertEqual(a['analyzed_runs'], 7)
        self.assertEqual(a['excluded_not_pre_race_records'], 3)
        self.assertEqual(a['acquisition_status'], 'complete')

    def test_unknown_race_date_never_complete(self):
        a = ca(audited([run(d) for d in range(1, 8)], 7), {})
        self.assertEqual(a['acquisition_status'], 'race-date-unverified')
        self.assertEqual(a['career_state'], 'race-date-unverified')
        self.assertFalse(a['career_complete'])

    def test_duplicates_not_double_counted(self):
        rows = [run(d) for d in range(1, 8)]
        h = audited(rows, 7)
        h['pastRaces'] = [dict(r) for r in rows]
        h['history'] = [run(3, fieldSize=None)]  # same date as a valid start
        a = ca(h)
        self.assertEqual(a['eligible_dated_runs'], 7)
        self.assertEqual(a['analyzed_runs'], 7)
        self.assertEqual(a['unusable_dated_records'], 0)
        self.assertEqual(a['acquisition_status'], 'complete')

    def test_pack_and_recover_preserve_acquisition(self):
        h = audited([run(d) for d in range(1, 13)], 12)
        packed = pack_horse(h, RACE['date'])
        self.assertTrue(packed['careerTransport']['complete'])
        self.assertEqual(packed['_careerHistoryAudit'], h['_careerHistoryAudit'])
        restored = recover_horse(packed, RACE['date'])
        self.assertEqual(restored['_careerHistoryAudit'], h['_careerHistoryAudit'])
        self.assertEqual(ca(packed), ca(h))
        self.assertEqual(ca(packed)['acquisition_status'], 'complete')

    def test_legacy_archive_without_audit_is_unverified(self):
        packed = pack_horse({'allPastRuns': [run(d) for d in range(1, 13)]}, RACE['date'])
        a = ca(packed)
        self.assertEqual(a['analyzed_runs'], 12)
        self.assertEqual(a['acquisition_status'], 'unverified')

    def test_corrupt_archive_is_partial_not_crash(self):
        packed = pack_horse(audited([run(d) for d in range(1, 13)], 12), RACE['date'])
        packed['careerArchive']['sha256'] = '0' * 64
        a = ca(packed)
        self.assertEqual(a['acquisition_status'], 'partial')
        self.assertEqual(a['acquisition_evidence']['reason'], 'career-archive-recovery-failed')

    def test_diagnosis_and_detail_share_state(self):
        h = audited([run(d) for d in range(1, 8)], 9)
        h['horseNumber'] = 1
        d = diagnose_horse(h, RACE)
        self.assertEqual(d['careerAnalysis'], d['horseDetail']['careerAnalysis'])
        self.assertEqual(d['careerAnalysis'], ca(h))
        self.assertEqual(d['careerAnalysis']['career_state'], 'partially-acquired')

    def test_all_runs_analyzed_recent_five_displayed(self):
        h = audited([run(d) for d in range(1, 13)], 12)
        d = build_horse_detail(h, RACE)
        self.assertEqual(d['careerAnalysis']['analyzed_runs'], 12)
        self.assertEqual(len(d['recentFive']), 5)


if __name__ == '__main__':
    unittest.main()
