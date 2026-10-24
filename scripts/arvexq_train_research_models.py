#!/usr/bin/env python3
"""Fit research models from a separate earlier dated D1 snapshot, never target races."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from arvexq.prediction.learned_scenarios import fit_model
from arvexq.prediction.fusion_historical_replay import train_and_validate


def train_models(source, target_date):
    details = source.get('details') if isinstance(source, dict) else None
    if not isinstance(details, list):
        raise ValueError('training source must have a details array')
    eligible = [d for d in details if isinstance(d, dict) and isinstance(d.get('date'), str)
                and d['date'] < target_date and (d.get('result') or {}).get('status') == '確定']
    models, errors = {}, {}
    for circuit in ('中央', '地方'):
        subset = [d for d in eligible if d.get('circuit') == circuit]
        if not subset:
            errors[circuit] = 'no eligible earlier finalized races'
            continue
        try:
            models[circuit] = fit_model(subset, circuit=circuit)
        except ValueError as exc:
            errors[circuit] = str(exc)
    # Use the SAME earlier D1 detail collection, not a new feed/endpoint.
    # The ensemble must have a disjoint training period and >=30 unseen
    # official-payout evaluations. No replay is called a frozen preoff receipt.
    fusion = {}
    for circuit in ('中央','地方'):
        # The legacy training helper also serves very small and empty
        # test batches. Independent fusion needs >=30 train PLUS >=30
        # temporally later holdout races, so do not mark small inputs
        # as a failure of the separate existing research model.
        subset = [d for d in eligible if d.get('circuit') == circuit]
        if len(subset) < 60 or len({d.get('date') for d in subset}) < 2:
            continue
        try:
            fusion[circuit] = train_and_validate(
                subset, circuit=circuit, target_date=target_date)
        except (ValueError, TypeError, KeyError, OverflowError, ZeroDivisionError) as exc:
            errors['fusion:' + circuit] = type(exc).__name__ + ': ' + str(exc)
    if fusion:
        models['fusion'] = fusion
    return models, errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--input', type=Path)
    inputs.add_argument('--input-dir', type=Path)
    parser.add_argument('--target-date', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.input_dir:
        source_files = sorted(p for p in args.input_dir.glob('*.json') if not p.name.endswith('-report.json'))
        combined = {'details': []}
        seen = set()
        for file in source_files:
            source = json.loads(file.read_text(encoding='utf-8'))
            for detail in source.get('details', []):
                if not isinstance(detail, dict):
                    continue
                identity = (detail.get('date'), detail.get('id'))
                if identity in seen:
                    continue
                seen.add(identity)
                combined['details'].append(detail)
    else:
        source_files = [args.input]
        combined = json.loads(args.input.read_text(encoding='utf-8'))
    models, errors = train_models(combined, args.target_date)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(models,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    args.report.write_text(json.dumps({'trainedCircuits':sorted(models),
        'errors':errors,'source':'earlier-dated-D1-details',
        'targetDate':args.target_date,'researchOnly':True,
        'fusionCalibratedCircuits':sorted((models.get('fusion') or {})),
        'fusionAudits':{c:res.get('audit') for c,res in (models.get('fusion') or {}).items()},
        'sourceDates':sorted({d.get('date') for d in combined['details'] if isinstance(d,dict) and d.get('date')}),
        'inputFileCount':len(source_files),'eligibleRecordCount':sum(1 for d in combined['details'] if isinstance(d,dict) and (d.get('result') or {}).get('status') == '確定' and str(d.get('date') or '') < args.target_date)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'trainedCircuits':sorted(models),'errors':errors},ensure_ascii=False))


if __name__=='__main__':
    main()
