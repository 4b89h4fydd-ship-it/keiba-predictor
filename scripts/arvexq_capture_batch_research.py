#!/usr/bin/env python3
"""Batch research capture from prefetch bundle, without altering production.

Run before off time against a current bundle and earlier trained models.
The receipts are locally timed and still need independent provenance review.
"""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from arvexq.prediction.new_forecast import build_forecast
from arvexq.backtest.freeze_research_candidate import freeze_research_candidate


def capture(bundle, models, receipt_dir):
    details = bundle.get('details') if isinstance(bundle, dict) else None
    if not isinstance(details, list):
        raise ValueError('bundle.details must be a list of race cards')
    if not isinstance(models, dict):
        raise ValueError('models must be a circuit-keyed dictionary')
    saved, skipped = [], {}
    for race in details:
        race_id = race.get('id') if isinstance(race, dict) else None
        if not race_id or not isinstance(race.get('date'), str):
            skipped[str(race_id)] = 'missing-race-identity-or-date'
            continue
        model = models.get(race.get('circuit'))
        if not isinstance(model, dict):
            skipped[race_id] = 'missing-circuit-model'
            continue
        training = model.get('training') or {}
        if not isinstance(training, dict) or not training.get('lastDate') or training['lastDate'] >= race['date']:
            skipped[race_id] = 'training-not-earlier-than-race'
            continue
        if race.get('result') or race.get('analysisType') == 'retrospective':
            skipped[race_id] = 'retrospective-race'
            continue
        try:
            prediction = build_forecast(race,model)
            if prediction.get('analysisType') != 'preoff-candidate':
                raise ValueError('not-before-post')
            path = freeze_research_candidate(race,prediction['recommendedBetPlan'],receipt_dir)
            saved.append({'raceId':race_id,'receipt':str(path)})
        except Exception as exc:
            # A malformed or oversized race must not block later race receipts.
            # Include the error type for audit; do not mark a skipped race saved.
            skipped[race_id] = type(exc).__name__ + ': ' + str(exc)
    return {'saved':saved, 'skipped':skipped, 'researchOnly':True,
            'independentlyVerifiedPreoff':False}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--receipt-dir',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(argv)
    result=capture(json.loads(args.bundle.read_text(encoding='utf-8')),
                   json.loads(args.models.read_text(encoding='utf-8')),args.receipt_dir)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'saved':len(result['saved']),'skipped':len(result['skipped'])},ensure_ascii=False))


if __name__=='__main__':
    main()
