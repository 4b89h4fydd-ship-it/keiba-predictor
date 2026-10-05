#!/usr/bin/env python3
from __future__ import annotations

import copy
from statistics import median

import scripts.arvexq_today_old_new_compare as audit
from arvexq.prediction.factor_model import rank_factor_model

FAMILIES = {
    'ability': [
        ('ability_speed_peak','ability_speed_median'),
        ('ability_peak_finish',), ('ability_sectional',), ('ability_true_run',),
        ('ability_pure',), ('ability_research',),
    ],
    'record': [
        ('record_career','record_recent'),
        ('record_win_rate','record_top3_rate'),
        ('record_level','record_class_edge','record_class_research'),
        ('record_representative',), ('record_race_performance',), ('record_form_research',),
    ],
    'suitability': [
        ('suit_distance_history','suit_track_history','suit_going_history','suit_surface_history'),
        ('suit_distance_model','suit_track_model','suit_going_model','suit_surface_model'),
        ('suit_research',),
    ],
    'pace': [
        ('pace_scenario',), ('pace_state',), ('pace_research',),
        ('pace_track_speed_fit',), ('pace_hidden_effort',),
    ],
    'support': [
        ('support_pedigree','support_pedigree_distance','support_pedigree_surface','support_pedigree_research'),
        ('support_body','support_body_change','support_carried_weight'),
        ('support_weather',), ('support_draw',), ('support_condition_change','support_freshness'),
        ('support_age_sex',), ('support_jockey','support_trainer','support_connections'),
        ('support_bias','support_bias_model'),
    ],
}
PRIMARY=('ability','record','suitability','pace')

def med(vals):
    x=[float(v) for v in vals if v is not None]
    return float(median(x)) if x else None

def rerank(detail):
    rows=[dict(r) for r in rank_factor_model(detail.get('horses') or [], detail)]
    if not rows: return []
    for r in rows:
        mr=r['metricRelative']
        fs={}
        for p,families in FAMILIES.items():
            family_scores=[med([mr.get(k) for k in fam]) for fam in families]
            fs[p]=med(family_scores)
        r['dedup']=fs
        r['dWins']=r['dLosses']=r['dTies']=0
    for i in range(len(rows)):
        for j in range(i+1,len(rows)):
            a,b=rows[i],rows[j]; aw=bw=0
            for p in PRIMARY:
                av,bv=a['dedup'][p],b['dedup'][p]
                if av is None or bv is None or av==bv: continue
                if av>bv: aw+=1
                else: bw+=1
            if aw>bw: a['dWins']+=1; b['dLosses']+=1
            elif bw>aw: b['dWins']+=1; a['dLosses']+=1
            else:
                av,bv=a['dedup']['support'],b['dedup']['support']
                if av is not None and bv is not None and av!=bv:
                    if av>bv: a['dWins']+=1; b['dLosses']+=1
                    else: b['dWins']+=1; a['dLosses']+=1
                else: a['dTies']+=1; b['dTies']+=1
    def rank_values(p):
        vals=sorted({r['dedup'][p] for r in rows if r['dedup'][p] is not None}, reverse=True)
        return {v:i+1 for i,v in enumerate(vals)}, len(vals)+1
    ranks={p:rank_values(p) for p in (*PRIMARY,'support')}
    for r in rows:
        r['dRanks']={p:ranks[p][0].get(r['dedup'][p],ranks[p][1]) for p in ranks}
    rows.sort(key=lambda r:(-r['dWins'],r['dLosses'],sum(r['dRanks'][p] for p in PRIMARY),r['dRanks']['support'],-r.get('sample',0),int(r['horse'].get('horseNumber') or 999)))
    return rows

def pos(order,n): return order.index(n)+1 if n in order else 999
def pct(x,n): return f'{x}/{n} ({100*x/n:.1f}%)' if n else '—'

def main():
    url=audit.API_BASE+'/api/day?'+audit.urllib.parse.urlencode({'date':audit.TARGET_DATE,'details':'1'})
    payload=audit.api_json(url); out=[]
    for detail in payload.get('details') or []:
        order=audit.finish_order(detail)
        if not order: continue
        snap,_=audit.find_prerace_snapshot(detail); old,_=audit.legacy_marks(detail,snap)
        base=audit.scrub_postrace(copy.deepcopy(detail))
        cur=rank_factor_model(base.get('horses') or [],base); ded=rerank(base)
        if not old or not cur or not ded: continue
        oldn=next((n for n,m in old.items() if m=='◎'),0)
        curn=int(cur[0]['horse'].get('horseNumber') or 0); dedn=int(ded[0]['horse'].get('horseNumber') or 0)
        nums=[int(r['horse'].get('horseNumber') or 0) for r in ded]
        out.append({'track':detail.get('track') or detail.get('venue') or '', 'race':audit.iv(detail.get('raceNumber',detail.get('raceNo'))), 'winner':order[0], 'old':pos(order,oldn), 'cur':pos(order,curn), 'ded':pos(order,dedn), 'winnerRank':nums.index(order[0])+1 if order[0] in nums else 999, 'curN':curn,'dedN':dedn,'top':[(int(r['horse'].get('horseNumber') or 0),r['dedup'],r.get('sample',0)) for r in ded[:3]]})
    n=len(out)
    print(f'SIGNAL DEDUP AUDIT {audit.TARGET_DATE} n={n}')
    for label,lim in [('◎1着',1),('◎連対',2),('◎3着内',3)]:
        vals=[sum(r[k]<=lim for r in out) for k in ('old','cur','ded')]
        print(label,*[pct(v,n) for v in vals],sep='\t')
    print('winnerTOP3',pct(sum(r['winnerRank']<=3 for r in out),n),'winnerTOP7',pct(sum(r['winnerRank']<=7 for r in out),n))
    changed=[r for r in out if r['curN']!=r['dedN']]
    print('changed',len(changed),'improved',sum(r['ded']<r['cur'] for r in changed),'worsened',sum(r['ded']>r['cur'] for r in changed))
    for r in changed:
        print(r)

if __name__=='__main__': main()
