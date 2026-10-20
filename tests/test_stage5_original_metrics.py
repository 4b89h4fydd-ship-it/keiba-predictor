import base64
import gzip
import hashlib
"""Stage5 only: read-only original bets; no prediction or acquisition change."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
from unittest import TestCase

from arvexq.backtest.stage5_original_metrics import summarize_original_ticket_evidence

JST = timezone(timedelta(hours=9))


def race(circuit='中央', kind='馬連', role='win', ref=False, winner=1):
    day = '2026-10-17'
    post = datetime(2026, 10, 17, 14, 0, tzinfo=JST)
    ident = ('jra' if circuit == '中央' else 'nar') + '-2026-10-17-京都-09'
    return {
        'id': ident, 'date': day, 'circuit': circuit, 'startTime': '14:00',
        'preRacePrediction': {
            'raceId': ident, 'raceDate': day, 'capturedAtEpoch': int(post.timestamp()) - 900,
            'frozen': True, 'horses': [
                {'horseNumber': 1, 'mark': '◎', 'honmeiRole': role},
                {'horseNumber': 2, 'mark': '○'},
                {'horseNumber': 3, 'mark': '▲'},
            ],
        },
        'preRaceBet': {
            'raceId': ident, 'fixedAt': '2026-10-17T13:45:00+09:00',
            'decision': '購入候補', 'referenceOnly': ref,
            'honmei': {'horseNumber': 1, 'role': role, 'grade': 'A'},
            'items': [{'kind': kind, 'combos': [[1, 2]] if kind == '馬連' else [[1, 2, 3]]}],
        },
        'result': {
            'status': '確定',
            'finishers': [{'finish': n, 'horseNumber': horse}
                          for n, horse in enumerate([winner, 2, 3] if winner == 1 else [winner, 1, 3], 1)],
            'payouts': [{'type': kind, 'combination': '1-2' if kind == '馬連' else '1-2-3',
                         'amount': 640}],
        },
    }


class Stage5OriginalMetricsTests(TestCase):
    def test_win_and_axis_have_separate_denominators_and_circuits(self):
        jra = race()
        nar = race(circuit='地方', role='axis', winner=2)
        out = summarize_original_ticket_evidence([jra, nar])['byCircuit']
        self.assertEqual(out['中央']['role']['win'], {'scoredRaces': 1, 'wins': 1})
        self.assertEqual(out['中央']['role']['axis']['scoredRaces'], 0)
        self.assertEqual(out['地方']['role']['axis'], {'scoredRaces': 1, 'podiums': 1})
        self.assertEqual(out['地方']['role']['win']['scoredRaces'], 0)

    def test_reference_and_unknown_reference_never_enter_metrics(self):
        reference = race(ref=True)
        unknown = race()
        unknown['id'] += '-2'
        unknown['preRaceBet']['raceId'] = unknown['id']
        unknown['preRacePrediction']['raceId'] = unknown['id']
        unknown['preRaceBet'].pop('referenceOnly')
        out = summarize_original_ticket_evidence([reference, unknown])['byCircuit']['中央']
        self.assertEqual(out['states']['reference-only'], 1)
        self.assertEqual(out['states']['reference-status-unknown'], 1)
        self.assertEqual(out['byKind'], {})

    def test_missing_results_and_payouts_are_unknown_not_losses(self):
        a = race()
        a.pop('result')
        b = race(circuit='地方')
        b['result']['payouts'] = []
        out = summarize_original_ticket_evidence([a, b])['byCircuit']
        x = out['中央']['byKind']['馬連']
        self.assertEqual(x['candidateRaces'], 1)
        self.assertEqual(x['pendingResultRaces'], 1)
        self.assertIsNone(x['observedHitRate'])
        self.assertIsNone(x['payoutYenAt100'])
        y = out['地方']['byKind']['馬連']
        self.assertEqual(y['missingPayoutRaces'], 1)
        self.assertIsNone(y['flatStakeReturnRate'])

    def test_mark_bet_mismatch_is_quarantined_without_repair(self):
        original = race()
        original['preRaceBet']['honmei']['horseNumber'] = 2
        pristine = deepcopy(original)
        out = summarize_original_ticket_evidence([original])['byCircuit']['中央']
        self.assertEqual(out['states']['mark-bet-honmei-mismatch'], 1)
        self.assertEqual(out['inconsistentRaceIds'], [original['id']])
        self.assertEqual(out['byKind'], {})
        self.assertEqual(original, pristine)

    def test_reject_late_or_duplicate_combos(self):
        late = race()
        late['preRaceBet']['fixedAt'] = '2026-10-17T14:00:00+09:00'
        dup = race(circuit='地方')
        dup['preRaceBet']['items'][0]['combos'] = [[1, 2], [2, 1]]
        out = summarize_original_ticket_evidence([late, dup])['byCircuit']
        self.assertEqual(out['中央']['states']['unverified-or-late-original'], 1)
        self.assertEqual(out['地方']['states']['invalid-ticket'], 1)

    def test_official_payout_and_exact_order(self):
        r = race(kind='3連単')
        out = summarize_original_ticket_evidence([r])['byCircuit']['中央']['byKind']['3連単']
        self.assertEqual((out['candidateRaces'], out['scoredRaces'], out['hits']), (1, 1, 1))
        self.assertEqual(out['stakeYenAt100'], 100)
        self.assertEqual(out['payoutYenAt100'], 640)
        self.assertEqual(out['flatStakeReturnRate'], 6.4)
        # Official payout, not inferred finish order, settles the bet.
        r['result']['finishers'][0]['horseNumber'] = 2
        r['result']['finishers'][1]['horseNumber'] = 1
        out = summarize_original_ticket_evidence([r])['byCircuit']['中央']['byKind']['3連単']
        self.assertEqual(out['hits'], 1)

    def test_existing_archived_originals_offline_reproduce_three_central_races(self):
        """Read actual immutable blobs, verified with the existing SHA check."""
        root = Path(__file__).resolve().parents[1] / 'arvexq/ui/static/saved-snapshots'
        records = []
        for day in ('2026-10-10', '2026-10-17'):
            manifest = json.loads((root / (day + '.json')).read_text(encoding='utf-8'))
            for race_id, item in manifest['races'].items():
                if not item.get('bet'):
                    continue
                blob = json.loads((root / item['file']).read_text(encoding='utf-8'))
                self.assertEqual(blob['version'], 'arvexq-saved-snapshot-v1')
                self.assertEqual(blob['sha256'], item['sha256'])
                compressed = base64.b64decode(blob['gzipBase64'], validate=True)
                self.assertLessEqual(len(compressed), 8 * 1024 * 1024)
                original_bytes = gzip.decompress(compressed)
                self.assertLessEqual(len(original_bytes), 16 * 1024 * 1024)
                self.assertEqual(len(original_bytes), item['bytes'])
                self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), item['sha256'])
                race_data = json.loads(original_bytes.decode('utf-8'))
                self.assertEqual(race_data['id'], race_id)
                self.assertEqual(race_data['date'], day)
                records.append(race_data)
        self.assertEqual(len(records), 14)
        out = summarize_original_ticket_evidence(records)['byCircuit']
        jra, nar = out['中央'], out['地方']
        self.assertEqual(jra['sourceRaces'], 12)
        self.assertEqual(nar['sourceRaces'], 2)
        self.assertEqual(jra['states']['reference-only'], 8)
        self.assertIn('jra-2026-10-17-新潟-09', jra['inconsistentRaceIds'])
        self.assertEqual(nar['states']['reference-only'], 1)
        self.assertEqual(nar['states']['reference-status-unknown'], 1)
        self.assertEqual(jra['states']['validated-nonreference-ticket'], 4)
        self.assertEqual(jra['states']['missing-or-incomplete-final-result'], 1)
        self.assertEqual(jra['role']['win'], {'scoredRaces': 3, 'wins': 0})
        self.assertEqual(jra['role']['axis'], {'scoredRaces': 0, 'podiums': 0})
        self.assertEqual(jra['byKind']['馬連']['hits'], 1)
        self.assertEqual(jra['byKind']['馬連']['scoredRaces'], 3)
        self.assertEqual(jra['byKind']['馬連']['payoutYenAt100'], 640)
        self.assertEqual(jra['byKind']['馬連']['stakeYenAt100'], 300)
        self.assertEqual(jra['byKind']['ワイド']['scoredRaces'], 3)
        self.assertEqual(jra['byKind']['ワイド']['hits'], 0)
        self.assertEqual(jra['byKind']['3連単']['scoredRaces'], 3)
        self.assertEqual(jra['byKind']['3連単']['stakeYenAt100'], 1800)
        self.assertEqual(jra['byKind']['3連単']['hits'], 0)
