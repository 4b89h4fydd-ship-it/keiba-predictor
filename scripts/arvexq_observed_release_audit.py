#!/usr/bin/env python3
"""Paired source-hashed replay and immutable-original audit. Never writes D1."""
from __future__ import annotations
import argparse, copy, hashlib, json, os, subprocess
from collections import defaultdict
from pathlib import Path
from arvexq.prediction.observed_model import rank_observed, apply_observed_marks
from arvexq.prediction.prerace_archive import sealed_lock, post_at
from scripts.arvexq_prerace_bet_integrity import has_valid_original

RACE_KEYS=('id','circuit','date','track','raceNumber','title','distance','surface','condition','weather',
           'fieldSize','analysisMode','scheduledStartTime','startTime','opponentLevel')
HORSE_KEYS=('id','horseNumber','frameNumber','name','status','scratched','withdrawn','age','sex',
            'recentRaces','allPastRuns','pastRaces','history','runs','careerArchive','careerTransport')
def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def inputs(d):
    # Positive allowlist excludes current result, payouts, market, body-weight,
    # old scores/marks, learned outputs and stored ticket receipts.
    out={k:copy.deepcopy(d[k]) for k in RACE_KEYS if k in d}
    out['horses']=[{k:copy.deepcopy(h[k]) for k in HORSE_KEYS if k in h} for h in d.get('horses',[])]
    return out

def hit(kind,combo,order):
    c=list(combo);t=order[:3]
    if kind=='単勝':return c==t[:1]
    if kind=='馬単':return c==t[:2]
    if kind=='馬連':return len(c)==2 and sorted(c)==sorted(t[:2])
    if kind in ('複勝','ワイド'):return bool(c) and all(n in t for n in c)
    if kind=='3連複':return len(c)==3 and sorted(c)==sorted(t)
    if kind=='3連単':return len(c)==3 and c==t
    return False

def ticket_metrics(plan,order):
    kinds={}
    for item in (plan or {}).get('items',[]):
        kind=item.get('kind','');combos=item.get('combos') or []
        if not combos:continue
        item_hit=any(hit(kind,c,order) for c in combos)
        kinds[kind]={'offered':True,'hit':item_hit or kinds.get(kind,{}).get('hit',False),
                     'points':len(combos)+kinds.get(kind,{}).get('points',0)}
    return kinds

def mark_metrics(marks,order):
    return [{'horseNumber':no,'mark':m,'finish':order.index(no)+1 if no in order else None}
            for no,m in marks.items() if m]

def replay(details,source):
    env={**os.environ,'ARVEXQ_REPLAY_SOURCE':str(source)}
    r=subprocess.run(['node','scripts/arvexq_observed_replay.js'],input=json.dumps(details),text=True,
                     capture_output=True,env=env,check=True,timeout=180)
    return {row['id']:row for row in json.loads(r.stdout)}

