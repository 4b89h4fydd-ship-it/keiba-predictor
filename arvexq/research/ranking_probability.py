"""Separate probability calibration; rank scores alone are never calibrated."""
import math
import random
from collections import defaultdict

TEMPERATURES = (.1, .2, .5, 1., 2., 5., 10.)


def win_probabilities(scores, temperature):
    if not scores or temperature <= 0 or any(not math.isfinite(x) for x in scores):
        raise ValueError('invalid ranking scores/temperature')
    m = max(scores)
    weights = [math.exp(max(-700., (x-m)/temperature)) for x in scores]
    return [x/sum(weights) for x in weights]


def podium_probabilities(scores, temperature):
    """Plackett-Luce top-three inclusion; not a calibrated claim by itself."""
    if len(scores) < 3:
        raise ValueError("three active runners required")
    weights = win_probabilities(scores, temperature)
    inclusion = [0.] * len(scores)
    for i, pi in enumerate(weights):
        rest_i = sum(weights[j] for j in range(len(weights)) if j != i)
        if rest_i <= 0:continue
        for j, pj in enumerate(weights):
            if j == i:continue
            rest_ij = sum(weights[k] for k in range(len(weights)) if k not in (i,j))
            if rest_ij <= 0:continue
            for k, pk in enumerate(weights):
                if k in (i,j):continue
                p = pi * pj/rest_i * pk/rest_ij
                for index in (i,j,k):inclusion[index] += p
    return inclusion


def probability_metrics(cards, temperature):
    losses, briers, podium_briers = [], [], []
    bins = defaultdict(list)
    for card in cards:
        rows = card['rows']; p = win_probabilities([r['score'] for r in rows], temperature)
        pp = podium_probabilities([r['score'] for r in rows], temperature)
        podium_briers.append(sum((v-int(rows[i]['finish']<=3))**2 for i,v in enumerate(pp)))
        winners = [i for i,r in enumerate(rows) if r['finish'] == 1]
        if len(winners) != 1:
            raise ValueError('exactly one winner required')
        losses.append(-math.log(max(p[winners[0]], 1e-15)))
        briers.append(sum((v-int(i==winners[0]))**2 for i,v in enumerate(p)))
        for i,v in enumerate(p):bins[min(9,int(v*10))].append((v,int(i==winners[0])))
    if not losses:return {'races':0,'logLoss':None,'brier':None,'ece':None}
    curve = [{'bin':k,'n':len(v),'predicted':sum(x for x,y in v)/len(v),
              'observed':sum(y for x,y in v)/len(v)} for k,v in sorted(bins.items())]
    total = sum(b['n'] for b in curve)
    return {'races':len(cards),'logLoss':sum(losses)/len(losses),
            'brier':sum(briers)/len(briers),
            'podiumBrier':sum(podium_briers)/len(podium_briers),
            'ece':sum(b['n']*abs(b['predicted']-b['observed']) for b in curve)/total,
            'calibrationCurve':curve,'brierDefinition':'sum across runners, average across races'}


def calibrate_and_evaluate(calibration, test, *, train_through=None):
    cd = {c['date'] for c in calibration}; td = {c['date'] for c in test}
    if not train_through or not cd or train_through >= min(cd):
        raise ValueError('training must precede calibration')
    if len(cd)<2 or len(td)<2 or max(cd)>=min(td):
        raise ValueError('independent multi-date calibration and later test required')
    if {c['raceId'] for c in calibration} & {c['raceId'] for c in test}:
        raise ValueError('race overlap')
    best = min(TEMPERATURES,key=lambda t: probability_metrics(calibration,t)['logLoss'])
    podium = min(TEMPERATURES,key=lambda t: probability_metrics(calibration,t)['podiumBrier'])
    return {'temperature':best,'podiumTemperature':podium,
            'podiumAfter':probability_metrics(test,podium)['podiumBrier'],'before':probability_metrics(test,1),
            'after':probability_metrics(test,best),'productionEligible':False,
            'note':'candidate calibration; score-generation training must independently precede calibration'}


def date_bootstrap(paired, seed=20261110, samples=2000):
    """Paired scalar differences clustered on day; no inference from one day."""
    grouped = defaultdict(list)
    for r in paired:grouped[r['date']].append(r['new']-r['baseline'])
    if len(grouped)<2:return {'status':'insufficient-dates','days':len(grouped),'ci95':None}
    days = sorted(grouped); rng=random.Random(seed); values=[]
    for _ in range(samples):
        draw=[x for _ in days for x in grouped[rng.choice(days)]]
        values.append(sum(draw)/len(draw))
    values.sort(); allvalues=[x for v in grouped.values() for x in v]
    return {'days':len(days),'races':len(paired),'meanDifference':sum(allvalues)/len(allvalues),
            'wins':sum(x>0 for x in allvalues),'losses':sum(x<0 for x in allvalues),
            'ci95':[values[int(.025*samples)],values[min(samples-1,int(.975*samples))]]}


def ticket_metrics(tickets):
    """Exact settled cash flows only. No implied payout from odds."""
    if not tickets:return {'tickets':0,'roi':None,'roiWithoutLargestPayout':None}
    if any(t.get('settled') is not True or t.get('stake',0)<=0 or t.get('return',-1)<0 for t in tickets):
        raise ValueError('settled positive stakes and actual nonnegative returns required')
    stake=sum(t['stake'] for t in tickets); returns=sum(t['return'] for t in tickets)
    return {'tickets':len(tickets),'stake':stake,'return':returns,'profit':returns-stake,
            'hitRate':sum(t['return']>0 for t in tickets)/len(tickets),'roi':returns/stake,
            'roiWithoutLargestPayout':(returns-max(t['return'] for t in tickets))/stake,
            'largestPayoutPolicy':'remove largest payout, retain all original stakes'}
