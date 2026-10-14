"""Research-only JRA/NAR feature combinations and one-percent weights."""
import itertools

FEATURES = {'jra': ('trueRun','pure','distanceFit','momentum'), 'nar': ('trueRun','pure','trackFit','earlyPace','distanceFit')}

def candidate_weights(circuit):
    features = FEATURES[circuit]
    for extra_count in (0,1,2):
        for extras in itertools.combinations(features[2:], extra_count):
            for added in itertools.product(range(0,31), repeat=extra_count):
                remaining = 100-sum(added)
                for first in range(remaining+1):
                    yield features[:2]+extras, (first,remaining-first)+added

def evaluate(races, keys, weights):
    n = wins = top3 = 0
    for race in races:
        horses = race.get('horses') or []
        if not horses or race.get('winnerHorseNumber') is None:
            continue
        scored=[]
        for horse in horses:
            try:
                values=[float(horse[k]) for k in keys]
                if not all(0 <= x <= 1 for x in values): raise ValueError('invalid feature')
                scored.append((sum(a*b for a,b in zip(values,weights)),int(horse['horseNumber'])))
            except (KeyError,TypeError,ValueError):
                scored=[]
                break
        if not scored: continue
        ranked=[x[1] for x in sorted(scored,key=lambda x:(-x[0],x[1]))]
        n+=1
        wins+=int(ranked[0]==int(race['winnerHorseNumber']))
        top3+=int(int(race['winnerHorseNumber']) in ranked[:3])
    return (n,wins,top3)