def summarize(rows,lane):
    out={}
    for circuit in sorted({r['circuit'] for r in rows}):
        group=[r for r in rows if r['circuit']==circuit];valid=[r for r in group if r[lane] is not None]
        m={'races':len(group),'availableForecasts':len(valid),'missingForecasts':len(group)-len(valid),
           'honmeiRaces':0,'honmeiWins':0,'honmeiPodium':0,'tickets':{},'marks':{}}
        for r in valid:
            x=r[lane];hon=next((z for z in x['marks'] if z['mark']=='◎'),None)
            if hon:
                m['honmeiRaces']+=1;m['honmeiWins']+=hon['finish']==1
                m['honmeiPodium']+=hon['finish'] is not None and hon['finish']<=3
            for z in x['marks']:
                a=m['marks'].setdefault(z['mark'],{'assigned':0,'wins':0,'top2':0,'top3':0})
                a['assigned']+=1;a['wins']+=z['finish']==1
                a['top2']+=z['finish'] is not None and z['finish']<=2
                a['top3']+=z['finish'] is not None and z['finish']<=3
            for k,v in x['tickets'].items():
                a=m['tickets'].setdefault(k,{'offeredRaces':0,'hitRaces':0,'totalPoints':0})
                a['offeredRaces']+=1;a['hitRaces']+=v['hit'];a['totalPoints']+=v['points']
        for a in m['tickets'].values():
            a['offeredHitRate']=a['hitRaces']/a['offeredRaces'] if a['offeredRaces'] else None
            a['allTargetRacesHitRate']=a['hitRaces']/len(group) if group else None
        out[circuit]=m
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',action='append',required=True)
    ap.add_argument('--baseline-source',required=True);ap.add_argument('--official-results')
    ap.add_argument('--output',required=True);args=ap.parse_args()
    records={};raw_hash={}
    for folder in args.input_dir:
        for p in Path(folder).glob('*.json'):
            if not p.name.startswith(('jra-','nar-')):continue
            b=p.read_bytes();d=json.loads(b).get('detail')
            if d:records[d['id']]=d;raw_hash[d['id']]=hashlib.sha256(b).hexdigest()
    officials={x['id']:x for x in json.loads(Path(args.official_results).read_text())} if args.official_results else {}
    sources=[records[k] for k in sorted(records)];clean=[inputs(d) for d in sources]
    before=replay(clean,Path(args.baseline_source));after=replay(clean,Path('arvexq/ui/static/app.js'))
    rows=[];score_mismatches=[];mark_mismatches=[]
    for d,base in zip(sources,clean):
        rid=d['id'];official=officials.get(rid);result=d.get('result') or {}
        saved=sorted((x for x in result.get('finishers',[]) if x.get('finish',0)>0),key=lambda x:x['finish'])
        order=official.get('officialOrder') if official and official.get('officialOrder') else [x['horseNumber'] for x in saved]
        if len(order)<3:continue
        row={'id':rid,'date':d['date'],'circuit':d['circuit'],'order':order,
             'resultSource':official or {'type':'saved-result','source':result.get('source'),'url':result.get('sourceUrl')},
             'responseSha256':raw_hash[rid],'inputSha256':digest(base),
             'originalPredictionSha256':digest(d.get('preRacePrediction')),
             'originalTicketSha256':digest(d.get('preRaceBet'))}
        lock=sealed_lock(d)
        if lock:
            bet=d.get('preRaceBet') if has_valid_original(d.get('preRaceBet'),race_id=rid,start_at=post_at(d)) else None
            row['original']={'marks':mark_metrics({x['horseNumber']:x.get('mark','') for x in lock['horses']},order),
                             'tickets':ticket_metrics(bet,order),'capturedAt':lock.get('capturedAtJst')}
        else:row['original']=None
        for lane,source in [('before',before),('after',after)]:
            r=source[rid];marks=mark_metrics({x['no']:x['mark'] for x in r['rows']},order)
            row[lane]={'marks':marks,'tickets':ticket_metrics(r['plan'],order)}
        py={z['horse']['horseNumber']:z for z in rank_observed(base['horses'],base)}
        marked=copy.deepcopy(base);apply_observed_marks(marked)
        py_marks={h['horseNumber']:h.get('integratedEvaluation',{}).get('mark','') for h in marked['horses']}
        for z in after[rid]['rows']:
            p=py.get(z['no'],{}).get('score');q=z['score']
            if (p is None)!=(q is None) or p is not None and abs(p-q)>1e-7:score_mismatches.append([rid,z['no'],p,q])
            if z['mark']!=py_marks[z['no']]:mark_mismatches.append([rid,z['no'],py_marks[z['no']],z['mark']])
        rank=sorted((z for z in after[rid]['rows'] if z['score'] is not None),key=lambda z:-z['score'])
        hon=next((z['horseNumber'] for z in row['after']['marks'] if z['mark']=='◎'),None)
        actual_rank=next((i+1 for i,z in enumerate(rank) if z['no']==order[0]),None)
        tri=row['after']['tickets'].get('3連単')
        row['missAnalysis']={'type':'observed-error-classification; causal attribution not established',
            'actualWinnerModelRank':actual_rank,'predictedHonmei':hon,'actualWinner':order[0],
            'winnerScored':actual_rank is not None,
            'trifectaStatus':'not-offered-insufficient-evidence-or-confidence' if not tri else 'hit' if tri['hit'] else 'actual-order-outside-top10',
            'inputCoverage':sum(z['score'] is not None for z in after[rid]['rows'])/len(after[rid]['rows']) if after[rid]['rows'] else 0}
        rows.append(row)
    summary={lane:summarize(rows,lane) for lane in ('original','before','after')}
    regressions=[]
    for circuit in summary['before']:
        b=summary['before'][circuit];a=summary['after'][circuit]
        for kind,old in b['tickets'].items():
            if a['tickets'].get(kind,{}).get('hitRaces',0)<old['hitRaces']:regressions.append({'circuit':circuit,'metric':kind+' hit races','before':old['hitRaces'],'after':a['tickets'].get(kind,{}).get('hitRaces',0)})
        if a['honmeiWins']<b['honmeiWins']:regressions.append({'circuit':circuit,'metric':'honmei wins','before':b['honmeiWins'],'after':a['honmeiWins']})
    report={'baselineSourceSha256':hashlib.sha256(Path(args.baseline_source).read_bytes()).hexdigest(),
            'candidateSourceSha256':hashlib.sha256(Path('arvexq/ui/static/app.js').read_bytes()).hexdigest(),
            'races':len(rows),'summary':summary,'scoreParityMismatches':score_mismatches,'markParityMismatches':mark_mismatches,
            'releaseGate':{'passed':not regressions and not score_mismatches and not mark_mismatches,'regressions':regressions},
            'conditions':['Paired exact same current saved factual inputs for both replay engines.',
                          'Replay is retrospective, not a forecast saved before the race.',
                          'Original accuracy uses only timestamp-validated immutable pre-off seals.',
                          'Histories are bounded strictly before race date; results, payouts, odds and old scores excluded.',
                          'Baseline trifecta max6 versus candidate max10; point budgets differ.',
                          'Observed miss classifications do not establish causal racing explanations.',
                          'Candidate selected with knowledge of Oct16; Oct12 is a separate historical check, not a prospective holdout.',
                          'Partial/missing forecasts and offered-only versus all-race denominators reported separately.'],
            'rows':rows}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:report[k] for k in ('races','summary','releaseGate')},ensure_ascii=False))
if __name__=='__main__':main()
