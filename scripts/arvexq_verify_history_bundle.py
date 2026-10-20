"""Verify repaired D1 data with the same final-result contract as the app."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from arvexq.components.item_073.state import result_state


def verify_history(report: dict, day: dict) -> dict:
    by={str(d.get('id') or ''):d for d in day.get('details',[]) if isinstance(d,dict)}
    expected=int(report.get('races') or 0)
    unresolved=set(report.get('missing_card') or [])|set(report.get('missing_result') or [])|set(report.get('missing_payout') or [])
    failures=[]
    for rid,d in by.items():
        if rid in unresolved:
            continue
        result_ok,payout_ok,status=result_state(d)
        if not result_ok or not payout_ok:
            failures.append({'raceId':rid,'resultComplete':result_ok,'payoutComplete':payout_ok,'status':status})
    return {'ok':len(by)>=expected and not failures,'details':len(by),'expected':expected,
            'unresolved':len(unresolved),'unexpectedIncomplete':failures}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--report',required=True);ap.add_argument('--day',required=True);ap.add_argument('--output')
    args=ap.parse_args();report=json.loads(Path(args.report).read_text());day=json.loads(Path(args.day).read_text())
    verdict=verify_history(report,day)
    if args.output:Path(args.output).write_text(json.dumps(verdict,ensure_ascii=False,indent=2))
    print('HISTORY_D1_VERIFICATION',json.dumps(verdict,ensure_ascii=False))
    if not verdict['ok']:raise SystemExit(1)
if __name__=='__main__':main()
