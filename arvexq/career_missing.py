"""Report unusable dated history without inventing finish statistics.

Two independent questions are answered here and must never be conflated:

* acquisition: was the whole pre-race career actually fetched?  Only explicit,
  race-date-bound evidence (``_careerHistoryAudit`` matching a reported start
  count exactly) can prove this.  A list named ``allPastRuns`` or a non-empty
  history is not proof; without evidence the state is ``unverified``.
* field completeness: are the fetched runs analysable (finish/field size etc.)?

``data_limitation == 'complete'`` therefore requires both.
"""
from arvexq.career_analysis import analyze_career
from arvexq.history import normalize_run
from arvexq.ingest.full_career import merge_career, date_key
from arvexq.prediction.past_performance import observed_runs, _date, _number
from arvexq.ingest.career_transport import recover_horse

KEYS = ('recentRaces', 'allPastRuns', 'pastRaces', 'history', 'runs')
AUDIT_VERSION = 'arvexq-career-coverage-v1'


def _candidates(source):
    out = []
    for key in KEYS:
        values = source.get(key)
        if isinstance(values, list):
            out.extend(v for v in values if isinstance(v, dict))
    return out


def _acquisition(source, cutoff, eligible_count, recovery_error):
    """Return (status, evidence). status: complete|partial|unverified|race-date-unverified."""
    audit = source.get('_careerHistoryAudit')
    audit = audit if isinstance(audit, dict) else {}
    evidence = {
        'source': '_careerHistoryAudit' if audit else None,
        'auditVersion': audit.get('version'),
        'requestedAtRaceDate': audit.get('requestedAtRaceDate'),
        'reportedStarts': audit.get('reportedStarts'),
        'auditObservedRuns': audit.get('observedRuns'),
        'currentEligibleRuns': eligible_count,
        'failedProviders': list(audit.get('failedProviders') or []),
        'reason': None,
    }
    if cutoff is None:
        evidence['reason'] = 'race-date-unknown'
        return 'race-date-unverified', evidence
    if recovery_error:
        evidence['reason'] = 'career-archive-recovery-failed'
        return 'partial', evidence
    if not audit:
        evidence['reason'] = 'no-acquisition-evidence'
        return 'unverified', evidence
    if audit.get('version') != AUDIT_VERSION or audit.get('requestedAtRaceDate') != cutoff.isoformat():
        evidence['reason'] = 'audit-not-bound-to-this-race-date'
        return 'unverified', evidence
    reported = audit.get('reportedStarts')
    failed = bool(audit.get('failedProviders'))
    if audit.get('paginationComplete') is False:
        evidence['reason'] = 'pagination-incomplete'
        return 'partial', evidence
    if not isinstance(reported, int) or isinstance(reported, bool) or reported < 0:
        evidence['reason'] = 'provider-fetch-failed' if failed else 'reported-starts-unknown'
        return ('partial' if failed else 'unverified'), evidence
    if eligible_count < reported:
        evidence['reason'] = 'fewer-runs-than-reported-starts'
        return 'partial', evidence
    if eligible_count > reported:
        evidence['reason'] = 'more-runs-than-reported-starts'
        return 'unverified', evidence
    if audit.get('complete') is not True:
        evidence['reason'] = 'audit-not-marked-complete'
        return 'unverified', evidence
    evidence['reason'] = 'reported-starts-matched'
    return 'complete', evidence


def build_career_analysis(horse, race):
    race = race if isinstance(race, dict) else {}
    cutoff = _date(race.get('date') or race.get('raceDate'))
    source = horse
    recovery_error = None
    if cutoff is not None and isinstance(horse.get('careerArchive'), dict):
        try:
            source = recover_horse(horse, cutoff.isoformat())
        except ValueError as exc:
            # A broken sidecar means older starts are not available: keep the
            # visible rows but never report the career as fully acquired.
            recovery_error = str(exc)
            source = {k: v for k, v in horse.items() if k != 'careerArchive'}
    rows = observed_runs({k: v for k, v in source.items() if k != 'careerArchive'}, race, limit=None)
    result = analyze_career([
        {'date': r.get('date'), 'distance': r.get('distance'),
         'course_type': r.get('surface'), 'track_condition': r.get('condition'),
         'finish_position': r.get('finish'), 'field_size': r.get('fieldSize')}
        for r in rows
    ])
    candidates = _candidates(source)
    raw_present = bool(candidates)
    # Same identity rule as observed_runs/audit_career: one start per date,
    # strictly before the race date.  Undated/same-day/future rows are excluded,
    # which is not the same thing as an acquisition gap.
    eligible = merge_career([], candidates, cutoff.isoformat()) if cutoff else []
    missing = set()
    invalid = 0
    for original in eligible:
        r = normalize_run(original)
        field = _number(r.get('fieldSize'))
        finish = _number(r.get('finish'))
        problems = set()
        if field is None or field < 2 or not field.is_integer():
            problems.add('field_size')
        if finish is None or finish < 1 or not finish.is_integer() or (field is not None and finish > field):
            problems.add('finish_position')
        if problems:
            invalid += 1
            missing.update(problems)
    excluded = sum(1 for c in candidates
                   if cutoff is None or not date_key(c.get('date') or c.get('raceDate') or c.get('日付'))
                   or date_key(c.get('date') or c.get('raceDate') or c.get('日付')) >= cutoff.isoformat())

    acquisition, evidence = _acquisition(source, cutoff, len(eligible), recovery_error)
    result['missing_fields'] = sorted(set(result['missing_fields']) | missing)
    result['unusable_dated_records'] = invalid
    result['unusable_count_scope'] = 'deduplicated-pre-race-dated-starts'
    result['eligible_dated_runs'] = len(eligible)
    result['excluded_not_pre_race_records'] = excluded
    result['acquisition_status'] = acquisition
    result['acquisition_evidence'] = evidence
    result['career_complete'] = acquisition == 'complete'
    if not rows:
        fields = 'no-analyzable-runs'
    elif result['missing_fields'] or invalid:
        fields = 'missing-fields'
    else:
        fields = 'complete'
    result['field_completeness'] = fields

    # Backward-compatible fields.  'complete' now requires verified acquisition.
    if not rows and not invalid:
        result['data_limitation'] = 'no_runs'
    elif acquisition == 'complete' and fields == 'complete':
        result['data_limitation'] = 'complete'
    else:
        result['data_limitation'] = 'partial'
    if invalid:
        result['history_status'] = 'partially-analyzable' if rows else 'history-present-but-unusable'
    elif rows:
        result['history_status'] = 'dated-observed'
    elif cutoff is None:
        result['history_status'] = 'race-date-unverified'
    elif raw_present:
        result['history_status'] = 'no-eligible-dated-runs'
    else:
        result['history_status'] = 'no-runs'

    # One summary state shared by API, horse detail and all-runner diagnosis.
    if cutoff is None:
        state = 'race-date-unverified'
    elif not eligible and acquisition != 'complete':
        state = 'no-history'
    elif eligible and not rows:
        state = 'history-present-but-unusable'
    elif acquisition == 'partial':
        state = 'partially-acquired'
    elif acquisition != 'complete':
        state = 'acquisition-unverified'
    elif not eligible:
        state = 'complete-no-starts'
    elif fields != 'complete':
        state = 'complete-with-missing-fields'
    else:
        state = 'complete'
    result['career_state'] = state
    return result
