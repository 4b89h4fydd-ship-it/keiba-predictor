"""Replay fixed fitted models on recovered, immutable pre-off snapshots.

NAR calibration dates Nov4-5; test Nov6-10, fixed before prediction.
Source remains provisional; no certification or production writes.
"""
import json
from itertools import groupby
from pathlib import Path
import joblib
import lightgbm as lgb
from arvexq.research.ranking_challenger import prepare_races,make_matrix,_scorecards,metrics
from arvexq.research.ranking_probability import calibrate_and_evaluate,ticket_metrics,date_bootstrap

ROOT=Path('/workspace/arvexq-research-data')
MODELS=Path('/workspace/arvexq-research-models/models')
results={rid:json.loads(p) for rid,p in json.load(open(ROOT/'recovered-results.json'))['rows']}
for p in (ROOT/'result-repairs').glob('*.json'):
    d=json.loads(p.read_text())
    if isinstance(d,dict) and d.get('id'):results[d['id']]=d
names=('ability','ana','pointwise','xgboost','winner','podium')
models={};vectors={};cards={n:{'calibration':[],'test':[]} for n in names};test_races={}
for name in names:
    path=next((MODELS/name/'nar').rglob('ranker.*'))
    vectors[name]=joblib.load(path.parent/'vectorizer.joblib')
    if path.suffix=='.ubj':
        from xgboost import XGBRanker
        model=XGBRanker();model.load_model(path)
    else:model=lgb.Booster(model_file=str(path))
    models[name]=model
with open(ROOT/'recovered-frozen.jsonl') as f:
    rows=(json.loads(line) for line in f)
    for rid,group in groupby(rows,key=lambda r:r['raceId']):
        members=list(group);day=members[0]['date']
        if members[0]['circuit']!='地方':continue
        block='calibration' if '2026-11-04'<=day<='2026-11-05' else 'test' if '2026-11-06'<=day<='2026-11-10' else None
        if block is None:continue
        for name in names:
            races=prepare_races(members,'nar','ana' if name=='ana' else 'ability')
            if len(races)!=1:raise ValueError('paired roster differs')
            x,_,_=make_matrix(races,vectors[name]);pred=list(models[name].predict(x))
            cards[name][block].extend(_scorecards(races,pred))
            if block=='test':test_races[rid]=races[0]
report={'eligibility':'provisional-source-not-independently-attested','splitFixedBeforeScoring':True,'models':{}}
for name in names:
    c=cards[name];test=c['test'];races=[test_races[t['raceId']] for t in test]
    scores=[e['score'] for t in test for e in t['rows']]
    m=metrics(races,scores);cal=calibrate_and_evaluate(c['calibration'],test,train_through='2026-10-24')
    tickets={'単勝':[],'複勝':[]};invalid=[]
    for t in test:
        winner=next(e['horseNumber'] for e in t['rows'] if e['finish']==1)
        top=max(t['rows'],key=lambda e:(e['score'],-e['horseNumber']))['horseNumber']
        payouts=results[t['raceId']]['result'].get('payouts') or []
        if not isinstance(payouts,list):invalid.append(t['raceId']);continue
        pm={k:[p for p in payouts if p.get('type')==k] for k in tickets}
        places=2 if len(t['rows'])<=7 else 3
        expected={e['horseNumber'] for e in t['rows'] if e['finish']<=places}
        try:
            if len(pm['単勝'])!=1 or int(pm['単勝'][0]['combination'])!=winner:raise ValueError()
            if len(pm['複勝'])!=places or {int(p['combination']) for p in pm['複勝']}!=expected:raise ValueError()
            for k in tickets:
                for p in pm[k]:
                    if int(p['amount'])<100:raise ValueError()
                paid=sum(int(p['amount']) for p in pm[k] if int(p['combination'])==top)
                tickets[k].append({'raceId':t['raceId'],'stake':100,'return':paid,'settled':True})
        except (ValueError,KeyError,TypeError):invalid.append(t['raceId'])
    report['models'][name]={'ranking':m,'probability':cal,'payoutCheck':'stored-payout-shape-and-finisher-reconciliation-only',
                           'roi':{k:ticket_metrics(v) for k,v in tickets.items()} if not invalid else None,
                           'invalidPayoutRaceIds':invalid,'calibrationRaces':len(c['calibration']),'testDates':sorted({t['date'] for t in test})}
base={t['raceId']:t for t in cards['ability']['test']}
for name in names:
    pairs=[]
    for t in cards[name]['test']:
        def hit(card):return int(max(card['rows'],key=lambda e:(e['score'],-e['horseNumber']))['finish']==1)
        pairs.append({'date':t['date'],'new':hit(t),'baseline':hit(base[t['raceId']])})
    report['models'][name]['pairedVsAbility']=date_bootstrap(pairs)
(ROOT/'recovered-forward-scores.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2))
(ROOT/'recovered-forward-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({n:{'ranking':r['ranking'],'probability':r['probability'],'roi':r['roi'],'paired':r['pairedVsAbility']} for n,r in report['models'].items()},ensure_ascii=False))
