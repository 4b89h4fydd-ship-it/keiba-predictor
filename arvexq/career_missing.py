"""Report unusable dated history without inventing finish statistics."""
from arvexq.career_analysis import analyze_career
from arvexq.history import normalize_run
from arvexq.prediction.past_performance import observed_runs, _date, _number
from arvexq.ingest.career_transport import recover_horse

KEYS = ('recentRaces', 'allPastRuns', 'pastRaces', 'history', 'runs')


def build_career_analysis(horse, race):
    cutoff = _date(race.get('date') or race.get('raceDate'))
    source = horse
    if cutoff is not None and isinstance(horse.get('careerArchive'), dict):
        source = recover_horse(horse, cutoff.isoformat())
    rows = observed_runs(source, race, limit=None)
    result = analyze_career([
        {'date': r.get('date'), 'distance': r.get('distance'),
         'course_type': r.get('surface'), 'track_condition': r.get('condition'),
         'finish_position': r.get('finish'), 'field_size': r.get('fieldSize')}
        for r in rows
    ])
    missing = set()
    seen = set()
    invalid = 0
    raw_present = any(isinstance(source.get(k), list) and source[k] for k in KEYS)
    for key in KEYS:
        values = source.get(key)
        if not isinstance(values, list):
            continue
        for original in values:
            if not isinstance(original, dict):
                continue
            r = normalize_run(original)
            at = _date(r.get('date'))
            if cutoff is None or at is None or at >= cutoff:
                continue
            field = _number(r.get('fieldSize'))
            finish = _number(r.get('finish'))
            problems = set()
            if field is None or field < 2 or not field.is_integer():
                problems.add('field_size')
            if finish is None or finish < 1 or not finish.is_integer() or (field is not None and finish > field):
                problems.add('finish_position')
            if not problems:
                continue
            fingerprint = (at.isoformat(), str(r.get('track') or ''),
                           str(r.get('distance') or ''), str(r.get('title') or ''),
                           str(r.get('finish') or ''), str(r.get('fieldSize') or ''))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            invalid += 1
            missing.update(problems)
    result['missing_fields'] = sorted(set(result['missing_fields']) | missing)
    result['unusable_dated_records'] = invalid
    result['unusable_count_scope'] = 'deduplicated-records-not-verified-career-starts'
    if invalid:
        result['data_limitation'] = 'partial'
        result['history_status'] = 'partially-analyzable' if rows else 'history-present-but-unusable'
    elif rows:
        result['history_status'] = 'dated-observed'
    elif cutoff is None:
        result['history_status'] = 'race-date-unverified'
    elif raw_present:
        result['history_status'] = 'no-eligible-dated-runs'
    else:
        result['history_status'] = 'no-runs'
    return result
