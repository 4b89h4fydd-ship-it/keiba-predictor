import copy
import unittest
from scripts.arvexq_verify_history_bundle import verify_history


def detail(rid,ranks,payouts=True,status='確定'):
    return {'id':rid,'result':{'status':status,'finishers':[{'horseNumber':no,'finish':rank} for no,rank in enumerate(ranks,1)],'payouts':[{'type':'単勝','amount':100}] if payouts else []}}

class HistoryVerificationTests(unittest.TestCase):
    def test_actual_failed_day_deadheat_rank_patterns(self):
        # Observed in 2026-03-20 Saga 7R and Obihiro 5R; no rank 3 / rank 2 exists.
        rows=[detail('saga',[1,2,2,4]),detail('obihiro',[1,1,3,4])]
        self.assertTrue(verify_history({'races':2},{'details':rows})['ok'])

    def test_missing_payout_still_fails(self):
        verdict=verify_history({'races':1},{'details':[detail('race',[1,2,2],False)]})
        self.assertFalse(verdict['ok'])
        self.assertFalse(verdict['unexpectedIncomplete'][0]['payoutComplete'])

    def test_incomplete_podium_and_nonfinal_result_still_fail(self):
        for ranks,status in [([1,2],'確定'),([1,2,3],'未確定')]:
            with self.subTest(ranks=ranks,status=status):
                self.assertFalse(verify_history({'races':1},{'details':[detail('race',ranks,status=status)]})['ok'])

    def test_explicit_unresolved_and_cancelled_are_distinct(self):
        bad=detail('unresolved',[],False);cancelled=detail('cancelled',[],False,'取止')
        report={'races':2,'missing_result':['unresolved']}
        self.assertTrue(verify_history(report,{'details':[bad,cancelled]})['ok'])
        self.assertFalse(verify_history({'races':2},{'details':[bad,cancelled]})['ok'])

    def test_cold_start_56_expected_only_44_published_reports_missing_ids(self):
        labels={f"nar-2026-01-18-test-{n:02d}":f"test {n}R" for n in range(1,57)}
        retained=list(labels)[:44]
        day={'races':[{'id':rid} for rid in retained],
             'details':[detail(rid,[1,2,3]) for rid in retained]}
        result=verify_history({'races':56,'labels':labels},day)
        self.assertFalse(result['ok'])
        self.assertEqual(result['details'],44)
        self.assertEqual(result['missingRaceIds'],sorted(list(labels)[44:]))
        self.assertEqual(result['missingSummaryRaceIds'],sorted(list(labels)[44:]))

    def test_equal_count_but_wrong_race_ids_never_passes(self):
        report={'races':2,'labels':{'race-A':'A','race-B':'B'}}
        day={'races':[{'id':'race-A'},{'id':'race-C'}],
             'details':[detail('race-A',[1,2,3]),detail('race-C',[1,2,3])]}
        verdict=verify_history(report,day)
        self.assertFalse(verdict['ok'])
        self.assertEqual(verdict['missingRaceIds'],['race-B'])
        self.assertEqual(verdict['unexpectedRaceIds'],['race-C'])

    def test_missing_whole_race_fails_and_input_is_immutable(self):
        day={'details':[detail('race',[1,2,3])]};before=copy.deepcopy(day)
        self.assertFalse(verify_history({'races':2},day)['ok'])
        self.assertEqual(day,before)
