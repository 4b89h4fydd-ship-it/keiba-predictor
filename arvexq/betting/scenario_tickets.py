"""Bounded all-kind comparison over joint, conditional finishing distributions.

No independence approximation for overlapping tickets; no scenario mixing weights.
Probabilities are conditional model estimates, never observed hit rates. This
module has no dependency on any retired ranking or ticket generator.
"""
from __future__ import annotations

from itertools import combinations, permutations
from math import isfinite
from typing import Any
from arvexq.core.runner_status import is_inactive_runner

VERSION = 'arvexq-scenario-tickets-v1'
KINDS = ('単勝', '複勝', '枠連', '馬連', '馬単', 'ワイド', '3連複', '3連単')
UNORDERED = {'枠連', '馬連', 'ワイド', '3連複'}
MARKS = {'◎', '○', '▲', '△', '☆', '注'}


def canonical(kind, combo):
    values = tuple(int(n) for n in combo)
    size = 3 if kind in ('3連複', '3連単') else 1 if kind in ('単勝', '複勝') else 2
    if kind not in KINDS or len(values) != size or any(n <= 0 for n in values):
        raise ValueError('invalid ticket')
    if kind != '枠連' and len(set(values)) != len(values):
        raise ValueError('a horse cannot occupy two places')
    return tuple(sorted(values)) if kind in UNORDERED else values


def ticket_hit(kind, combo, order, *, frames=None, place_places=None):
    """For a complete non-dead-heat order; official payouts settle dead heats."""
    c = canonical(kind, combo)
    t = tuple(int(n) for n in order)
    if len(set(t)) != len(t):
        raise ValueError('duplicate horse in finishing order')
    if kind == '単勝':
        return bool(t) and c[0] == t[0]
    if kind == '複勝':
        if place_places not in (2, 3):
            raise ValueError('official place terms required')
        return c[0] in t[:place_places]
    if kind == '枠連':
        if not frames or len(t) < 2 or any(n not in frames for n in t[:2]):
            raise ValueError('frame evidence required')
        return c == tuple(sorted(frames[n] for n in t[:2]))
    if kind == '馬単':
        return c == t[:2]
    if kind == '馬連':
        return len(t) >= 2 and c == tuple(sorted(t[:2]))
    if kind == 'ワイド':
        return len(t) >= 3 and set(c).issubset(t[:3])
    if kind == '3連複':
        return len(t) >= 3 and c == tuple(sorted(t[:3]))
    return c == t[:3]


def validate_scenarios(scenarios, runners):
    """Require the same full field and proper probability mass in every branch."""
    if not scenarios:
        raise ValueError('missing joint scenario distribution')
    runner_set = set(runners)
    clean = []
    seen = set()
    for scenario in scenarios:
        name = str(scenario.get('id') or '')
        if not name or name in seen:
            raise ValueError('scenario IDs must be present and unique')
        seen.add(name)
        orders = []
        for row in scenario.get('orders') or []:
            order = tuple(int(n) for n in row['order'])
            p = float(row['probability'])
            if len(order) != len(runner_set) or set(order) != runner_set:
                raise ValueError('all active runners required in each order')
            if not isfinite(p) or not 0 <= p <= 1:
                raise ValueError('invalid probability')
            orders.append((order, p))
        if not orders or abs(sum(p for _, p in orders) - 1) > 1e-6:
            raise ValueError('scenario probability mass must sum to one')
        clean.append((name, orders))
    return clean


