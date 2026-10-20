"""Verify repaired D1 data with the same final-result contract as the app."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from arvexq.results.state import result_state


def verify_history(report: dict, day: dict) -> dict:
    detail_rows=[d for d in day.get('details',[]) if isinstance(d,dict)]
    by={str(d.get('id') or ''):d for d in detail_rows}
    expected=int(report.get('races') or 0)
    labels=report.get('labels') or {}
    expected_ids=set(labels) if isinstance(labels,dict) else set()
    observed_ids={rid for rid in by if rid}
    missing_ids=sorted(expected_ids-observed_ids)
    extra_ids=sorted(observed_ids-expected_ids) if expected_ids else []
    duplicate_ids=sorted(rid for rid in observed_ids if sum(
        str(d.get('id') or '')==rid for d in detail_rows)>1)
    day_ids={str(r.get('id') or '') for r in day.get('races',[]) if isinstance(r,dict) and r.get('id')}
    missing_summaries=sorted(expected_ids-day_ids) if expected_ids and 'races' in day else []
    unresolved=set(report.get('missing_card') or [])|set(report.get('missing_result') or [])|set(report.get('missing_payout') or [])
    failures=[]
    for rid,d in by.items():
        if rid in unresolved:
            continue
        result_ok,payout_ok,status=result_state(d)
        if not result_ok or not payout_ok:
            failures.append({'raceId':rid,'resultComplete':result_ok,'payoutComplete':payout_ok,'status':status})
    complete=(len(by)==expected and not failures and not missing_ids
              and not extra_ids and not duplicate_ids and not missing_summaries
              and (not expected_ids or len(expected_ids)==expected))
    return {'ok':complete,'details':len(by),'expected':expected,
            'unresolved':len(unresolved),'unexpectedIncomplete':failures,
            'missingRaceIds':missing_ids,'unexpectedRaceIds':extra_ids,
            'duplicateDetailIds':duplicate_ids,'missingSummaryRaceIds':missing_summaries}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--report',required=True);ap.add_argument('--day',required=True);ap.add_argument('--output')
    args=ap.parse_args();report=json.loads(Path(args.report).read_text());day=json.loads(Path(args.day).read_text())
    verdict=verify_history(report,day)
    if args.output:Path(args.output).write_text(json.dumps(verdict,ensure_ascii=False,indent=2))
    print('HISTORY_D1_VERIFICATION',json.dumps(verdict,ensure_ascii=False))
    if not verdict['ok']:raise SystemExit(1)
if __name__=='__main__':main()
