"""Read-only official recovery for immutable snapshots lacking historical gaps.

Never writes D1, predictions, original snapshots or deployment state. The same
newly verified prior observations feed both baseline and challenger.
"""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import os
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from arvexq.core.runner_status import is_inactive_runner
from arvexq.ingest.full_career import merge_career
from arvexq.prediction.observed_model import _course_history,rank_observed
from arvexq.prediction.past_performance import observed_runs
from arvexq.research.mineta_field_proxy import score_race
from scripts.arvexq_contextual_role_comparison import evaluate


def load_inputs(root,end):
    for file in sorted(root.glob('*.json')):
        envelope=json.loads(file.read_text())
        if 'gzipBase64' not in envelope:continue
        raw=gzip.decompress(base64.b64decode(envelope['gzipBase64'],validate=True))
        if len(raw)!=envelope['bytes'] or hashlib.sha256(raw).hexdigest()!=envelope['sha256']:
            raise ValueError('immutable input digest mismatch: '+file.name)
        detail=json.loads(raw)
        if str(detail.get('date') or '')>end:continue
        yield detail


def main():
    os.environ.setdefault('ARVEXQ_BOOTSTRAP_WARM','0')
    os.environ.setdefault('ARVEXQ_DATA_CORE','0')
    os.environ.setdefault('NAR_RESULT_TIMEOUT_SEC','3.5')
    import app
    from arvexq.databanks.legacy_bridge import _nar_official_past_result_adapter,_jra_official_prior_result_adapter
    end=(datetime.now(ZoneInfo('Asia/Tokyo')).date()-timedelta(days=1)).isoformat()
    output=Path(os.getenv('ARVEXQ_REPLAY_OUTPUT','/tmp/arvexq-contextual-official-replay'))
    output.mkdir(parents=True,exist_ok=True)
    counts=Counter();locks={};guard=threading.Lock();cache={}
    def cached(key,fn):
        with guard:lock=locks.setdefault(key,threading.Lock())
        with lock:
            if key not in cache:cache[key]=fn()
            return copy.deepcopy(cache[key])
    def nar_fetch(d):
        key=('nar',d['date'],d['track'],int(d['raceNumber']))
        return cached(key,lambda:app._nar_official_result_fast({**d,'horses':[]}))
    def jra_parse(cname,base=None,*,strict_errors=False):
        return cached(('jra',cname),lambda:app._jra_parse_result(cname,base,strict_errors=strict_errors))
    namespace=vars(app).copy();namespace['_nar_official_result_fast']=nar_fetch
    namespace['_jra_parse_result']=jra_parse
    nar=_nar_official_past_result_adapter(namespace)
    jra=_jra_official_prior_result_adapter(namespace)
    cards=sorted(load_inputs(Path('arvexq/ui/static/saved-snapshots'),end),key=lambda d:(d['circuit']=='中央',d['date'],d['id']))
    ready=[]
    for d in cards:
        active=[h for h in d.get('horses',[]) if not is_inactive_runner(h)]
        histories=[_course_history(h,d) for h in active]
        if len(active)<5 or len(score_race(histories,d))!=len(active):
            counts[(d['circuit'],'incomplete-position')]+=1;continue
        ready.append(d)
    print('OFFICIAL_REPLAY_CANDIDATES',len(ready),'of',len(cards),flush=True)
    # Interleave whole-date buckets deterministically, independent of outcomes.
    # A bounded run must not examine only the first venue/date in the archive.
    buckets={}
    for d in ready:buckets.setdefault((d['circuit']=='中央',d['date']),[]).append(d)
    ready=[bucket[i] for central in (False,True)
           for i in range(max((len(v) for k,v in buckets.items() if k[0]==central),default=0))
           for key,bucket in sorted(buckets.items()) if key[0]==central and i<len(bucket)]
    def recover(d):
        filename=hashlib.sha256(d['id'].encode()).hexdigest()+'.json'
        checkpoint=output/filename
        if checkpoint.exists():return json.loads(checkpoint.read_text())
        circuit=d['circuit'];active=[h for h in d.get('horses',[]) if not is_inactive_runner(h)]
        try:
            if circuit=='地方':result=nar_fetch(d)
            else:
                run={k:d[k] for k in ('date','track','distance','surface','raceNumber') if k in d}
                parsed=app._jra_resolve_prior_results(active[0],run)
                result=(parsed or {}).get('result')
            if not result or len(result.get('finishers') or [])<3:
                return {'id':d['id'],'circuit':circuit,'failure':'official-target-result-unavailable'}
            def horse(h):
                supplement=(nar if circuit=='地方' else jra)(h,d,5) or {}
                q=copy.deepcopy(h)
                runs=merge_career(h.get('allPastRuns') or h.get('recentRaces'),supplement.get('recentRaces'),d['date'])
                q['allPastRuns']=runs;q['recentRaces']=runs[:5]
                return q
            # Bounded total concurrency; adapters reuse official parsed-race caches.
            with ThreadPoolExecutor(max_workers=4) as pool:horses=list(pool.map(horse,active))
            out={k:copy.deepcopy(d.get(k)) for k in ('id','date','circuit','track','distance','surface','condition','analysisMode')}
            out.update(horses=horses,result=result,_comparisonInputSource='immutable-snapshot-plus-verified-official-prior-results')
            matched=len(rank_observed(horses,out))
            out['_officialRecovery']={'active':len(active),'scored':matched}
            checkpoint.write_text(json.dumps(out,ensure_ascii=False))
            return out
        except Exception as exc:return {'id':d['id'],'circuit':circuit,'failure':type(exc).__name__+': '+str(exc)[:250]}
    started=time.monotonic();budget=float(os.getenv('ARVEXQ_OFFICIAL_REPLAY_SECONDS','480'))
    source_failures=Counter()
    def recovered():
        for i,d in enumerate(ready):
            if time.monotonic()-started>budget:
                counts[('all','time-budget-unprocessed')]+=len(ready)-i
                break
            if source_failures[d['circuit']]>=2:
                counts[(d['circuit'],'source-circuit-open')]+=1
                continue
            out=recover(d)
            if out.get('failure'):
                counts[(d['circuit'],out['failure'])]+=1
                if out['failure'].startswith(('URLError','HTTPError')):source_failures[d['circuit']]+=1
                print('RECOVERY_FAILED',d['id'],out['failure'],flush=True)
                continue
            counts[(d['circuit'],'recovered-cards')]+=1
            print('RECOVERY',i+1,len(ready),d['id'],out['_officialRecovery'],flush=True)
            yield out
    report=evaluate(recovered())
    if any('source-circuit-open' in str(k) or 'time-budget-unprocessed' in str(k) for k in counts):
        report['status']='blocked'
        report['gateFailures'].append('Official recovery source failure or execution budget leaves unprocessed inputs')
    report.update(officialRecoveryCounts={str(k):v for k,v in counts.items()},checkpointDirectory=str(output),
        immutableInputCards=len(cards),positionCompleteCandidates=len(ready))
    (output/'comparison-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('OFFICIAL_CONTEXTUAL_REPORT='+json.dumps(report,ensure_ascii=False,separators=(',',':')),flush=True)


if __name__=='__main__':main()
