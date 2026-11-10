"""Same-cohort model comparison. Development only; no deployment or odds writes."""
import argparse
import json
from pathlib import Path
from arvexq.research.ranking_challenger import prepare_races, train_one

VARIANTS = (
    ('ability', 'ability', 'lambdarank', 'graded'),
    ('ana', 'ana', 'lambdarank', 'graded'),
    ('pointwise', 'ability', 'pointwise', 'graded'),
    ('xgboost', 'ability', 'xgboost', 'graded'),
    ('winner', 'ability', 'lambdarank', 'win'),
    ('podium', 'ability', 'lambdarank', 'podium'),
)


def benchmark(rows, out):
    reports = []
    for circuit in ('jra', 'nar'):
        ids = ({r['raceId'] for r in prepare_races(rows, circuit, 'ability')} &
               {r['raceId'] for r in prepare_races(rows, circuit, 'ana')})
        cohort = [r for r in rows if r['raceId'] in ids]
        for name, head, learner, target in VARIANTS:
            try:
                result = train_one(cohort, circuit, head, out/name, learner=learner,
                                   target=target, development_only=True)
                result['name'] = name
                # Scores stay inspectable alongside the fitted estimator.
                result['lightgbmLambdaMARTAlias'] = name == 'ability'
            except ValueError as exc:
                result = {'name': name, 'circuit': circuit, 'status': 'insufficient-data',
                          'reason': str(exc), 'productionEligible': False}
            reports.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out/'benchmark.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2))
    return reports


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('frozen_jsonl'); p.add_argument('output_dir')
    a = p.parse_args()
    benchmark([json.loads(line) for line in Path(a.frozen_jsonl).read_text().splitlines() if line], Path(a.output_dir))
