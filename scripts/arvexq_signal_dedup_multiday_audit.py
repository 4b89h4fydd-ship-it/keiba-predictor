#!/usr/bin/env python3
from __future__ import annotations

import copy
import os
import urllib.parse
from datetime import date, timedelta

import scripts.arvexq_today_old_new_compare as audit
import scripts.arvexq_signal_dedup_audit as dedup
from arvexq.prediction.factor_model import rank_factor_model

DAYS = int(os.environ.get('ARVEXQ_DAYS', '7'))
END_DATE = date.fromisoformat(os.environ.get('ARVEXQ_DATE', '2026-10-05'))


def scrub(detail, target_date):
    d = copy.deepcopy(detail)
    for key in list(d):
        if key.lower() in {'result','results','payout','payouts','payoff','finishers','finishorder','winner'}:
            d.pop(key, None)
    ds = target_date.isoformat()
    for horse in d.get('horses') or []:
        if not isinstance(horse, dict):
            continue
        for key in ('allPastRuns','recentRaces'):
            rows = horse.get(key)
            if not isinstance(rows, list):
                continue
            kept=[]
            for run in rows:
                if not isinstance(run, dict):
                    continue
                text=str(run.get('date') or run.get('raceDate') or run.get('day') or '')
                if ds in text:
                    continue
                kept.append(run)
            horse[key]=kept
    return d


def pos(order, n):
    return order.index(n)+1 if n in order else 999


def pct(x,n):
    return f'{x}/{n} ({100*x/n:.1f}%)' if n else '—'


def main():
    rows=[]; fetch=[]
    for offset in range(DAYS):
        day=END_DATE-timedelta(days=offset)
        url=audit.API_BASE+'/api/day?'+urllib.parse.urlencode({'date':day.isoformat(),'details':'1'})
        try:
            payload=audit.api_json(url)
        except Exception as exc:
            fetch.append((day.isoformat(),'ERROR',str(exc)[:120])); continue
        used=0
        for detail in payload.get('details') or []:
            if not isinstance(detail,dict): continue
            order=audit.finish_order(detail)
            if not order: continue
            base=scrub(detail,day)
            cur=rank_factor_model(base.get('horses') or [],base)
            de=dedup.rerank(base)
            if not cur or not de: continue
            curn=int(cur[0]['horse'].get('horseNumber') or 0)
            den=int(de[0]['horse'].get('horseNumber') or 0)
            cur_nums=[int(r['horse'].get('horseNumber') or 0) for r in cur]
            de_nums=[int(r['horse'].get('horseNumber') or 0) for r in de]
            winner=order[0]
            rows.append({'date':day.isoformat(),'track':detail.get('track') or detail.get('venue') or '', 'race':audit.iv(detail.get('raceNumber',detail.get('raceNo'))),
                         'winner':winner,'curN':curn,'dedN':den,'curPos':pos(order,curn),'dedPos':pos(order,den),
                         'curWinnerRank':cur_nums.index(winner)+1 if winner in cur_nums else 999,
                         'dedWinnerRank':de_nums.index(winner)+1 if winner in de_nums else 999})
            used+=1
        fetch.append((day.isoformat(),len(payload.get('details') or []),used))
    n=len(rows)
    print(f'DEDUP MULTIDAY {DAYS}d through {END_DATE.isoformat()} n={n}')
    for label,lim in [('◎1着',1),('◎連対',2),('◎3着内',3),('◎5着内',5)]:
        c=sum(r['curPos']<=lim for r in rows); d=sum(r['dedPos']<=lim for r in rows)
        print(f'{label}\tCURRENT={pct(c,n)}\tDEDUP={pct(d,n)}\tdelta={d-c:+d}')
    for label,lim in [('勝馬TOP3',3),('勝馬TOP5',5),('勝馬TOP7',7)]:
        c=sum(r['curWinnerRank']<=lim for r in rows); d=sum(r['dedWinnerRank']<=lim for r in rows)
        print(f'{label}\tCURRENT={pct(c,n)}\tDEDUP={pct(d,n)}\tdelta={d-c:+d}')
    changed=[r for r in rows if r['curN']!=r['dedN']]
    print('changed',len(changed),'improved',sum(r['dedPos']<r['curPos'] for r in changed),'worsened',sum(r['dedPos']>r['curPos'] for r in changed),'equal',sum(r['dedPos']==r['curPos'] for r in changed))
    print('by_day')
    for ds in sorted({r['date'] for r in rows}):
        z=[r for r in rows if r['date']==ds]; nn=len(z)
        print(ds,'n',nn,'top1',sum(r['curPos']==1 for r in z),sum(r['dedPos']==1 for r in z),'top3',sum(r['curPos']<=3 for r in z),sum(r['dedPos']<=3 for r in z),'changed',sum(r['curN']!=r['dedN'] for r in z))
    print('fetch',fetch)

if __name__=='__main__': main()
