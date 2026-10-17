"""Strict historical evaluation of *frozen* research tickets, never post-race reconstructions.

Inputs must be independently snapshotted before scheduled off and have a
verified provenance; this module never computes candidate tickets from results.
"""
from collections import defaultdict
from datetime import datetime
from arvexq.backtest.ticket_metrics import parse_official_payouts, ticket_payout
from arvexq.betting.scenario_tickets import canonical

KINDS = ('単勝','複勝','枠連','馬連','馬単','ワイド','3連複','3連単')


def _date(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed
    except (AttributeError, TypeError, ValueError):
        return None


def evaluate_frozen_candidates(records):
    """Return separately scoped measurements; reject unverifiable cases.

    Each record has frozen candidate, capturedAt, scheduledOffAt, result,
    circuit, and independent verification flags. No claim of holdout status is
    inferred from model features or from a claimed date alone.
    """
    groups = defaultdict(list)
    exclusions = defaultdict(int)
    seen_races = set()
    for record in records:
        if not isinstance(record, dict):
            exclusions['malformed-record'] += 1
            continue
        captured, off = _date(record.get('capturedAt')), _date(record.get('scheduledOffAt'))
        if (not captured or not off or captured >= off or
                record.get('preoffSourceVerified') is not True or
                record.get('heldOutFromTraining') is not True):
            exclusions['not-proven-preoff-holdout'] += 1
            continue
        candidate, result = record.get('candidate'), record.get('result')
        if not isinstance(candidate, dict) or candidate.get('status') != 'research-only-not-a-recommendation':
            exclusions['missing-frozen-candidate'] += 1
            continue
        if not isinstance(result, dict) or result.get('status') != '確定':
            exclusions['not-final'] += 1
            continue
        kind = candidate.get('kind')
        combos = candidate.get('combos')
        if kind not in KINDS or not isinstance(combos, list) or not 1 <= len(combos) <= 10:
            exclusions['invalid-ticket'] += 1
            continue
        try:
            normalized = [canonical(kind, combo) for combo in combos]
            if len(set(normalized)) != len(normalized):
                raise ValueError('duplicate combinations')
        except (TypeError, ValueError, KeyError):
            exclusions['invalid-ticket'] += 1
            continue
        race_id = record.get('raceId')
        if not isinstance(race_id, str) or not race_id.strip():
            exclusions['missing-race-identity'] += 1
            continue
        if race_id in seen_races:
            exclusions['duplicate-race'] += 1
            continue
        seen_races.add(race_id)
        payouts, invalid = parse_official_payouts(result)
        paid = ticket_payout(kind, combos, payouts, invalid)
        if paid is None:
            exclusions['missing-official-payout'] += 1
            continue
        circuit = record.get('circuit')
        if circuit not in ('中央', '地方'):
            exclusions['unknown-circuit'] += 1
            continue
        groups[(circuit, kind)].append((paid, len(combos)))
    by_circuit = {}
    for circuit in ('中央', '地方'):
        by_kind = {}
        for kind in KINDS:
            rows = groups[(circuit, kind)]
            n = len(rows)
            stake = sum(points * 100 for _, points in rows)
            paid = sum(amount for amount, _ in rows)
            by_kind[kind] = {'evaluatedRaces': n, 'hitRaces': sum(amount > 0 for amount, _ in rows),
                            'measuredHitRate': sum(amount > 0 for amount, _ in rows) / n if n else None,
                            'averagePoints': sum(points for _, points in rows) / n if n else None,
                            'stakeYenAt100': stake, 'payoutYenAt100': paid if n else None,
                            'flatStakeReturnRate': paid / stake if stake else None}
        by_circuit[circuit] = by_kind
    return {'version': 'arvexq-frozen-research-ticket-evaluation-v1',
            'researchOnly': True, 'notRecommendedBets': True,
            'byCircuit': by_circuit, 'excluded': dict(exclusions),
            'target80Achieved': False,
            'note': 'Observed fractions are not calibrated probabilities. A pass/fail adoption gate requires separately preregistered sample and coverage requirements.'}
