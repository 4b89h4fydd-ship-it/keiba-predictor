#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.prediction.mass_feature_snapshot import build_mass_feature_snapshot


def horse(no, odds, popularity, finishes, speeds):
    runs=[]
    for i,(finish,speed) in enumerate(zip(finishes,speeds)):
        runs.append({
            'date':f'2026-09-{30-i:02d}',
            'finish':finish,
            'fieldSize':12,
            'distance':1600,
            'track':'T',
            'surface':'芝',
            'condition':'良',
            'speedIndex':speed,
            'opponentLevel':100-i,
            'corner4':max(1,finish),
        })
    return {
        'horseNumber':no,
        'name':f'H{no}',
        'winOdds':odds,
        'popularity':popularity,
        'recentRaces':runs,
    }


base={
    'id':'leak-test-1',
    'date':'2026-10-06',
    'circuit':'中央',
    'track':'T',
    'raceNumber':11,
    'distance':1600,
    'surface':'芝',
    'condition':'良',
    'preRacePrediction':{'modelVersion':'test-lock'},
    'horses':[
        horse(1,2.4,1,[1,2,3,1,4],[105,101,99,104,96]),
        horse(2,5.8,2,[4,3,2,5,3],[98,99,101,96,97]),
        horse(3,12.0,5,[7,6,5,4,3],[91,92,93,94,95]),
    ],
}

first=build_mass_feature_snapshot(base)
mutated=deepcopy(base)
mutated.update({
    'result':{'finishers':[{'horseNumber':3,'finish':1},{'horseNumber':1,'finish':2}]},
    'results':[3,1,2],
    'finishers':[3,1,2],
    'payout':999999,
    'payouts':[{'kind':'3連単','payout':999999}],
    'winner':3,
    'winnerHorseNumber':3,
    'actualFlow':[3,2,1],
    'finalOrder':[3,1,2],
    'confirmedResult':True,
})
second=build_mass_feature_snapshot(mutated)
assert first['featureHash']==second['featureHash'], (first['featureHash'],second['featureHash'])

changed=deepcopy(base)
changed['horses'][0]['recentRaces'][0]['speedIndex']=80
third=build_mass_feature_snapshot(changed)
assert first['featureHash']!=third['featureHash'], 'legitimate pre-race history change must alter feature hash'

names={k for row in first['rows'] for k in row['features']}
assert 'market::win_odds' in names
assert 'market::popularity' in names
for forbidden in ('result','payout','winner','finalOrder','confirmedResult'):
    assert not any(forbidden.lower() in name.lower() for name in names), forbidden

assert first['featureSchema']['featureCount']>100, first['featureSchema']
print('mass-feature-leakage-ok',first['featureSchema']['featureCount'],first['featureHash'][:12])
