#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,re,statistics,urllib.parse,urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
JST=timezone(timedelta(hours=9)); API_DEFAULT='https://kraiz-api.4b89h4fydd.workers.dev'
def num(v,d=0.0):
    try:
        x=float(v); return x if math.isfinite(x) else d
    except:return d
def iv(v,d=0):
    try:return int(float(v))
    except:return d
def scratched(h):return h.get('scratched') is True or bool(re.search(r'取消|除外|競走除外|出走取消',str(h.get('status') or '')))
def api_json(u):
    q=urllib.request.Request(u,headers={'user-agent':'ARVEXQ-recent-audit/2.0','accept':'application/json'})
    with urllib.request.urlopen(q,timeout=30) as r:return json.loads(r.read().decode())
def order(d):
    z=[]
    for r in ((d.get('result') or {}).get('finishers') or []):
        f,n=iv(r.get('finish')),iv(r.get('horseNumber'))
        if f>0 and n>0:z.append((f,n))
    return [n for _,n in sorted(z)]
def horses(d):
    out=[]
    for h in d.get('horses') or []:
        if scratched(h):continue
        n=iv(h.get('horseNumber')); e=h.get('integratedEvaluation') or {}
        if n>0 and e:out.append((n,h,e))
    return out
def rank(hs,key):return [n for n,h,e in sorted(hs,key=lambda t:(-num(t[2].get(key),-1e9),t[0]))]
def odds_rank(hs):
    z=[]
    for n,h,e in hs:
        o=num(h.get('winOdds'),0)
        if o>0:z.append((o,n))
    return [n for _,n in sorted(z)] if len(z)>=4 else []
def mark(h,e):
    for o in (h,e):
        for k in ('aiMark','mark','predictionMark','symbol','predictionSymbol'):
            v=o.get(k)
            if isinstance(v,str) and v.strip():return v.strip()
    return ''
def greedy_tri(hs):
    out=[]
    for k in ('p1Score','p2Score','p3Score'):
        c=[t for t in hs if t[0] not in out]
        if not c:return []
        c.sort(key=lambda t:(-num(t[2].get(k),-1e9),t[0])); out.append(c[0][0])
    return out
def calc(rs):
    n=len(rs)
    if not n:return {'races':0}
    m=[r for r in rs if r['marketRank']<999]
    agree=[r for r in m if r['p1Pick']==r['marketPick']]; disagree=[r for r in m if r['p1Pick']!=r['marketPick']]
    def hit(a,k='winnerRankP1',lim=1):return sum(r[k]<=lim for r in a)/len(a) if a else None
    return {'races':n,'p1Top1':hit(rs),'p1Top3':hit(rs,lim=3),'p1Top5':hit(rs,lim=5),
      'overallTop1':hit(rs,'winnerRankOverall',1),'singleTri':sum(r['triExact'] for r in rs)/n,
      'marketRaces':len(m),'marketTop1':hit(m,'marketRank',1) if m else None,'marketTop3':hit(m,'marketRank',3) if m else None,
      'agreeRaces':len(agree),'agreeWin':sum(r['winner']==r['p1Pick'] for r in agree)/len(agree) if agree else None,
      'disagreeRaces':len(disagree),'arvexqWinWhenDisagree':sum(r['winner']==r['p1Pick'] for r in disagree)/len(disagree) if disagree else None,
      'marketWinWhenDisagree':sum(r['winner']==r['marketPick'] for r in disagree)/len(disagree) if disagree else None}
