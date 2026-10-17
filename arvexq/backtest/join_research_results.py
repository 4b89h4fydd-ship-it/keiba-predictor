"""Join frozen receipts with independently supplied official results for an audit.

This is an offline research join, NOT a historical pre-off proof. The output
never asserts verification of pre-off timestamps or the training split.
"""
from copy import deepcopy
from pathlib import Path
from arvexq.backtest.verify_research_receipt import verify_receipt
from arvexq.backtest.frozen_research_tickets import evaluate_frozen_candidates
import json


def join_receipts(receipt_dir, results_by_race):
    rows, invalid = [], []
    for path in sorted(Path(receipt_dir).glob('*.json')):
        try:
            proof = verify_receipt(path)
            receipt = json.loads(path.read_text(encoding='utf-8'))['snapshot']
            race_id = proof['raceId']
            result = results_by_race.get(race_id)
            if not isinstance(result, dict):
                invalid.append({'raceId': race_id, 'reason': 'missing-official-result'})
                continue
            rows.append({'raceId': race_id, 'circuit': receipt.get('circuit'),
                         'candidate': deepcopy(receipt['candidate']),
                         'capturedAt': receipt['capturedAt'],
                         'scheduledOffAt': receipt['scheduledOffAt'],
                         'result': deepcopy(result),
                         'preoffSourceVerified': False,
                         'heldOutFromTraining': False})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            invalid.append({'receipt': path.name, 'reason': 'invalid-receipt', 'detail': str(exc)})
    return {'version': 'arvexq-frozen-research-join-v1',
            'joined': rows, 'unjoined': invalid,
            'measured': evaluate_frozen_candidates(rows),
            'requiresIndependentProvenanceReview': True}
