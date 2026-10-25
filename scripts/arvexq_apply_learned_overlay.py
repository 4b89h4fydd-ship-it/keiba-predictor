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
from arvexq.pipeline.persisted_inputs import may_create_prerace_prediction
from arvexq.prediction.prerace_archive import sealed_lock
from arvexq.prediction.fusion_source_composer import assemble_fusion_inputs
from arvexq.forecast.engine import build_prediction
from arvexq.forecast.marks import generate_marks
from arvexq.forecast.tickets import generate_tickets


# Retired mutable presentation fields. Do not touch immutable pre-off records,
# official result evidence, cards, historical runs or versioned audit archives.
LEGACY_ACTIVE_FIELDS = (
    'aiEvaluation', 'pacePrediction', 'predictionStatus',
    'predictionModelVersion', 'markEngineVersion', 'markDefinitions',
    'gradeDefinitions', 'scenarioAnalysis', 'honmeiDecision',
    'recommendedBetPlan', 'forecastText', 'probabilityModelStatus',
    'productionEligible', 'prediction', 'predictionMarks',
    'recommendedBets', 'tickets', 'buyList', 'bets',
)


def without_legacy_presentation(detail):
    row = dict(detail)
    for key in LEGACY_ACTIVE_FIELDS:
        row.pop(key, None)
    row['predictionStatus'] = 'new-model-unavailable'
    row['recommendedBetPlan'] = {
        'decision': '見送り', 'items': [],
        'reason': '新方式の学習済みモデルを確認できないため旧予想を表示しない',
    }
    row['legacyPresentationDisabled'] = True
    horses = []
    for horse in row.get('horses') or []:
        if not isinstance(horse, dict):
            horses.append(horse)
            continue
        horse = dict(horse)
        horse.pop('integratedEvaluation', None)
        # The old UI also reads marks directly from horse rows.
        for key in ('predMark', 'mark', '印', 'honmeiRole'):
            horse.pop(key, None)
        horses.append(horse)
    if isinstance(row.get('horses'), list):
        row['horses'] = horses
    return row


