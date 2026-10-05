#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, re, statistics, urllib.parse, urllib.request
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone

JST=timezone(timedelta(hours=9))
API_DEFAULT='https://kraiz-api.4b89h4fydd.workers.dev'


def num(v, default=0.0):
    try:
        x=float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default

def iv(v, default=0):
    try:return int(float(v))
    except Exception:return default

def is_scratched(h):
    if h.get('scratched') is True:return True
    return bool(re.search(r'取消|除外|競走除外|出走取消', str(h.get('status') or '')))

def api_json(url):
    req=urllib.request.Request(url, headers={'user-agent':'ARVEXQ-recent-audit/1.0','accept':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

def finish_order(d):
    rows=((d.get('result') or {}).get('finishers') or [])
    z=[]
    for r in rows:
        f=iv(r.get('finish')); n=iv(r.get('horseNumber'))
        if f>0 and n>0:z.append((f,n))
    z.sort()
    return [n for _,n in z]

def horses_ready(d):
    out=[]
    for h in d.get('horses') or []:
        if is_scratched(h):continue
        n=iv(h.get('horseNumber'))
        e=h.get('integratedEvaluation') or {}
        if n>0 and e:
            out.append((n,h,e))
    return out

def role_rank(hs, key):
    return [n for n,h,e in sorted(hs, key=lambda t:(-num(t[2].get(key), -1e9), t[0]))]

def overall_rank(hs):
    return [n for n,h,e in sorted(hs, key=lambda t:(-num(t[2].get('score'), -1e9), t[0]))]

def greedy_trifecta(hs):
    chosen=[]
    for key in ('p1Score','p2Score','p3Score'):
        cand=[t for t in hs if t[0] not in chosen]
        if not cand:return []
        cand.sort(key=lambda t:(-num(t[2].get(key), -1e9), t[0]))
        chosen.append(cand[0][0])
    return chosen

def mark_of(h,e):
    for obj in (h,e):
        for k in ('aiMark','mark','predictionMark','symbol','predictionSymbol'):
            v=obj.get(k)
            if isinstance(v,str) and v.strip(): return v.strip()
    return ''

def candidate_meta(d):
    out={}
    for k,v in d.items():
        kl=k.lower()
        if any(x in kl for x in ('select','recommend','confidence','target','value','strict','mainrace','featured')):
            if isinstance(v,(str,int,float,bool)) or v is None: out[k]=v
    return out

def calc(rows):
    n=len(rows)
    if not n:return {'races':0}
    top1=sum(r['winnerRankP1']==1 for r in rows)
    top3=sum(r['winnerRankP1']<=3 for r in rows)
    top5=sum(r['winnerRankP1']<=5 for r in rows)
    ov1=sum(r['winnerRankOverall']==1 for r in rows)
    tri=sum(r['trifectaExact'] for r in rows)
    place2=sum(r['winnerRankP1']<=2 for r in rows)
    return {
      'races':n,'p1Top1':top1/n,'p1Top2':place2/n,'p1Top3':top3/n,'p1Top5':top5/n,
      'overallTop1':ov1/n,'singleTrifectaExact':tri/n,
      'medianWinnerRankP1':statistics.median(r['winnerRankP1'] for r in rows),
      'p1Top1Count':top1,'p1Top3Count':top3,'singleTrifectaExactCount':tri,
    }
def pct(x):return f'{100*x:.1f}%'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--api',default=API_DEFAULT); ap.add_argument('--days',type=int,default=14); ap.add_argument('--out',default='recent-accuracy.json'); a=ap.parse_args()
    today=datetime.now(JST).date(); allrows=[]; daily_fetch=[]; mark_counter=Counter(); meta_samples=[]
    for off in range(0,a.days+1):
        ds=(today-timedelta(days=off)).isoformat()
        url=a.api.rstrip('/')+'/api/day?'+urllib.parse.urlencode({'date':ds,'details':'1'})
        try:p=api_json(url)
        except Exception as e:
            daily_fetch.append({'date':ds,'error':str(e)[:180]}); continue
        usable=0
        for d in p.get('details') or []:
            order=finish_order(d)
            hs=horses_ready(d)
            if len(order)<3 or len(hs)<4 or order[0] not in {x[0] for x in hs}:continue
            p1=role_rank(hs,'p1Score'); ov=overall_rank(hs); tri=greedy_trifecta(hs)
            try:r1=p1.index(order[0])+1
            except ValueError:r1=999
            try:ro=ov.index(order[0])+1
            except ValueError:ro=999
            marks={n:mark_of(h,e) for n,h,e in hs}
            for m in marks.values():
                if m: mark_counter[m]+=1
            meta=candidate_meta(d)
            if meta and len(meta_samples)<20:meta_samples.append({'id':d.get('id'),'date':ds,'meta':meta})
            allrows.append({
              'date':ds,'id':str(d.get('id') or ''),'circuit':str(d.get('circuit') or ''),'track':str(d.get('track') or ''),'raceNo':iv(d.get('raceNumber')),
              'winner':order[0],'winnerRankP1':r1,'winnerRankOverall':ro,'top3':order[:3],'predTrifecta':tri,'trifectaExact':tri[:3]==order[:3],
              'field':len(hs),'winnerMark':marks.get(order[0],''),'topP1Mark':marks.get(p1[0],'') if p1 else ''
            }); usable+=1
        daily_fetch.append({'date':ds,'apiRaceCount':iv(p.get('raceCount')),'detailCount':iv(p.get('detailCount')),'usableFinal':usable})
    allrows.sort(key=lambda r:(r['date'],r['circuit'],r['track'],r['raceNo'],r['id']))
    windows={}
    for days in (1,3,7,14):
        start=(today-timedelta(days=days-1)).isoformat()
        rs=[r for r in allrows if r['date']>=start]
        windows[str(days)]=calc(rs)
        windows[str(days)]['byCircuit']={c:calc([r for r in rs if r['circuit']==c]) for c in sorted({r['circuit'] for r in rs})}
    daily={d:calc([r for r in allrows if r['date']==d]) for d in sorted({r['date'] for r in allrows}, reverse=True)}
    worst=[r for r in allrows if r['winnerRankP1']>=4]
    recent_worst=sorted(worst,key=lambda r:(r['date'],r['raceNo']),reverse=True)[:30]
    out={'generatedAt':datetime.now(JST).isoformat(),'today':today.isoformat(),'rows':len(allrows),'windows':windows,'daily':daily,'fetch':daily_fetch,'markCounts':dict(mark_counter),'metaSamples':meta_samples,'recentWinnerOutsideTop3':recent_worst}
    with open(a.out,'w',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print('# ARVEXQ recent prediction accuracy audit')
    print('generated',out['generatedAt'],'usable races',len(allrows))
    for w in ('1','3','7','14'):
        m=windows[w]
        print(f"WINDOW {w}d races={m.get('races',0)} P1_TOP1={pct(m.get('p1Top1',0))} P1_TOP3={pct(m.get('p1Top3',0))} P1_TOP5={pct(m.get('p1Top5',0))} OVERALL_TOP1={pct(m.get('overallTop1',0))} SINGLE_TRI={pct(m.get('singleTrifectaExact',0))}")
        for c,cm in m.get('byCircuit',{}).items():
            print(f"  CIRCUIT {c or '不明'} n={cm.get('races',0)} P1_TOP1={pct(cm.get('p1Top1',0))} P1_TOP3={pct(cm.get('p1Top3',0))} TRI={pct(cm.get('singleTrifectaExact',0))}")
    print('DAILY')
    for d,m in list(daily.items())[:10]:
        print(f"  {d} n={m.get('races',0)} P1_TOP1={pct(m.get('p1Top1',0))} P1_TOP3={pct(m.get('p1Top3',0))} TRI={pct(m.get('singleTrifectaExact',0))}")
    print('MARK_COUNTS',json.dumps(dict(mark_counter),ensure_ascii=False,sort_keys=True))
    print('META_SAMPLES',json.dumps(meta_samples[:5],ensure_ascii=False))
    print('RECENT_WINNER_OUTSIDE_TOP3')
    for r in recent_worst[:20]: print(json.dumps(r,ensure_ascii=False))
if __name__=='__main__':main()
