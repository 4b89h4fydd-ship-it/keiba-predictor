"""Research-only weight search. Input: JSON array of PRE-OFF frozen race feature rows.
Each race: {circuit,date,winnerHorseNumber,horses:[{horseNumber,trueRun,pure,sectional}]}.
No result-derived features permitted. No production model mutation.
"""
import argparse
import json


def sweep(races, holdout_fraction=.25):
    out = {}
    for circuit in ('jra', 'nar'):
        selected = sorted((r for r in races if str(r.get('circuit','')).lower() == circuit), key=lambda r: str(r.get('date','')))
        dates = sorted({str(r.get('date','')) for r in selected})
        if len(dates) < 4:
            out[circuit] = {'error':'insufficient-distinct-dates', 'races':len(selected)}
            continue
        cutoff = dates[max(1, int(len(dates)*(1-holdout_fraction)))]
        train = [r for r in selected if str(r.get('date','')) < cutoff]
        test = [r for r in selected if str(r.get('date','')) >= cutoff]
        def evaluate(group, weights):
            wins = top3 = eligible = 0
            for race in group:
                horses = race.get('horses') or []
                if not horses or not race.get('winnerHorseNumber'):
                    continue
                if any(any(h.get(k) is None for k in ('trueRun','pure','sectional')) for h in horses):
                    continue  # Do not fabricate missing evidence
                if any(any(not (0 <= float(h[k]) <= 1) for k in ('trueRun','pure','sectional')) for h in horses):
                    continue  # Reject out-of-range inputs
                ranked = sorted(horses,key=lambda h: -sum(weights[i]*float(h[k]) for i,k in enumerate(('trueRun','pure','sectional'))))
                eligible += 1
                winner = int(race['winnerHorseNumber'])
                wins += int(int(ranked[0]['horseNumber']) == winner)
                top3 += int(any(int(h['horseNumber']) == winner for h in ranked[:3]))
            return {'races':eligible,'wins':wins,'winnerTop3':top3,'winRate':wins/eligible if eligible else None,'top3Rate':top3/eligible if eligible else None}
        candidates = [(a,b,100-a-b) for a in range(0,101,1) for b in range(0,101-a,1)]
        scored = [(evaluate(train,tuple(w/100 for w in candidate)),candidate) for candidate in candidates]
        valid = [(s,w) for s,w in scored if s['races'] >= 20]
        if not valid:
            out[circuit] = {'error':'insufficient-complete-training-races','trainRaces':len(train),'testRaces':len(test)}
            continue
        # Avoid overfitting a single winner: favor top-3 capture, then win rate.
        best = max(valid,key=lambda x:(x[0]['top3Rate'],x[0]['winRate'],-sum(abs(a-b) for a,b in zip(x[1],(45,35,20)))))
        baseline = (.45,.35,.20)
        held = evaluate(test,tuple(w/100 for w in best[1]))
        base = evaluate(test,baseline)
        improved = (held['races'] >= 20 and held['races'] == base['races'] and held['top3Rate'] > base['top3Rate'] and held['winRate'] >= base['winRate'])
        out[circuit] = {'cutoffDate':cutoff,'bestWeightsPercent':best[1], 'training':best[0], 'holdout':held, 'baselineHoldout':base, 'eligibleForPromotion':bool(improved), 'note':'research-only; never auto-promote on retrospective replay'}
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('frozen_races_json')
    args = parser.parse_args()
    with open(args.frozen_races_json,encoding='utf-8') as f:
        races=json.load(f)
    print(json.dumps(sweep(races),ensure_ascii=False,indent=2))
