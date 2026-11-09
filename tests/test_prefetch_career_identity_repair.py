"""Retain every observed career start even if run counts are unchanged."""
import unittest
from scripts.arvexq_select_prefetch_repairs import repair_reason


def card(runs):
    return {'id': 'jra-test', 'date': '2026-10-17',
            'horses': [{'horseNumber': 1, 'name': 'A', 'allPastRuns': runs},
                       {'horseNumber': 2, 'name': 'B', 'allPastRuns': []}],
            'preparedMeta': {'diagnosisReady': True}}


class CareerIdentityRepairTests(unittest.TestCase):
    def test_same_count_different_observation_is_repaired(self):
        fresh = card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])
        stored = card([{'date': '2026-08-01', 'track': '東京', 'finish': 1}])
        self.assertEqual(repair_reason(fresh, stored), 'career_history_missing_observations')

    def test_equivalent_history_not_rewritten(self):
        fresh = card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])
        self.assertEqual(repair_reason(fresh, card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])), '')

    def test_corrupt_archive_requires_repair(self):
        fresh = card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])
        stored = card([])
        stored['horses'][0]['careerArchive'] = {'encoding': 'broken'}
        self.assertEqual(repair_reason(fresh, stored), 'career_archive_invalid')


class CanonicalCareerVerifyTests(unittest.TestCase):
    """The 2026-11-05 Kasamatsu failure: the assembled source carried a
    second representation of an already-stored start (YYYYMMDD date and an
    adapter-specific raceId). Storage canonicalises careers by race date,
    so verification must compare in that canonical form — while a genuinely
    missing start or a different finish must still fail."""

    def _bundles(self, source_runs, saved_runs):
        def detail(runs):
            return {'id': 'jra-test', 'date': '2026-10-17',
                    'horses': [{'horseNumber': 1, 'name': 'A', 'allPastRuns': runs,
                                'recentRaces': runs[:5]},
                               {'horseNumber': 2, 'name': 'B', 'allPastRuns': [],
                                'recentRaces': []}]}
        source = {'summaries': [{'id': 'jra-test'}], 'details': [detail(source_runs)]}
        saved = {'races': [{'id': 'jra-test'}], 'details': [detail(saved_runs)]}
        return source, saved

    def test_variant_representation_of_same_start_passes(self):
        from arvexq.pipeline.persisted_inputs import verify_persisted_facts
        stored = [{'date': '2026-09-01', 'track': '東京', 'raceNumber': 5,
                   'raceId': 'store-id', 'finish': 3}]
        source = stored + [{'date': '20260901', 'track': '東京', 'raceNumber': 5,
                            'raceId': 'official-id', 'finish': 3}]
        src, saved = self._bundles(source, stored)
        self.assertEqual(verify_persisted_facts(src, saved), [])

    def test_missing_start_still_fails(self):
        from arvexq.pipeline.persisted_inputs import verify_persisted_facts
        stored = [{'date': '2026-09-01', 'track': '東京', 'raceNumber': 5, 'finish': 3}]
        source = stored + [{'date': '2026-08-15', 'track': '東京', 'raceNumber': 3, 'finish': 2}]
        src, saved = self._bundles(source, stored)
        errors = verify_persisted_facts(src, saved)
        self.assertTrue(any('allPastRuns-truncated' in e for e in errors), errors)

    def test_finish_disagreement_still_fails(self):
        from arvexq.pipeline.persisted_inputs import verify_persisted_facts
        stored = [{'date': '2026-09-01', 'track': '東京', 'raceNumber': 5, 'finish': 3}]
        source = [{'date': '2026-09-01', 'track': '東京', 'raceNumber': 5, 'finish': 1}]
        src, saved = self._bundles(source, stored)
        errors = verify_persisted_facts(src, saved)
        self.assertTrue(any('allPastRuns-truncated' in e for e in errors), errors)

    def test_blank_finish_placeholder_is_not_a_fact(self):
        # The 2026-11-05 Kasamatsu case: the assembled source carried
        # finish=0 (the CSV adapter's blank-placing sentinel) for a start
        # whose stored career holds the real placing. 0 asserts nothing,
        # so the stored career must verify.
        from arvexq.pipeline.persisted_inputs import verify_persisted_facts
        stored = [{'date': '2026-10-04', 'track': '高知', 'raceNumber': 2, 'finish': 4}]
        source = [{'date': '2026-10-04', 'track': '高知', 'raceNumber': 2, 'finish': 0}]
        src, saved = self._bundles(source, stored)
        self.assertEqual(verify_persisted_facts(src, saved), [])

    def test_real_finish_lost_in_storage_still_fails(self):
        # The reverse direction keeps its teeth: a real placing present in
        # the source but reduced to the placeholder in storage is a loss.
        from arvexq.pipeline.persisted_inputs import verify_persisted_facts
        stored = [{'date': '2026-10-04', 'track': '高知', 'raceNumber': 2, 'finish': 0}]
        source = [{'date': '2026-10-04', 'track': '高知', 'raceNumber': 2, 'finish': 4}]
        src, saved = self._bundles(source, stored)
        errors = verify_persisted_facts(src, saved)
        self.assertTrue(any('allPastRuns-truncated' in e for e in errors), errors)


if __name__ == '__main__':
    unittest.main()