def pct(x):return '—' if x is None else f'{x*100:.1f}%'
def confidence(rs):
    z=sorted(rs,key=lambda r:r['p1Margin'],reverse=True); out={}
    for frac in (.10,.20,.30,.50):
        k=max(1,round(len(z)*frac)); a=z[:k]
        out[str(int(frac*100))]={'races':len(a),'top1':sum(r['winner']==r['p1Pick'] for r in a)/len(a),'top3':sum(r['winnerRankP1']<=3 for r in a)/len(a),'avgMargin':sum(r['p1Margin'] for r in a)/len(a)}
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--api',default=API_DEFAULT);ap.add_argument('--days',type=int,default=14);ap.add_argument('--out',default='recent-accuracy.json');a=ap.parse_args()
    today=datetime.now(JST).date();rows=[];fetch=[];marks=Counter();winmarks=Counter()
    for off in range(a.days+1):
        ds=(today-timedelta(days=off)).isoformat();u=a.api.rstrip('/')+'/api/day?'+urllib.parse.urlencode({'date':ds,'details':'1'})
        try:p=api_json(u)
        except Exception as e:fetch.append({'date':ds,'error':str(e)[:160]});continue
        use=0
        for d in p.get('details') or []:
            o=order(d);hs=horses(d)
            if len(o)<3 or len(hs)<4 or o[0] not in {x[0] for x in hs}:continue
            p1=rank(hs,'p1Score');ov=rank(hs,'score');mk=odds_rank(hs);tri=greedy_tri(hs)
            try:r1=p1.index(o[0])+1
            except:r1=999
            try:ro=ov.index(o[0])+1
            except:ro=999
            try:rm=mk.index(o[0])+1
            except:rm=999
            em={n:mark(h,e) for n,h,e in hs}
            for x in em.values():
                if x:marks[x]+=1
            if em.get(o[0]):winmarks[em[o[0]]]+=1
            scores=sorted([num(e.get('p1Score'),-1e9) for n,h,e in hs],reverse=True);margin=(scores[0]-scores[1]) if len(scores)>1 else 0
            rows.append({'date':ds,'id':str(d.get('id') or ''),'circuit':str(d.get('circuit') or ''),'track':str(d.get('track') or ''),'raceNo':iv(d.get('raceNumber')),
              'winner':o[0],'winnerRankP1':r1,'winnerRankOverall':ro,'marketRank':rm,'p1Pick':p1[0] if p1 else 0,'marketPick':mk[0] if mk else 0,
              'p1Margin':margin,'winnerMark':em.get(o[0],''),'triExact':tri[:3]==o[:3],'top3':o[:3]});use+=1
        fetch.append({'date':ds,'raceCount':iv(p.get('raceCount')),'usable':use})
    rows.sort(key=lambda r:(r['date'],r['circuit'],r['track'],r['raceNo']))
    windows={}
    for days in (1,3,7,14):
        st=(today-timedelta(days=days-1)).isoformat();rs=[r for r in rows if r['date']>=st];m=calc(rs);m['confidence']=confidence(rs) if rs else {};m['byCircuit']={c:calc([r for r in rs if r['circuit']==c]) for c in sorted({r['circuit'] for r in rs})};windows[str(days)]=m
    rs7=[r for r in rows if r['date']>=(today-timedelta(days=6)).isoformat()]
    tracks=[]
    for t in sorted({r['track'] for r in rs7}):
        x=[r for r in rs7 if r['track']==t]
        if len(x)>=8:tracks.append((calc(x)['p1Top1'],t,len(x),calc(x)['p1Top3']))
    tracks.sort()
    winmark7=Counter(r['winnerMark'] or '無印' for r in rs7)
    out={'generatedAt':datetime.now(JST).isoformat(),'rows':len(rows),'windows':windows,'markCounts':dict(marks),'winnerMarkCounts':dict(winmarks),'winnerMark7d':dict(winmark7),'worstTracks7d':[{'track':t,'n':n,'top1':a,'top3':b} for a,t,n,b in tracks[:10]],'fetch':fetch}
    with open(a.out,'w',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print('# ARVEXQ recent accuracy audit v2')
    for w in ('3','7','14'):
        m=windows[w];print(f"WINDOW {w}d n={m['races']} ARVEXQ_TOP1={pct(m['p1Top1'])} TOP3={pct(m['p1Top3'])} MARKET_TOP1={pct(m['marketTop1'])} MARKET_TOP3={pct(m['marketTop3'])} AGREE_n={m['agreeRaces']} AGREE_WIN={pct(m['agreeWin'])} DISAGREE_n={m['disagreeRaces']} ARVEXQ_DISAGREE_WIN={pct(m['arvexqWinWhenDisagree'])} MARKET_DISAGREE_WIN={pct(m['marketWinWhenDisagree'])}")
        for c,x in m['byCircuit'].items():print(f"  {c or '不明'} n={x['races']} ARVEXQ_TOP1={pct(x['p1Top1'])} TOP3={pct(x['p1Top3'])} MARKET_TOP1={pct(x['marketTop1'])}")
        print('  CONF', ' '.join(f"top{k}%:{v['races']}R win={pct(v['top1'])} top3={pct(v['top3'])}" for k,v in m['confidence'].items()))
    print('WINNER_MARK_7D',json.dumps(dict(winmark7),ensure_ascii=False,sort_keys=True))
    print('WORST_TRACKS_7D',json.dumps(out['worstTracks7d'],ensure_ascii=False))
    print('ALL_MARK_COUNTS',json.dumps(dict(marks),ensure_ascii=False,sort_keys=True))
if __name__=='__main__':main()