def compare_tickets(detail: dict[str, Any], scenarios: list[dict[str, Any]], *,
                    model_version: str, max_points: int = 10,
                    target: float = .8) -> dict[str, Any]:
    """Compare all eight kinds, and return reference candidates only.

    Statistical validation belongs to a separately locked holdout evaluation.
    Never turn a modeled 80% chance into an assertion of 80% measured accuracy.
    Decimal odds must come from an explicitly pre-off market snapshot. A caller
    must separately validate its timestamp/provenance before execution.
    """
    if not isinstance(max_points, int) or isinstance(max_points, bool) or not 1 <= max_points <= 10:
        raise ValueError('point budget must be between one and ten')
    if not 0 < target < 1:
        raise ValueError('target must be a probability')
    horses = [h for h in detail.get('horses', []) if isinstance(h, dict)
              and not is_inactive_runner(h) and not h.get('cancelled')
              and h.get('horseNumber')]
    runners = [int(h['horseNumber']) for h in horses]
    if len(set(runners)) != len(runners) or len(runners) < 3:
        raise ValueError('invalid active field')
    distributions = validate_scenarios(scenarios, runners)
    marked = {int(h['horseNumber']): h.get('integratedEvaluation', {}).get('mark', '') for h in horses}
    honmei = [n for n, mark in marked.items() if mark == '◎']
    if len(honmei) != 1:
        raise ValueError('exactly one unified honmei required')
    axis = honmei[0]
    partners = [n for n, mark in marked.items() if mark in MARKS]
    frames = {int(h['horseNumber']): int(h['frameNumber']) for h in horses if h.get('frameNumber')}
    allowed = detail.get('availableBetTypes')
    place_places = detail.get('placePlaces')
    market = detail.get('preOffMarket') or {}
    market_prices = market.get('odds') if market.get('provenanceVerified') is True else {}
    market_prices = market_prices if isinstance(market_prices, dict) else {}
    comparisons = []
    for kind in KINDS:
        entry = {'kind': kind, 'combos': [], 'points': 0,
                 'conditionalProbabilityRange': None, 'expectedReturnRange': None,
                 'decision': '見送り', 'reason': ''}
        comparisons.append(entry)
        if not isinstance(allowed, list) or kind not in allowed:
            entry['reason'] = '発売券種の確認資料なし' if allowed is None else '発売対象外'
            continue
        if kind == '複勝' and place_places not in (2, 3):
            entry['reason'] = '複勝の払戻対象着順が未確認'
            continue
        if kind == '枠連' and len(frames) != len(runners):
            entry['reason'] = '全頭の枠番が未確認'
            continue
        if kind in ('単勝', '複勝'):
            candidates = [(axis,)]
        elif kind == '枠連':
            candidates = sorted({tuple(sorted((frames[axis], frames[n]))) for n in partners if n != axis})
        elif kind in ('馬連', 'ワイド'):
            candidates = [tuple(sorted((axis, n))) for n in partners if n != axis]
        elif kind == '馬単':
            candidates = [(axis, n) for n in partners if n != axis] + [(n, axis) for n in partners if n != axis]
        elif kind == '3連複':
            candidates = [tuple(sorted((axis, *c))) for c in combinations([n for n in partners if n != axis], 2)]
        else:
            candidates = [c for c in permutations(partners, 3) if axis in c]
        candidates = sorted(set(candidates))
        events = []
        for combo in candidates:
            hits = [{i for i, (o, _) in enumerate(orders)
                     if ticket_hit(kind, combo, o, frames=frames, place_places=place_places)}
                    for _, orders in distributions]
            probs = [sum(orders[i][1] for i in hit) for hit, (_, orders) in zip(hits, distributions)]
            # A combination may hit in only some scenarios. Retain it so the
            # union of up to ten tickets can cover complementary scenarios.
            # Reject only a ticket that never hits in any modeled scenario.
            if max(probs) <= 0:
                continue
            prices = market_prices.get(kind, {})
            price = prices.get('-'.join(map(str, combo))) if isinstance(prices, dict) else None
            try:
                price = float(price)
                if not isfinite(price) or price <= 1:
                    price = None
            except (TypeError, ValueError):
                price = None
            events.append({'combo': combo, 'hits': hits, 'probs': probs, 'odds': price})
        covered = [set() for _ in distributions]
        chosen = []
        remaining = events[:]
        probabilities = [0.] * len(distributions)
        while remaining and len(chosen) < max_points:
            def gain(event):
                mass = [sum(orders[i][1] for i in covered[j] | event['hits'][j])
                        for j, (_, orders) in enumerate(distributions)]
                return (min(mass), sum(mass), tuple(-n for n in event['combo']))
            best = max(remaining, key=gain)
            if gain(best)[0] <= min(probabilities) and gain(best)[1] <= sum(probabilities):
                break
            chosen.append(best)
            remaining.remove(best)
            for j in range(len(covered)):
                covered[j].update(best['hits'][j])
            probabilities = [sum(orders[i][1] for i in covered[j]) for j, (_, orders) in enumerate(distributions)]
            if min(probabilities) >= target:
                break
        entry['combos'] = [list(e['combo']) for e in chosen]
        entry['points'] = len(chosen)
        if not chosen:
            entry['reason'] = '全展開で根拠を持つ組み合わせなし'
            continue
        entry['conditionalProbabilityRange'] = [min(probabilities), max(probabilities)]
        entry['lossProbabilityRange'] = [1 - max(probabilities), 1 - min(probabilities)]
        entry['stakeYenAt100'] = len(chosen) * 100
        if all(e['odds'] is not None for e in chosen):
            returns = [sum(e['probs'][j] * e['odds'] for e in chosen) / len(chosen)
                       for j in range(len(distributions))]
            entry['expectedReturnRange'] = [min(returns), max(returns)]
        entry['reason'] = ('点数上限内で条件付き確率が目標未達' if min(probabilities) < target else
                           '条件付き確率は目標内だが未使用データの実測検証が未完了')
        if entry['expectedReturnRange'] is None:
            entry['reason'] += '。発走前の券種別オッズ不足により期待回収は不明'
    # Research-only leader. This is *not* a recommended bet: modeled chance
    # cannot substitute for independently measured pre-off accuracy.
    eligible = [entry for entry in comparisons if entry['combos']
                and entry['conditionalProbabilityRange'] is not None]
    ranked = sorted(eligible, key=lambda entry: (
        -entry['conditionalProbabilityRange'][0],
        -(entry['expectedReturnRange'][0] if entry['expectedReturnRange'] is not None else -1),
        entry['points'], KINDS.index(entry['kind'])))
    research_leader = ({
        'kind': ranked[0]['kind'],
        'combos': ranked[0]['combos'],
        'points': ranked[0]['points'],
        'conditionalProbabilityRange': ranked[0]['conditionalProbabilityRange'],
        'expectedReturnRange': ranked[0]['expectedReturnRange'],
        'status': 'research-only-not-a-recommendation',
    } if ranked else None)
    return {'researchLeader': research_leader,
            'eligibleCandidateKinds': len(eligible),
            'version': VERSION, 'modelVersion': model_version,
            'raceId': detail.get('id'), 'honmeiHorseNumber': axis,
            'comparisons': comparisons, 'decision': '見送り', 'items': [],
            'reason': '候補の全券種比較。未使用データによる検証が完了するまで推奨を確定しない',
            'probabilityStatus': 'conditional-model-estimate-not-measured-hit-rate',
            'maxPoints': max_points, 'targetHitRate': target}
