"""Offline, reproducible challenger diagnostic. Does not write production/D1.

These archived days were used in prior research. No claim of untouched holdout
performance is permitted. Result/odds fields never enter model features.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from arvexq.prediction.learned_scenarios import VERSION, fit_model, race_family
from arvexq.prediction.new_forecast import build_forecast


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def run(source: Path, *, train_date: str, evaluate_date: str):
    corpus, hashes = [], {}
    for path in sorted(source.rglob('*.json')):
        wrapper = json.loads(path.read_text())
        if not isinstance(wrapper, dict):
            continue
        detail = wrapper.get('detail',wrapper)
        if not isinstance(detail,dict) or not detail.get('id') or not isinstance(detail.get('horses'),list):
            continue
        if detail['id'] in hashes:
            raise ValueError('duplicate race in corpus: '+detail['id'])
        corpus.append(detail); hashes[detail['id']] = sha256(path.read_bytes()).hexdigest()
    if train_date >= evaluate_date:
        raise ValueError('training must precede evaluation')
    models, training_errors = {}, {}
    for circuit in ('中央','地方'):
        training = [d for d in corpus if d.get('date') == train_date and d.get('circuit') == circuit]
        try:
            models[circuit] = fit_model(training,circuit=circuit)
        except ValueError as exc:
            training_errors[circuit] = str(exc)
    rows = []
    for detail in sorted(corpus,key=lambda d:d['id']):
        if detail.get('date') != evaluate_date:
            continue
        source_before = digest(detail)
        original_hash = digest({k:detail.get(k) for k in ('preRacePrediction','preRaceBet')})
        row = {'raceId':detail['id'],'circuit':detail.get('circuit'),'track':detail.get('track'),
               'sourceSha256':hashes[detail['id']],'analysisType':'retrospective',
               'raceFamily':race_family(detail)}
        model = models.get(detail.get('circuit'))
        if model is None or race_family(detail) != 'flat':
            row.update({'status':'unsupported-or-untrained','honmei':0,'recommended':False})
            rows.append(row); continue
        result = build_forecast(detail,model)
        assert original_hash == digest({k:result.get(k) for k in ('preRacePrediction','preRaceBet')})
        assert digest(detail) == source_before
        honmei = result['honmeiDecision']['horseNumber']
        finish = next((r.get('finish') for r in (detail.get('result') or {}).get('finishers',[])
                       if r.get('horseNumber') == honmei),None) if honmei else None
        plan = result['recommendedBetPlan']
        row.update({'status':result['predictionStatus'],'honmei':honmei,'finish':finish,
                    'modelHash':model['modelHash'],'originalRecordHash':original_hash,
                    'originalRecordsPreserved':True,'forecastText':result['forecastText'],
                    'recommended':bool(plan.get('items')),'betPlan':plan,
                    'marks':[{ 'horseNumber':h['horseNumber'],'mark':h['integratedEvaluation']['mark'],
                              'reason':h['integratedEvaluation']['markReason'],
                              'probabilityRanges':h['integratedEvaluation']['modelProbabilities']}
                             for h in result['horses']],
                    'careerCompleteHorses':sum(r['careerComplete'] for r in result['scenarioAnalysis']['reports']),
                    'activeHorses':len(result['scenarioAnalysis']['reports'])})
        rows.append(row)
    summary = {}
    for circuit in ('中央','地方'):
        group = [r for r in rows if r['circuit']==circuit]
        scored = [r for r in group if isinstance(r.get('finish'),int) and r['finish'] > 0]
        plans = [r for r in group if r.get('recommended')]
        summary[circuit] = {'targetRaces':len(group),'axisScoredRaces':len(scored),
                            'axisWins':sum(r['finish']==1 for r in scored),
                            'axisTop3':sum(r['finish']<=3 for r in scored),
                            'axisWinRate':sum(r['finish']==1 for r in scored)/len(scored) if scored else None,
                            'axisTop3Rate':sum(r['finish']<=3 for r in scored)/len(scored) if scored else None,
                            'recommendedRaces':len(plans),'recommendedHitRate':None,
                            'returnRate':None,'stakeYenAt100':0 if not plans else None,
                            'skipRate':1-len(plans)/len(group) if group else None,
                            'statuses':dict(Counter(r['status'] for r in group)),
                            'target80Achieved':False,
                            'note':'事後診断。全見送りは的中率達成ではない。中央の評価対象がなければ不足。'}
    return {'version':VERSION,'trainDate':train_date,'evaluateDate':evaluate_date,
            'validationStatus':'reused-archived-day-diagnostic-not-untouched-holdout',
            'inputSourceHashes':hashes,'trainingErrors':training_errors,
            'models':models,'byCircuit':summary,'races':rows,
            'productionEligible':False,
            'limitations':['取得応答は事後保存。各入力が発走前に既知だったことの完全な証明はない',
                           '全過去走の網羅性は未確認','単純な位置取りの感度分析であり、展開発生頻度は未学習',
                           '現行ブラウザー・APIには未接続','未使用データ検証と推奨判断の校正が必要']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--train-date',default='2026-10-12')
    parser.add_argument('--evaluate-date',default='2026-10-16')
    args=parser.parse_args()
    result=run(args.input_dir,train_date=args.train_date,evaluate_date=args.evaluate_date)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['byCircuit'],ensure_ascii=False,indent=2))
