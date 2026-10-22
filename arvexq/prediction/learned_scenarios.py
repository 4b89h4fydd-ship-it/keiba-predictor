"""Date-bounded learned scenario challenger, never a production fallback.

No hand-weighted ability sum. Coefficients are fitted only from explicitly
provided earlier races. Conditional scenarios are sensitivity tests, not a
claimed reproduction of any tipster's proprietary algorithm.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
from itertools import permutations
from math import exp, isfinite, log1p, sqrt
from statistics import mean, median, pstdev
import json

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import observed_runs, _number, _positions

VERSION = 'arvexq-learned-whole-career-scenarios-v2'
FEATURES = ('win_rate', 'top2_rate', 'top3_rate', 'finish_median', 'finish_peak',
            'recent_finish_mean', 'finish_spread', 'log_starts',
            'same_track_finish', 'same_distance_finish', 'same_surface_finish',
            'same_going_finish', 'same_class_finish', 'early_position',
            'late_position', 'closing_gain', 'rest_log_days', 'distance_change',
            'weight_change', 'same_jockey_finish', 'early_field_mean',
            'early_field_spread', 'early_relative', 'early_pressure_interaction',
            'comparable_margin', 'comparable_sectional_rank',
            'recent_win_rate', 'recent_top2_rate', 'recent_top3_rate',
            'same_direction_win_rate', 'same_direction_top2_rate', 'same_direction_top3_rate',
            'same_condition_win_rate', 'same_condition_top2_rate', 'same_condition_top3_rate',
            'recent_same_condition_win_rate', 'recent_same_condition_top2_rate', 'recent_same_condition_top3_rate',
            'win_sampling_error', 'top3_sampling_error', 'trainer_match', 'circuit_transfer')
JRA_TRACKS = {'札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉'}


def race_family(detail):
    if '帯広' in str(detail.get('track') or ''):
        return 'banei'
    if '障' in str(detail.get('surface') or '') or detail.get('analysisMode') == '障害' or '障害' in str(detail.get('title') or ''):
        return 'jumps'
    return 'flat'


def active_horses(detail):
    return sorted([h for h in detail.get('horses', []) if isinstance(h, dict)
                   and h.get('horseNumber') and not is_inactive_runner(h)
                   and not h.get('cancelled')], key=lambda h: int(h['horseNumber']))


def _quality(row):
    return (row['fieldSize'] - row['finish']) / (row['fieldSize'] - 1)


def _median(values):
    values = [v for v in values if v is not None]
    return median(values) if values else None


def _position(row, last=False):
    corners = _positions(row.get('cornerPositions') or row.get('passing'))
    if not corners:
        return None
    p = corners[-1] if last else corners[0]
    return (row['fieldSize'] - p) / (row['fieldSize'] - 1) if 1 <= p <= row['fieldSize'] else None


def rate_evidence(runs):
    """Observed frequencies with Wilson 95% intervals, not current-race forecasts."""
    n = len(runs)
    result = {'starts': n, 'status': 'observed-history-not-predicted-probability'}
    for key, rank in (('win', 1), ('top2', 2), ('top3', 3)):
        hits = sum(r['finish'] <= rank for r in runs)
        p = hits / n if n else None
        interval = None
        error = None
        if n:
            z = 1.959963984540054
            denominator = 1 + z*z/n
            center = (p + z*z/(2*n))/denominator
            radius = z*sqrt(p*(1-p)/n + z*z/(4*n*n))/denominator
            interval = [max(0., center-radius), min(1., center+radius)]
            error = radius
        result[key] = {'hits': hits, 'rate': p, 'percent': p*100 if n else None,
                       'interval95': interval, 'intervalHalfWidth': error}
    return result


def evidence(horse, detail):
    # A jump start and a flat start are different events; never train one as
    # interchangeable evidence for the other. Banei likewise has its own family.
    runs = [r for r in observed_runs(horse, detail, limit=None)
            if race_family(r) == race_family(detail)]
    qualities = [_quality(r) for r in runs]
    distance = _number(detail.get('distance'))
    surface, track = detail.get('surface'), detail.get('track')
    going, klass = detail.get('condition'), detail.get('class') or detail.get('className')
    match = lambda key, value: [_quality(r) for r in runs if value and r.get(key) == value]
    same_distance = [r for r in runs if distance and _number(r.get('distance')) == distance]
    comparable = [r for r in same_distance if surface and r.get('surface') == surface
                  and track and r.get('track') == track]
    direction = detail.get('direction') or detail.get('courseDirection')
    same_direction = [r for r in runs if direction and r.get('direction') == direction]
    same_condition = [r for r in comparable if direction and r.get('direction') == direction]
    rates = {name: rate_evidence(rows) for name, rows in (
        ('all', runs), ('recent', runs[:5]), ('sameDistance', same_distance),
        ('sameTrack', [r for r in runs if track and r.get('track') == track]),
        ('sameDirection', same_direction), ('sameCondition', same_condition),
        ('recentSameCondition', same_condition[:5]))}
    n = len(runs)
    early = [_position(r) for r in runs]
    late = [_position(r, True) for r in runs]
    gain = [q-p for q,p in zip(qualities,late) if p is not None]
    recent = runs[0] if runs else {}
    old_distance = _number(recent.get('distance'))
    old_weight, weight = _number(recent.get('carriedWeight')), _number(horse.get('carriedWeight'))
    rest = (date.fromisoformat(detail['date']) - date.fromisoformat(recent['_raceDate'])).days if runs else None
    values = [sum(r['finish'] == 1 for r in runs)/n if n else None,
              sum(r['finish'] <= 2 for r in runs)/n if n else None,
              sum(r['finish'] <= 3 for r in runs)/n if n else None,
              _median(qualities), max(qualities) if qualities else None,
              mean(qualities[:5]) if qualities else None,
              pstdev(qualities) if len(qualities) > 1 else None, log1p(n) if n else None,
              _median(match('track', track)), _median([_quality(r) for r in same_distance]),
              _median(match('surface', surface)), _median(match('condition', going)),
              _median([_quality(r) for r in runs if klass and (r.get('class') or r.get('className')) == klass]),
              _median(early), _median(late), _median(gain), log1p(rest) if rest is not None else None,
              (distance-old_distance)/old_distance if distance and old_distance else None,
              weight-old_weight if weight is not None and old_weight is not None else None,
              _median(match('jockey', horse.get('jockey'))), None, None, None, None,
              _median([_number(r.get('marginSeconds', r.get('timeBehindWinner'))) for r in comparable]),
              _median([(r['fieldSize']-rank)/(r['fieldSize']-1) for r in comparable
                       if (rank := _number(r.get('last3fRank'))) is not None and 1 <= rank <= r['fieldSize']])]
    audit = horse.get('_careerHistoryAudit') or {}
    old_track = recent.get('track')
    transfer = ('中央から地方' if old_track in JRA_TRACKS and detail.get('circuit') == '地方' else
                '地方から中央' if old_track and old_track not in JRA_TRACKS and detail.get('circuit') == '中央' else None)
    for scope in ('recent', 'sameDirection', 'sameCondition', 'recentSameCondition'):
        values.extend(rates[scope][key]['rate'] for key in ('win', 'top2', 'top3'))
    values.extend([rates['all']['win']['intervalHalfWidth'], rates['all']['top3']['intervalHalfWidth'],
                   float(recent['trainer'] == horse['trainer']) if recent.get('trainer') and horse.get('trainer') else None,
                   float(bool(transfer)) if old_track else None])
    fields = ('sire', 'dam', 'trainer', 'jockey', 'carriedWeight', 'bodyWeight', 'bodyWeightChange')
    return {'horseNumber': int(horse['horseNumber']), 'name': horse.get('name', ''),
            'observedStarts': n, 'careerComplete': audit.get('complete') is True,
            'careerCoverageStatus': audit.get('status', 'unverified'),
            'featureValues': dict(zip(FEATURES, values)), 'rateEvidence': rates,
            'positionObservations': [v for v in early if v is not None],
            'transfer': transfer, 'missingFields': [k for k in fields if horse.get(k) in (None, '')],
            'sourceDates': [r['_raceDate'] for r in runs],
            'note': '通算率は確認できた過去走の範囲。全履歴の網羅が未確認なら生涯実績と断定しない'}


def race_evidence(detail, *, scenario='usual'):
    reports = [evidence(h, detail) for h in active_horses(detail)]
    if scenario not in ('usual', 'forward', 'held-up'):
        raise ValueError('unknown scenario')
    for r in reports:
        p = r['positionObservations']
        if p and scenario != 'usual':
            # Empirical quartiles are scenario assumptions, never performance boosts.
            ordered = sorted(p)
            r['featureValues']['early_position'] = ordered[(3*(len(p)-1))//4 if scenario == 'forward' else (len(p)-1)//4]
    positions = [r['featureValues']['early_position'] for r in reports if r['featureValues']['early_position'] is not None]
    center, spread = (mean(positions), pstdev(positions)) if positions else (None, None)
    for r in reports:
        f = r['featureValues']
        p = f['early_position']
        f['early_field_mean'], f['early_field_spread'] = center, spread
        f['early_relative'] = p-center if p is not None and center is not None else None
        f['early_pressure_interaction'] = p*center if p is not None and center is not None else None
    return reports


def _sigmoid(x):
    return 1/(1+exp(-max(-40., min(40., x))))


def _vector(report, centers, scales):
    values = [report['featureValues'][k] for k in FEATURES]
    return [(float(v)-c)/s if v is not None else 0. for v,c,s in zip(values,centers,scales)] + [float(v is None) for v in values]


def fit_model(details, *, circuit, family='flat', epochs=150, learning_rate=.03, l2=.01):
    """Pairwise logistic ranking. Fixed optimizer settings are not ability weights.

    This is training code, not validation: fit only on a prespecified earlier
    partition. Evaluation dates are enforced by predict_model.
    """
    if circuit not in ('中央', '地方'):
        raise ValueError('explicit circuit required')
    samples, ids, dates = [], [], []
    for detail in sorted(details, key=lambda d: (d.get('date',''), d.get('id',''))):
        if detail.get('circuit') != circuit or race_family(detail) != family:
            continue
        rid = detail.get('id')
        if not rid or rid in ids:
            raise ValueError('duplicate or missing training race ID')
        if (detail.get('result') or {}).get('status') != '確定':
            continue
        finishers = detail['result'].get('finishers', [])
        if not isinstance(finishers, list) or not finishers:
            continue
        try:
            if any(not isinstance(r, dict) or not r.get('horseNumber') or not r.get('finish')
                   or isinstance(r['horseNumber'], bool) or isinstance(r['finish'], bool)
                   or int(r['horseNumber']) <= 0 or int(r['finish']) <= 0
                   for r in finishers):
                continue
            labels = {int(r['horseNumber']): int(r['finish']) for r in finishers}
        except (TypeError, ValueError, OverflowError):
            continue
        # Train only against the complete active field. Partial results or missing
        # pre-race history must not silently bias winner ranking toward covered horses.
        rows = race_evidence(detail)
        numbers = [r['horseNumber'] for r in rows]
        finishers = [r for r in detail['result'].get('finishers', [])
                     if isinstance(r, dict) and r.get('horseNumber') and r.get('finish')]
        finish_numbers = [int(r['horseNumber']) for r in finishers]
        if (len(rows) < 3 or len(set(numbers)) != len(numbers)
                or len(finishers) != len(labels)
                or set(numbers) != set(labels)
                or len(set(finish_numbers)) != len(finish_numbers)
                or sum(rank == 1 for rank in labels.values()) != 1
                or any(not r['observedStarts'] for r in rows)):
            continue
        samples.append((rows, labels))
        ids.append(rid); dates.append(detail['date'])
    if not samples:
        raise ValueError('no observed, labelled training races')
    all_rows = [r for rows,_ in samples for r in rows]
    centers, scales = [], []
    for key in FEATURES:
        vals = [r['featureValues'][key] for r in all_rows if r['featureValues'][key] is not None]
        centers.append(mean(vals) if vals else 0.)
        scales.append(pstdev(vals) if len(vals) > 1 and pstdev(vals) > 0 else 1.)
    pairs = []
    for rows, labels in samples:
        vectors = [_vector(r, centers, scales) for r in rows]
        race_pairs = []
        for i in range(len(rows)):
            for j in range(i+1,len(rows)):
                a,b = labels[rows[i]['horseNumber']], labels[rows[j]['horseNumber']]
                if a != b:
                    race_pairs.append(([x-y for x,y in zip(vectors[i],vectors[j])], float(a < b)))
        if race_pairs:
            pairs.append(race_pairs)
    if not pairs:
        raise ValueError('training labels contain no ordered pairs')
    weights = [0.]*(2*len(FEATURES))
    for _ in range(epochs):
        gradient = [l2*w for w in weights]
        for race_pairs in pairs:
            for vector,label in race_pairs:
                error = _sigmoid(sum(w*x for w,x in zip(weights,vector)))-label
                for k,x in enumerate(vector):
                    gradient[k] += error*x/(len(pairs)*len(race_pairs))
        weights = [w-learning_rate*g for w,g in zip(weights,gradient)]
    input_hash = sha256(json.dumps(samples, sort_keys=True, ensure_ascii=False,
                                   separators=(',', ':')).encode()).hexdigest()
    training = {'raceIds': ids, 'lastDate': max(dates), 'races': len(ids), 'circuit': circuit,
                'family': family, 'inputEvidenceHash': input_hash}
    artifact = {'version': VERSION, 'features': list(FEATURES), 'centers': centers, 'scales': scales,
                'weights': weights, 'training': training, 'calibrationStatus': 'unvalidated',
                'optimizer': {'epochs': epochs, 'learningRate': learning_rate, 'l2': l2}}
    artifact['modelHash'] = sha256(json.dumps(artifact,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    return artifact


def _orders(rows, utilities):
    maximum = max(utilities)
    weights = {r['horseNumber']: exp(max(-30., u-maximum)) for r,u in zip(rows,utilities)}
    total = sum(weights.values())
    orders = []
    # Top-three disjoint events suffice for all eight supported bet rules.
    for a,b,c in permutations(weights,3):
        p = weights[a]/total*weights[b]/(total-weights[a])*weights[c]/(total-weights[a]-weights[b])
        # Tail identity is retained to satisfy field completeness; its order is
        # irrelevant to any top-three bet, not an estimated lower finishing order.
        orders.append({'order': [a,b,c]+[n for n in weights if n not in (a,b,c)], 'probability': p})
    return orders


def predict_model(detail, model):
    if model.get('version') != VERSION or model.get('features') != list(FEATURES):
        raise ValueError('model feature/version mismatch')
    training = model['training']
    if not detail.get('id') or not detail.get('date'):
        raise ValueError('race identity and date required')
    if detail.get('circuit') != training['circuit']:
        raise ValueError('cross-circuit model prohibited')
    if race_family(detail) != training['family']:
        raise ValueError('flat, jumps and banei models cannot be interchanged')
    if detail.get('id') in training['raceIds'] or detail.get('date','') <= training['lastDate']:
        raise ValueError('prediction must be strictly later than all training races')
    if len(model['weights']) != len(FEATURES)*2 or len(model['centers']) != len(FEATURES) or len(model['scales']) != len(FEATURES):
        raise ValueError('invalid model dimensions')
    if any(not isfinite(float(v)) for key in ('weights','centers','scales') for v in model[key]) or any(v <= 0 for v in model['scales']):
        raise ValueError('invalid model parameters')
    unhashed = {k:v for k,v in model.items() if k != 'modelHash'}
    expected_hash = sha256(json.dumps(unhashed, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    if model.get('modelHash') != expected_hash:
        raise ValueError('model artifact hash mismatch')
    scenarios = []
    base = race_evidence(detail)
    if len(base) < 3 or any(not r['observedStarts'] for r in base):
        return {'version': VERSION, 'status': 'insufficient-history', 'reports': base, 'scenarios': []}
    for name,label in [('usual','通常の隊列'),('forward','前の位置を取り合う場合'),('held-up','想定より後ろに控える場合')]:
        rows = race_evidence(detail,scenario=name)
        if name != 'usual' and any(not r['positionObservations'] for r in rows):
            continue
        utilities = [sum(w*x for w,x in zip(model['weights'],_vector(r,model['centers'],model['scales']))) for r in rows]
        orders = _orders(rows,utilities)
        probs = {r['horseNumber']: {'win': 0., 'top2': 0., 'top3': 0.} for r in rows}
        for event in orders:
            probs[event['order'][0]]['win'] += event['probability']
            for no in event['order'][:2]:
                probs[no]['top2'] += event['probability']
            for no in event['order'][:3]:
                probs[no]['top3'] += event['probability']
        scenarios.append({'id': name, 'label': label, 'orders': orders, 'probabilities': probs,
                          'assumptionStatus': 'positional-sensitivity-not-validated-pace-frequency'})
    return {'version': VERSION, 'modelHash': model['modelHash'], 'status': 'uncalibrated-challenger',
            'reports': base, 'scenarios': scenarios, 'probabilityStatus': 'uncalibrated',
            'unsupported': ['展開の発生頻度', '血統・厩舎の因果的効果', '同日馬場バイアス',
                            '異クラス間の能力換算', '陣営の意図', '未観測の過去走']}
