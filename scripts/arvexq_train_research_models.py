#!/usr/bin/env python3
"""Fit research models from a separate earlier dated D1 snapshot, never target races."""
import argparse
import json
from pathlib import Path
from arvexq.prediction.learned_scenarios import fit_model


def train_models(source, target_date):
    details = source.get('details') if isinstance(source, dict) else None
    if not isinstance(details, list):
        raise ValueError('training source must have a details array')
    eligible = [d for d in details if isinstance(d, dict) and isinstance(d.get('date'), str)
                and d['date'] < target_date and (d.get('result') or {}).get('status') == '確定']
    models, errors = {}, {}
    for circuit in ('中央', '地方'):
        subset = [d for d in eligible if d.get('circuit') == circuit]
        try:
            models[circuit] = fit_model(subset, circuit=circuit)
        except ValueError as exc:
            errors[circuit] = str(exc)
    return models, errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--target-date', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    models, errors = train_models(json.loads(args.input.read_text(encoding='utf-8')),args.target_date)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(models,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    args.report.write_text(json.dumps({'trainedCircuits':sorted(models),
        'errors':errors,'source':'earlier-dated-frozen-d1-details',
        'targetDate':args.target_date,'researchOnly':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'trainedCircuits':sorted(models),'errors':errors},ensure_ascii=False))


if __name__=='__main__':
    main()
