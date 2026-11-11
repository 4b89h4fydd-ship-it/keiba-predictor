"""Read-only Stage 5 audit of ORIGINAL pre-off marks and ticket receipts.

Not a prediction, recommendation, new acquisition path or live API. Input
races must come from independently verified saved originals. Incomplete
results/payouts and reference-only receipts never become losing bets.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from arvexq.backtest.ticket_metrics import parse_official_payouts, ticket_payout
from arvexq.betting.scenario_tickets import KINDS, canonical
from arvexq.prediction.prerace_archive import post_at, sealed_lock
from scripts.arvexq_prerace_bet_integrity import has_valid_original


def _podium(result: Any) -> tuple[int, int, int] | None:
    if not isinstance(result, dict) or result.get('status') != '確定':
        return None
    indexed = {}
    for row in result.get('finishers') or []:
        if not isinstance(row, dict):
            return None
        try:
            pos, no = int(row.get('finish')), int(row.get('horseNumber'))
        except (TypeError, ValueError):
            return None
        if pos in (1, 2, 3):
            if pos in indexed or no <= 0:
                return None
            indexed[pos] = no
    if set(indexed) != {1, 2, 3} or len(set(indexed.values())) != 3:
        return None
    return indexed[1], indexed[2], indexed[3]


def _tickets(items: Any) -> dict[str, list[tuple[int, ...]]] | None:
    """Validate all saved combinations, without creating or changing them."""
    if not isinstance(items, list) or not items:
        return None
    kinds: dict[str, list[tuple[int, ...]]] = {}
    try:
        for item in items:
            if not isinstance(item, dict) or item.get('kind') not in KINDS:
                return None
            kind = item['kind']
            combos = item.get('combos')
            if not isinstance(combos, list) or not 1 <= len(combos) <= 10:
                return None
            normalized = [canonical(kind, c) for c in combos]
            kinds.setdefault(kind, []).extend(normalized)
        if any(len(rows) > 10 or len(rows) != len(set(rows)) for rows in kinds.values()):
            return None
    except (TypeError, ValueError, KeyError, OverflowError):
        return None
    return kinds


def _role(prediction: dict, bet: dict) -> tuple[str | None, int | None, str | None]:
    """Return saved role only; never infer ◎【軸】 from an ◎【単】 podium hit."""
    horses = prediction.get('horses') or []
    hon = [r for r in horses if isinstance(r, dict) and r.get('mark') == '◎']
    if len(hon) != 1:
        return None, None, 'missing-or-ambiguous-honmei'
    try:
        no = int(hon[0]['horseNumber'])
    except (ValueError, TypeError, KeyError):
        return None, None, 'invalid-honmei-number'
    if no <= 0:
        return None, None, 'invalid-honmei-number'
    b = bet.get('honmei')
    role_in_mark = hon[0].get('honmeiRole')
    if b is not None:
        if not isinstance(b, dict):
            return None, no, 'invalid-bet-honmei'
        try:
            bet_no = int(b['horseNumber'])
        except (ValueError, TypeError, KeyError):
            return None, no, 'invalid-bet-honmei'
        if bet_no != no:
            return None, no, 'mark-bet-honmei-mismatch'
        if role_in_mark in ('win', 'axis') and b.get('role') in ('win', 'axis') and role_in_mark != b['role']:
            return None, no, 'mark-bet-role-mismatch'
    role = role_in_mark if role_in_mark in ('win', 'axis') else (b.get('role') if isinstance(b, dict) else None)
    return role if role in ('win', 'axis') else None, no, None


def summarize_original_ticket_evidence(races: list[dict[str, Any]]) -> dict[str, Any]:
    """JRA/NAR-separated observed performance, with explicit evidence gaps.

    ROI is flat 100 yen per unique saved combination, not actual purchases.
    A sample includes only submitted archived records, not all race meetings.
    A missing official payout excludes that kind from assessed ROI/hit rates.
    """
    by_circuit: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for circuit in ('中央', '地方'):
        by_circuit[circuit] = {
            'sourceRaces': 0, 'states': Counter(), 'role': {
                'win': {'scoredRaces': 0, 'wins': 0},
                'axis': {'scoredRaces': 0, 'podiums': 0},
            }, 'byKind': {}, 'inconsistentRaceIds': [],
        }
    for detail in races:
        if not isinstance(detail, dict) or detail.get('circuit') not in by_circuit:
            continue
        group = by_circuit[detail['circuit']]
        group['sourceRaces'] += 1
        status = group['states']
        race_id = detail.get('id')
        if not isinstance(race_id, str) or not race_id:
            status['invalid-race-id'] += 1
            continue
        if race_id in seen:
            status['duplicate-race-id'] += 1
            continue
        seen.add(race_id)
        bet = detail.get('preRaceBet')
        if not isinstance(bet, dict):
            status['no-original-bet'] += 1
            continue
        if bet.get('referenceOnly') is True:
            status['reference-only'] += 1
            # References cannot count as recommendations, but conflicting
            # saved marks and bet role are still material evidence defects.
            lock = sealed_lock(detail)
            post = post_at(detail)
            if lock and post and has_valid_original(bet, race_id=race_id, start_at=post):
                _, _, error = _role(lock, bet)
                if error:
                    status[error] += 1
                    group['inconsistentRaceIds'].append(race_id)
            continue
        if bet.get('referenceOnly') is not False:
            status['reference-status-unknown'] += 1
            continue
        post = post_at(detail)
        lock = sealed_lock(detail)
        if not lock or not post or not has_valid_original(bet, race_id=race_id, start_at=post):
            status['unverified-or-late-original'] += 1
            continue
        if bet.get('decision') == '見送り':
            status['intentional-skip'] += 1
            continue
        combos = _tickets(bet.get('items'))
        if combos is None:
            status['invalid-ticket'] += 1
            continue
        role, number, error = _role(lock, bet)
        if error:
            status[error] += 1
            group['inconsistentRaceIds'].append(race_id)
            continue
        status['validated-nonreference-ticket'] += 1
        result = detail.get('result')
        podium = _podium(result)
        if podium is None:
            status['missing-or-incomplete-final-result'] += 1
        elif role == 'win':
            group['role']['win']['scoredRaces'] += 1
            group['role']['win']['wins'] += int(number == podium[0])
        elif role == 'axis':
            group['role']['axis']['scoredRaces'] += 1
            group['role']['axis']['podiums'] += int(number in podium)
        elif podium is not None:
            status['role-not-proven'] += 1
        official, invalid = parse_official_payouts(result) if podium else ({}, set())
        for kind, selections in combos.items():
            row = group['byKind'].setdefault(kind, {
                'candidateRaces': 0, 'scoredRaces': 0, 'hits': 0,
                'stakeYenAt100': 0, 'payoutYenAt100': 0,
                'pendingResultRaces': 0, 'missingPayoutRaces': 0,
            })
            row['candidateRaces'] += 1
            if podium is None:
                row['pendingResultRaces'] += 1
                continue
            paid = ticket_payout(kind, selections, official, invalid)
            if paid is None:
                row['missingPayoutRaces'] += 1
                continue
            row['scoredRaces'] += 1
            row['hits'] += int(paid > 0)
            row['stakeYenAt100'] += 100 * len(selections)
            row['payoutYenAt100'] += paid
    for group in by_circuit.values():
        group['states'] = dict(sorted(group['states'].items()))
        for row in group['byKind'].values():
            n, stake = row['scoredRaces'], row['stakeYenAt100']
            row['observedHitRate'] = row['hits'] / n if n else None
            row['flatStakeReturnRate'] = row['payoutYenAt100'] / stake if stake else None
            if n == 0:
                row['payoutYenAt100'] = None
    return {
        'version': 'arvexq-stage5-verified-original-ticket-metrics-v1',
        'scope': 'input-saved-originals-only-not-entire-racing-calendar',
        'purchaseStatus': 'simulated-100-yen-per-combination-not-real-purchases',
        'productionRecommendation': False,
        'byCircuit': by_circuit,
    }
