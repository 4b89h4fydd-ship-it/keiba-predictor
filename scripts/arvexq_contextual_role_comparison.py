"""Paired chronological evaluation; candidate never changes production or seals."""
from __future__ import annotations
import copy
import base64
import gzip
import hashlib
import json
import os
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from arvexq.prediction.observed_model import apply_observed_marks
from arvexq.research.contextual_role_candidate import predict
from scripts.arvexq_role_mark_audit import api_json, API_BASE, finish_order


def restore_card(thin, snapshot_dir=Path('arvexq/ui/static/saved-snapshots')):
    """Day indexes intentionally omit history. Restore verified original inputs."""
    manifest_path=snapshot_dir/(str(thin.get('date'))+'.json')
    saved=None
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        ref=(manifest.get('races') or {}).get(str(thin.get('id')))
        if ref:
            path=snapshot_dir/str(ref['file'])
            if path.parent.resolve()!=snapshot_dir.resolve():raise ValueError('invalid snapshot path')
            envelope=json.loads(path.read_text())
            raw=gzip.decompress(base64.b64decode(envelope['gzipBase64'],validate=True))
            digest=hashlib.sha256(raw).hexdigest()
            if digest!=envelope['sha256'] or digest!=ref['sha256'] or len(raw)!=envelope['bytes']:
                raise ValueError('snapshot integrity mismatch')
            saved=json.loads(raw)
    source='immutable-repository-snapshot'
    if saved is None:
        response=api_json(API_BASE+'/api/race/'+urllib.parse.quote(str(thin['id']),safe=''))
        saved=response.get('detail')
        source='full-saved-api-replay'
    if not isinstance(saved,dict) or saved.get('id')!=thin.get('id') or saved.get('date')!=thin.get('date'):
        raise ValueError('restored race identity mismatch')
    saved=copy.deepcopy(saved)
    saved['result']=copy.deepcopy(thin.get('result'))
    saved['_comparisonInputSource']=source
    return saved


def stripped(detail):
    # Outcome payloads and prior predictions are not candidate inputs.
    return {k: copy.deepcopy(detail.get(k)) for k in
            ('id','date','circuit','track','distance','surface','condition','analysisMode','horses')}


def outcome(order, marks, axis):
    top = set(order[:3])
    def horse(mark):return next((n for n,m in marks.items() if m==mark),0)
    special = [n for n,m in marks.items() if m in ('☆','注')]
    return dict(win=int(horse('◎')==order[0]),axis=int(axis in top),
                second=int(horse('○') in order[:2]),third=int(horse('▲') in top),
                delta=int(horse('△')==order[2]),covered=sum(n in marks and bool(marks[n]) for n in top),
                specialHits=sum(n in top for n in special),specialPicks=len(special))


def evaluate(cards, predictor=predict):
    accepted=[]; skipped=Counter();sources=Counter();seen=set()
    for d in cards:
        identity=(d.get('date'),d.get('id'))
        if identity in seen:skipped['duplicate-race']+=1;continue
        seen.add(identity)
        order=finish_order(d)
        if len(order)<3: skipped['no-final-top3']+=1;continue
        r=stripped(d)
        if not isinstance(r.get('horses'),list): skipped['no-card']+=1;continue
        baseline=apply_observed_marks(copy.deepcopy(r))
        candidate=predictor(r)
        if not baseline['observedModelCoverage']['allObserved'] or not candidate['fullyObserved']:
            skipped['incomplete-observations']+=1;continue
        bmarks={int(h['horseNumber']):h.get('integratedEvaluation',{}).get('mark','') for h in baseline['horses']}
        if not set(order[:3]).issubset(bmarks): skipped['result-runner-missing']+=1;continue
        accepted.append(dict(id=d['id'],date=d['date'],circuit=d['circuit'],
            baseline=outcome(order,bmarks,baseline['honmeiDecision']['axisHorseNumber']),
            candidate=outcome(order,candidate['marks'],candidate['axisHorseNumber'])))
        sources[d.get('_comparisonInputSource','provided-card')]+=1
    # Split whole dates, never different races on the same day between periods.
    dates=sorted({d['date'] for d in accepted})
    cutoff=dates[max(0,int(len(dates)*.6))] if dates else None
    groups={}
    for circuit in ('中央','地方'):
        groups[circuit]={}
        for phase in ('early','holdout'):
            rows=[r for r in accepted if r['circuit']==circuit and ((r['date']>=cutoff)==(phase=='holdout'))]
            summary={'races':len(rows),'ids':[r['id'] for r in rows]}
            for kind in ('baseline','candidate'):
                sums={k:sum(r[kind][k] for r in rows) for k in ('win','axis','second','third','delta','covered','specialHits','specialPicks')}
                summary[kind]={**sums,'specialPrecision':sums['specialHits']/sums['specialPicks'] if sums['specialPicks'] else None}
            groups[circuit][phase]=summary
    failures=[]
    for circuit,phases in groups.items():
        hold=phases['holdout'];b,c=hold['baseline'],hold['candidate']
        if hold['races']<30: failures.append(circuit+': fewer than 30 paired holdout races')
        for key in ('win','axis','second','third','delta','covered'):
            if c[key]<b[key]: failures.append(circuit+': '+key+' regressed')
        if not any(c[k]>b[k] for k in ('win','axis','covered')): failures.append(circuit+': no primary improvement')
        if c['specialPicks'] < 10 or b['specialPicks'] < 10:
            failures.append(circuit+': special-mark precision evidence insufficient')
        elif c['specialPrecision']<b['specialPrecision']: failures.append(circuit+': special precision regressed')
    return dict(status='blocked' if failures else 'eligible-for-browser-parity-validation',
        gateFailures=failures,holdoutStart=cutoff,pairedRaces=len(accepted),skipped=dict(skipped),
        groups=groups,inputSources=dict(sources),warning='Retrospective replay of date-bounded histories. Not a sealed pre-off forecast or proof of future accuracy.',
        productionChanged=False)


def main():
    end=datetime.now(ZoneInfo('Asia/Tokyo')).date()-timedelta(days=1)
    days=int(os.getenv('ARVEXQ_COMPARISON_DAYS','28'));errors=[]
    def restored(thin):
        try:return restore_card(thin)
        except Exception as e:
            errors.append({'date':thin.get('date'),'id':thin.get('id'),'error':str(e)})
            return None
    def cards():
        for i in range(days-1,-1,-1):
            day=(end-timedelta(days=i)).isoformat()
            try:
                payload=api_json(API_BASE+'/api/day?'+urllib.parse.urlencode({'date':day,'details':'1'}))
                details=payload.get('details') or []
                if isinstance(details,dict):details=list(details.values())
                details=[d for d in details if isinstance(d,dict)]
                print('DAY',day,'cards',len(details),flush=True)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    for card in pool.map(restored,details):
                        if card is not None:yield card
            except Exception as e:
                errors.append({'date':day,'error':str(e)})
                print('DAY_ERROR',day,type(e).__name__,flush=True)
    result=evaluate(cards());result.update(fetchErrors=errors,start=(end-timedelta(days=days-1)).isoformat(),end=end.isoformat())
    if errors:result['status']='blocked';result['gateFailures'].append('Incomplete retrieval window')
    Path('contextual-role-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('CONTEXTUAL_ROLE_REPORT='+json.dumps(result,ensure_ascii=False,separators=(',',':')))
    if result['status']=='blocked':print('PRODUCTION_REPLACEMENT_BLOCKED')


if __name__=='__main__':main()
