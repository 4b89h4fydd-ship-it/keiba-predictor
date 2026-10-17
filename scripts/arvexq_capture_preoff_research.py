#!/usr/bin/env python3
"""Research-only pre-off candidate capture from an already trained, dated model.

Offline input only; no D1 writes, no production bet recommendations.
Model training evidence is caller-supplied and must be independently audited.
"""
import argparse
import json
from pathlib import Path
from arvexq.prediction.new_forecast import build_forecast
from arvexq.backtest.freeze_research_candidate import freeze_research_candidate


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--race-json', type=Path, required=True)
    parser.add_argument('--model-json', type=Path, required=True)
    parser.add_argument('--receipt-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    race = json.loads(args.race_json.read_text(encoding='utf-8'))
    model = json.loads(args.model_json.read_text(encoding='utf-8'))
    if not isinstance(race, dict) or not isinstance(model, dict):
        parser.error('race and model must be JSON objects')
    if race.get('result') or race.get('analysisType') == 'retrospective':
        parser.error('result-bearing or retrospective race cannot be captured')
    if not isinstance(race.get('date'), str) or not isinstance(model.get('training'), dict):
        parser.error('dated race and documented training required')
    if not model['training'].get('lastDate') or model['training']['lastDate'] >= race['date']:
        parser.error('model training must end strictly before race day')
    prediction = build_forecast(race, model)
    if prediction.get('analysisType') != 'preoff-candidate':
        parser.error('candidate no longer before post')
    receipt = freeze_research_candidate(race, prediction['recommendedBetPlan'], args.receipt_dir)
    print(json.dumps({'receipt': str(receipt), 'raceId': race['id'],
                      'researchOnly': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
