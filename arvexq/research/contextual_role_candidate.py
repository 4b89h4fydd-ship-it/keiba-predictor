"""Five-issue challenger. Research only until chronological circuit gates pass.

Scores are uncalibrated relative evidence, never advertised as hit rates.
All constants are hypotheses; validation must precede any live replacement.
"""
from __future__ import annotations

import math
from statistics import mean, pstdev
from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.observed_model import rank_observed, _course_history, _verified_jra_proof, model_version, JRA_MODEL_VERSION
from arvexq.prediction.past_performance import observed_runs
from arvexq.prediction.special_marks import allocate_special_marks

VERSION = 'arvexq-contextual-roles-candidate-v1'


def number(v):
    try:
        x = float(v)
        return x if math.isfinite(x) and v is not None and v != '' else None
    except (TypeError, ValueError):
        return None


def history(horse, race):
    runs = observed_runs(_course_history(horse, race), race, limit=5)
    if model_version(race) == JRA_MODEL_VERSION:
        runs = [q for q in runs if _verified_jra_proof(q)]
    return runs


def comparable(run, race):
    d, target = number(run.get('distance')), number(race.get('distance'))
    return bool(d is not None and target is not None and abs(d-target) <= 150
                and race.get('surface') and run.get('surface') == race['surface'])


def context_weight(run, race, idx):
    # Unknown conditions do not masquerade as matching conditions.
    w = 1 / (1 + idx * .25)
    if comparable(run, race): w *= 2
    if race.get('track') and run.get('track') == race['track']: w *= 1.5
    going = race.get('condition')
    if going and going != '不明' and (run.get('condition') or run.get('going')) == going: w *= 1.25
    level = number(run.get('opponentLevel'))
    if level is not None and 0 <= level <= 1: w *= .5 + .5 * level
    return w


def valid_first(run):
    corners = run.get('cornerPositions')
    fs = number(run.get('fieldSize'))
    first = number(corners[0]) if isinstance(corners, list) and corners else None
    return first if fs and first is not None and 1 <= first <= fs else None


def joint_probabilities(rows):
    """Different observed heads for each slot; exact without-replacement joint."""
    if not rows: return []
    weights = [[math.exp((row['roles'][role] - 1) / .20) for row in rows]
               for role in ('win', 'second', 'third')]
    sums = [sum(w) for w in weights]
    probs = [[0., 0., 0.] for row in rows]
    joint = []
    for i in range(len(rows)):
        p1 = weights[0][i] / sums[0]
        probs[i][0] += p1
        for j in range(len(rows)):
            if i == j: continue
            p12 = p1 * weights[1][j] / (sums[1] - weights[1][i])
            probs[j][1] += p12
            for k in range(len(rows)):
                if k in (i, j): continue
                p123 = p12 * weights[2][k] / (sums[2] - weights[2][i] - weights[2][j])
                probs[k][2] += p123
                joint.append((i, j, k, p123))
    for row, p in zip(rows, probs): row['relativeSlotProbabilities'] = p
    return joint


