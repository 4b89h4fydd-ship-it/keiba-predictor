#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH=Path('app.py')
text=PATH.read_text(encoding='utf-8')
original=text

# netkeiba enrichment used to append then truncate, allowing the same historical
# start from JRA + netkeiba to occupy two slots. Always field-merge instead.
old='''        if row.get("recentRaces") and len(h.get("recentRaces") or [])<5:
            existing=list(h.get("recentRaces") or []);existing.extend(row.get("recentRaces") or []);h["recentRaces"]=[z for z in existing if isinstance(z,dict)][:5]
'''
new='''        if row.get("recentRaces"):
            h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)
'''
if old in text:
    text=text.replace(old,new,1)
elif 'h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)' not in text:
    raise SystemExit('netkeiba enrichment history anchor not found')

# Live JRA card hydration must not replace a richer stored history wholesale.
old='''                            for k in ("bodyWeight","bodyWeightChange","sex","age","carriedWeight","jockey","trainer","recentRaces"):
                                if z.get(k) not in (None,"",0,[]):h[k]=z.get(k)
'''
new='''                            for k in ("bodyWeight","bodyWeightChange","sex","age","carriedWeight","jockey","trainer"):
                                if z.get(k) not in (None,"",0,[]):h[k]=z.get(k)
                            if z.get("recentRaces"):
                                h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],z.get("recentRaces") or [],5)
'''
if old in text:
    text=text.replace(old,new,1)
elif 'h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],z.get("recentRaces") or [],5)' not in text:
    raise SystemExit('live JRA history hydration anchor not found')

# Fast history used dict overwrite by key. That could discard complementary fields.
old='''        if runs:
            old=list(h.get("allPastRuns") or h.get("recentRaces") or [])
            dedup={}
            for rr in runs+old:
                if isinstance(rr,dict):dedup[RACEDB._run_key(rr)]=rr
            merged=sorted(dedup.values(),key=lambda z:str(z.get("date") or ""),reverse=True)
            h["recentRaces"]=merged[:5]
            h["allPastRuns"]=merged
'''
new='''        if runs:
            old=list(h.get("allPastRuns") or h.get("recentRaces") or [])
            merged=_jra_merge_runs(old,runs,max(5,len(old)+len(runs)))
            h["recentRaces"]=merged[:5]
            h["allPastRuns"]=merged
'''
if old in text:
    text=text.replace(old,new,1)
elif 'merged=_jra_merge_runs(old,runs,max(5,len(old)+len(runs)))' not in text:
    raise SystemExit('fast history merge anchor not found')

for required in (
    'h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)',
    'h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],z.get("recentRaces") or [],5)',
    'merged=_jra_merge_runs(old,runs,max(5,len(old)+len(runs)))',
):
    if required not in text:
        raise SystemExit(f'central history merge patch missing: {required}')

PATH.write_text(text,encoding='utf-8')
print('central history merge patch', 'updated' if text!=original else 'already-current')
