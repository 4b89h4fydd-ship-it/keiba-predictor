"""Fail-closed verification of archived research capture receipts."""
from pathlib import Path
from arvexq.backtest.verify_research_receipt import verify_receipt


def audit_capture(receipt_dir, capture_report):
    paths = sorted(Path(receipt_dir).glob('*.json'))
    saved = capture_report.get('saved') if isinstance(capture_report, dict) else None
    if not isinstance(saved, list) or not saved or len(saved) != len(paths):
        return {'verified': False, 'receiptCount': len(paths), 'reason': 'count-or-report-mismatch'}
    expected = [item.get('raceId') for item in saved if isinstance(item, dict)]
    if len(expected) != len(saved) or any(not isinstance(x, str) or not x for x in expected):
        return {'verified': False, 'receiptCount': len(paths), 'reason': 'invalid-report-race-ids'}
    if len(expected) != len(set(expected)):
        return {'verified': False, 'receiptCount': len(paths), 'reason': 'duplicate-reported-race'}
    actual = []
    try:
        for path in paths:
            actual.append(verify_receipt(path)['raceId'])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return {'verified': False, 'receiptCount': len(paths), 'reason': 'invalid-receipt', 'detail': str(exc)}
    return {'verified': sorted(expected) == sorted(actual),
            'receiptCount': len(paths),
            'reason': 'verified-local-checksums-only' if sorted(expected) == sorted(actual) else 'race-identity-mismatch',
            'independentlyVerifiedPreoff': False}