def predict(race):
    ranked = rank_observed(race.get('horses') or [], race)
    histories = {int(row['horse']['horseNumber']): history(row['horse'], race) for row in ranked}
    front = sum(any(valid_first(q) is not None and valid_first(q) <= 3 for q in runs[:3]) for runs in histories.values())
    pressure = front / len(ranked) if ranked else 0
    distance = number(race.get('distance'))
    # Modest bounded context change, evaluated independently against the fixed mix.
    position_weight = max(.35, min(.70, .60 - .20 * pressure +
                          (.05 if distance is not None and distance <= 1400 else 0) -
                          (.05 if distance is not None and distance >= 2000 else 0)))
    for row in ranked:
        runs = histories[int(row['horse']['horseNumber'])]
        weighted = [(q, context_weight(q, race, i)) for i, q in enumerate(runs)]
        den = sum(w for _, w in weighted)
        # No fake neutral histories. rank_observed already requires actual inputs.
        rates = [sum(w * (int(q['finish']) == slot) for q, w in weighted)/den for slot in (1, 2, 3)]
        quality = [(int(q['fieldSize'])-int(q['finish']))/(int(q['fieldSize'])-1) for q in runs]
        top3 = sum(w * (int(q['finish']) <= 3) for q,w in weighted)/den
        comp = [q for q in runs if comparable(q,race)]
        # Reproduction requires proof in current surface/distance, not an old peak alone.
        reproducible = [q for q in comp if int(q['finish']) <= 3 or (
            number(q.get('marginSeconds', q.get('timeBehindWinner'))) is not None and
            0 <= number(q.get('marginSeconds', q.get('timeBehindWinner'))) <= .70)]
        firsts = [valid_first(q) for q in runs if valid_first(q) is not None]
        front_habit = mean(f <= 3 for f in firsts) if firsts else None
        pace_fit = (1 - pressure * front_habit) if front_habit is not None else None
        base = position_weight * row['factors']['mineta'] + (1-position_weight) * row['factors']['margin']
        # Empirical slot tendencies have limited influence in a five-run sample.
        trust = min(1., len(runs)/5)
        row['contextScore'] = base
        row['roles'] = {name: (1-.30*trust)*base + .30*trust*rate for name,rate in zip(('win','second','third'),rates)}
        axis = .50 * base + .50 * top3 - .10 * pstdev(quality)
        if pace_fit is not None: axis -= .10 * (1-pace_fit)
        row['roles']['axis'] = axis
        row['roleEvidence'] = dict(samples=len(runs),slotRates=rates,top3Rate=top3,
            qualityDeviation=pstdev(quality),comparableRuns=len(comp),reproductionRuns=len(reproducible),
            opponentKnownRuns=sum(number(q.get('opponentLevel')) is not None for q in runs),
            paceFit=pace_fit,frontPressureRunners=front,positionWeight=position_weight,
            marginWeight=1-position_weight)
    win_order = sorted(ranked, key=lambda row:(-row['roles']['win'],int(row['horse']['horseNumber'])))
    special = allocate_special_marks(win_order, race)
    marks = {}
    if win_order:
        marks[int(win_order[0]['horse']['horseNumber'])] = '◎'
    remaining = list(win_order[1:])
    for label, key in (('○','win'),('▲','second'),('△','third')):
        if not remaining: break
        # ○ evaluates first/second aptitude; ▲ second/third aptitude.
        def score(row):
            s = row['roles']
            return (s['win']+s['second'] if label=='○' else s['second']+s['third'] if label=='▲' else s[key])
        chosen = max(remaining,key=lambda row:(score(row),-int(row['horse']['horseNumber'])))
        marks[int(chosen['horse']['horseNumber'])] = label
        remaining.remove(chosen)
    # Compare special evidence before final core allocation: keep only reproducible
    # special marks, and preserve existing primary ◎/○ roles.
    for label, flag in (('☆','star'),('注','note')):
        candidates = [row for row in win_order[2:] if special[int(row['horse']['horseNumber'])].get(flag)
                      and row['roleEvidence']['reproductionRuns'] > 0]
        if label == '☆':
            candidates = [row for row in candidates if row['roleEvidence']['paceFit'] is not None
                          and row['roleEvidence']['paceFit'] >= .6]
        candidates = [row for row in candidates if marks.get(int(row['horse']['horseNumber'])) not in ('◎','○','☆','注')]
        if candidates:
            chosen = max(candidates,key=lambda row:(special[int(row['horse']['horseNumber'])][flag+'Strength'],-int(row['horse']['horseNumber'])))
            marks[int(chosen['horse']['horseNumber'])] = label
    # Refill displaced ▲/△ by their own slot evidence.
    for label, roles in (('▲',('second','third')),('△',('third',))):
        if label in marks.values(): continue
        pool=[row for row in win_order if int(row['horse']['horseNumber']) not in marks]
        if pool:
            chosen=max(pool,key=lambda row:(sum(row['roles'][role] for role in roles),-int(row['horse']['horseNumber'])))
            marks[int(chosen['horse']['horseNumber'])]=label
    axis = max((row for row in ranked if row['sample']>=3),key=lambda row:(row['roles']['axis'],-int(row['horse']['horseNumber'])),default=None)
    for row in ranked: row['mark'] = marks.get(int(row['horse']['horseNumber']), '')
    active = [h for h in race.get('horses',[]) if not is_inactive_runner(h)]
    full = len(ranked)==len(active) and len(ranked)>=3
    joint = joint_probabilities(ranked) if full else []
    return dict(version=VERSION, rows=ranked, marks=marks,
                axisHorseNumber=int(axis['horse']['horseNumber']) if axis and full else 0,
                fullyObserved=full, joint=joint,
                status='research-only-unvalidated')
