"""Audit evidence for the fixed 200 responsibilities; never infer completion."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

STATES = ('未着手','解析済','分離済','単体テスト成功','結合テスト成功','CI成功','main統合済','本番検証済')
WAITING_FOR_PREDICTION = '予想ロジック仕様待ち'
ROOT = Path(__file__).resolve().parents[1]

def audit(manifest):
    items = manifest.get('items') or []
    errors = []
    if len(items)!=200 or [x.get('id') for x in items]!=list(range(1,201)):
        errors.append('fixed IDs 1..200 must appear once in order')
    complete = 0
    for item in items:
        prefix=str(item.get('id'))+': '
        state=item.get('status')
        if manifest.get('version', 1) >= 2:
            owner = item.get('owner')
            if owner not in ('Codex', '別チャット', '共同'):
                errors.append(prefix+'explicit responsibility owner is required')
            dependency = item.get('prediction_logic_status')
            expected = '対象外' if owner == 'Codex' else WAITING_FOR_PREDICTION
            if dependency != expected:
                errors.append(prefix+'prediction boundary does not match owner')
        if state == WAITING_FOR_PREDICTION:
            if item.get('owner') not in ('別チャット', '共同'):
                errors.append(prefix+'prediction waiting state requires a prediction owner')
            continue
        if state not in STATES:
            errors.append(prefix+'unknown status');continue
        stage=STATES.index(state)
        if stage>=2:
            if not item.get('module') or not item.get('files') or not item.get('tests'):
                errors.append(prefix+'module, files and tests are required')
            for path in item.get('files',[])+item.get('tests',[]):
                if not (ROOT/path).is_file():errors.append(prefix+'missing '+path)
        evidence=item.get('evidence') or {}
        required=('unit','integration','ci_url','main_sha','production')
        for threshold,key in enumerate(required,3):
            if stage>=threshold and not evidence.get(key):errors.append(prefix+'missing '+key+' evidence')
        if stage>=5 and not evidence.get('commit_sha'):errors.append(prefix+'missing tested commit SHA')
        if stage==7 and all(evidence.get(k) for k in required+('commit_sha',)):
            complete+=1
    if manifest.get('completed')!=complete:errors.append('declared completed count differs from verified evidence')
    # Counts are descriptive only: no module or CI success promotes an item.
    state_counts = {status: sum(item.get('status') == status for item in items)
                    for status in STATES + (WAITING_FOR_PREDICTION,)}
    # Simplified reporting buckets must always reconcile to the fixed manifest.
    partial = sum(state_counts[s] for s in STATES[1:7])
    not_started = state_counts['未着手'] + state_counts[WAITING_FOR_PREDICTION]
    verification_needed = len(items) - complete - partial - not_started
    return {'total':len(items),'complete':complete,'remaining':200-complete,
            'partial':partial,'not_started_or_waiting':not_started,
            'unclassified':verification_needed,'state_counts':state_counts,
            'errors':errors,
            'verdict':'完了' if complete==200 and not errors else '未完了'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    result=audit(json.loads((ROOT/'docs/independence/requirements.json').read_text()))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result['errors'] or (args.require_complete and result['complete']!=200) else 0

if __name__=='__main__':raise SystemExit(main())
