#!/usr/bin/env python3
"""Apply the learned forecast as the visible candidate, preserving sealed originals.

Never treat an uncalibrated scenario ticket as a production recommendation.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from arvexq.prediction.new_forecast import build_forecast


def apply(bundle, models):
    out = dict(bundle)
    details = []
    changed, skipped = [], {}
    for detail in bundle.get('details', []):
        if not isinstance(detail, dict) or not detail.get('id'):
            details.append(detail)
            continue
        circuit = detail.get('circuit')
        model = models.get(circuit)
        if not isinstance(model, dict):
            skipped[str(detail['id'])] = 'no-earlier-circuit-model'
            details.append(detail)
            continue
        if (model.get('training') or {}).get('lastDate', '9999') >= str(detail.get('date') or ''):
            skipped[str(detail['id'])] = 'training-date-not-earlier'
            details.append(detail)
            continue
        try:
            updated = build_forecast(detail, model)
            # Never rewrite an authentic immutable pre-off original.
            for key in ('preRacePrediction', 'preRaceBet', 'preRaceBetPlan'):
                if key in detail:
                    updated[key] = detail[key]
            # Do not promote uncalibrated bets as recommendations.
            if updated.get('recommendedBetPlan', {}).get('items'):
                raise ValueError('uncalibrated ticket promotion prohibited')
            details.append(updated)
            changed.append(str(detail['id']))
        except Exception as exc:
            skipped[str(detail['id'])] = type(exc).__name__ + ': ' + str(exc)
            details.append(detail)
    out['details'] = details
    meta = dict(out.get('meta') or {})
    meta['learnedForecastOverlayCount'] = len(changed)
    meta['learnedForecastOverlayResearchOnly'] = True
    out['meta'] = meta
    return out, {'overlaid': changed, 'skipped': skipped, 'productionTicketAccuracyVerified': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--models', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    payload, report = apply(json.loads(args.bundle.read_text(encoding='utf-8')),
                            json.loads(args.models.read_text(encoding='utf-8')))
    args.out.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('LEARNED_FORECAST_OVERLAY',len(report['overlaid']),'skipped',len(report['skipped']))


if __name__ == '__main__':
    main()