def apply(bundle, models, *, now=None):
    out = dict(bundle)
    details = []
    changed, skipped = [], {}
    fused, fusion_errors = [], {}
    for detail in bundle.get('details', []):
        if not isinstance(detail, dict) or not detail.get('id'):
            details.append(detail)
            continue
        # An already sealed original is immutable. Never overwrite that
        # record, even when the new method weights are different.
        if sealed_lock(detail):
            details.append(detail)
            skipped[str(detail['id'])] = 'already-frozen-preoff-original-preserved'
            continue
        # Reuse this EXACT existing D1 publication step for the trained
        # five-method fusion. No added endpoint or alternative data source.
        fusion = ((models.get('fusion') or {}).get(detail.get('circuit'))
                  if isinstance(models, dict) else None)
        if fusion and may_create_prerace_prediction(detail):
            try:
                sources = assemble_fusion_inputs(
                    detail, fusion['models'], fusion['calibration'], now=now)
                candidate = dict(detail)
                candidate['fusionInputs'] = {
                    'opinions': sources['opinions'],
                    'calibration': sources['calibration'],
                    'odds': sources.get('odds'),
                    'capturedAt': sources['capturedAt'],
                }
                pred = build_prediction(candidate, now=now)
                if not isinstance(pred, dict) or pred.get('predictionStatus') != 'ready':
                    raise ValueError('five-method forecast cannot be verified before off')
                marks = generate_marks(pred)
                tickets = generate_tickets(pred, marks, race=detail)
                if len(marks) != 5 or not isinstance(tickets, list):
                    raise ValueError('fusion marks or tickets contract incomplete')
                ready = dict(detail)
                ready['predictionStatus'] = 'ready'
                ready['predictionModelVersion'] = pred['modelVersion']
                ready['prediction'] = pred
                ready['predictionMarks'] = marks
                ready['recommendedBets'] = tickets
                ready['forecastText'] = pred['forecastText']
                # Save compact, immutable before-off per-method winner votes
                # for later genuine settlement. Do NOT leak the full ML model
                # or bulky all-triple opinion arrays into the D1 racecard.
                ready['fusionMethodPreoffReceipt'] = {
                    'raceId': sources['raceId'], 'raceDate': sources['raceDate'],
                    'circuit': sources['circuit'],
                    'capturedAt': sources['capturedAt'],
                    'scheduledOffAt': sources['scheduledOffAt'],
                    'sourceKind': 'preoff-method-opinions-unsealed',
                    'sourceVersions': sources['sourceVersions'],
                    'roster': sources['roster'],
                    'arms': {name: {field: opinion[field] for field in (
                          'modelVersion','evidenceId','raceId','capturedAt','win','top3')}
                          for name, opinion in sources['opinions'].items()},
                }
                labels = {row['horseNumber']: row['mark'] for row in marks}
                ready['horses'] = []
                for horse in detail.get('horses') or []:
                    if not isinstance(horse, dict):
                        ready['horses'].append(horse)
                        continue
                    runner = dict(horse)
                    # Never retain an obsolete runner mark for an unmarked
                    # starter; only this prediction's five marks are active.
                    for key in ('predMark', 'mark', '印', 'honmeiRole'):
                        runner.pop(key, None)
                    if runner.get('horseNumber') in labels:
                        runner['predMark'] = labels[runner['horseNumber']]
                    ready['horses'].append(runner)
                details.append(ready)
                fused.append(str(detail['id']))
                continue
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                fusion_errors[str(detail['id'])] = type(exc).__name__ + ': ' + str(exc)
        # From the user-approved replacement cutoff onward, do not
        # run the obsolete learned-forecast fallback at all. A missing
        # five-method prediction is explicitly unavailable, not a
        # different model's unverified candidate.
        if str(detail.get('date') or '') >= '2026-10-23':
            if not may_create_prerace_prediction(detail):
                details.append(detail)
                skipped[str(detail['id'])] = 'post-off-original-preserved'
            else:
                details.append(without_legacy_presentation(detail))
                skipped[str(detail['id'])] = (
                    'fusion-inputs-unavailable' if not fusion
                    else 'fusion-inputs-invalid')
            continue
        # Preserve historical sealed originals and keep the pre-cutoff
        # research behavior only for historical diagnostic compatibility.
        circuit = detail.get('circuit')
        model = models.get(circuit)
        if not isinstance(model, dict):
            skipped[str(detail['id'])] = 'no-earlier-circuit-model'
            details.append(without_legacy_presentation(detail))
            continue
        if (model.get('training') or {}).get('lastDate', '9999') >= str(detail.get('date') or ''):
            skipped[str(detail['id'])] = 'training-date-not-earlier'
            details.append(without_legacy_presentation(detail))
            continue
        # A prefetched race can pass its scheduled start while heavy D1
        # reads/learning are still running. Do not replace its preserved
        # original with a newly generated post-off learned forecast. The
        # public projection independently hides unapproved legacy opinions.
        if (str(detail.get('date') or '') >= '2026-10-23'
                and not may_create_prerace_prediction(detail)):
            details.append(detail)
            skipped[str(detail['id'])] = 'post-off-original-preserved'
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
            details.append(without_legacy_presentation(detail))
    out['details'] = details
    meta = dict(out.get('meta') or {})
    meta['learnedForecastOverlayCount'] = len(changed)
    meta['learnedForecastOverlayResearchOnly'] = True
    meta['empiricalFusionPreoffReadyCount'] = len(fused)
    out['meta'] = meta
    return out, {'overlaid': changed, 'skipped': skipped,
                 'fusionPublished': fused, 'fusionErrors': fusion_errors,
                 'productionTicketAccuracyVerified': False}


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
    print('FUSION_PREFETCH_READY',len(report['fusionPublished']),
          'fusion_errors',len(report['fusionErrors']),
          'legacy_research_only',len(report['overlaid']))


if __name__ == '__main__':
    main()
