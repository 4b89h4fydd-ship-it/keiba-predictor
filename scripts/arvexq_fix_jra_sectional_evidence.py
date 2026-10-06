#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path("app.py")
text = PATH.read_text(encoding="utf-8")
original = text

# 1) JRA official result tables publish 推定上り. Preserve the raw seconds.
old_ix = '    ix={"fin":hidx("着順"),"frame":hidx("枠"),"no":hidx("馬番"),"name":hidx("馬名"),"sexage":hidx("性齢"),"cw":hidx("負担重量","斤量"),"jockey":hidx("騎手名","騎手"),"time":hidx("タイム"),"corner":hidx("コーナー通過順位","コーナー通過順"),"bw":hidx("馬体重"),"trainer":hidx("調教師名","調教師"),"pop":hidx("単勝人気","人気")}\n'
new_ix = '    ix={"fin":hidx("着順"),"frame":hidx("枠"),"no":hidx("馬番"),"name":hidx("馬名"),"sexage":hidx("性齢"),"cw":hidx("負担重量","斤量"),"jockey":hidx("騎手名","騎手"),"time":hidx("タイム"),"last3f":hidx("推定上り","上り"),"corner":hidx("コーナー通過順位","コーナー通過順"),"bw":hidx("馬体重"),"trainer":hidx("調教師名","調教師"),"pop":hidx("単勝人気","人気")}\n'
if old_ix in text:
    text = text.replace(old_ix, new_ix, 1)
elif '"last3f":hidx("推定上り","上り")' not in text:
    raise SystemExit("JRA result header index anchor not found")

old_tm = '        tm=_jra_parse_time_seconds(val("time"));corners=[];cm=re.search(r"\\d{1,2}(?:-\\d{1,2})+",val("corner"))\n'
new_tm = '        tm=_jra_parse_time_seconds(val("time"));m3=re.search(r"\\d+(?:\\.\\d+)?",val("last3f"));last3f=float(m3.group()) if m3 else None;corners=[];cm=re.search(r"\\d{1,2}(?:-\\d{1,2})+",val("corner"))\n'
if old_tm in text:
    text = text.replace(old_tm, new_tm, 1)
elif 'val("last3f")' not in text:
    raise SystemExit("JRA result time/corner anchor not found")

old_finisher = '"timeSeconds":tm,"cornerPositions":corners,"bodyWeight":bw'
new_finisher = '"timeSeconds":tm,"last3FSeconds":last3f,"cornerPositions":corners,"bodyWeight":bw'
if old_finisher in text:
    text = text.replace(old_finisher, new_finisher, 1)
elif '"last3FSeconds":last3f' not in text:
    raise SystemExit("JRA finisher payload anchor not found")

# 2) Convert raw seconds into a within-race rank/percentile. This is an ordering
# transform only: no hand-set coefficient and no cross-course raw-time comparison.
rank_anchor = '    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))\n'
rank_block = '''    sectionals=sorted({float(x.get("last3FSeconds")) for x in finishers if x.get("last3FSeconds") not in (None,"") and float(x.get("last3FSeconds"))>0})
    for x in finishers:
        try:s=float(x.get("last3FSeconds")) if x.get("last3FSeconds") not in (None,"") else 0.0
        except (TypeError,ValueError):s=0.0
        if s>0 and sectionals:
            rk=sectionals.index(s)+1
            x["last3FRank"]=rk
            x["last3FPercentile"]=0.5 if len(sectionals)==1 else 1.0-(rk-1)/(len(sectionals)-1)
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
'''
if 'x["last3FPercentile"]=' not in text:
    idx = text.find('def _jra_parse_result(')
    pos = text.find(rank_anchor, idx)
    if idx < 0 or pos < 0:
        raise SystemExit("JRA finisher sort anchor not found")
    text = text[:pos] + rank_block + text[pos + len(rank_anchor):]

# 3) Historical central-run conversion must carry the official closing evidence
# into recentRaces/allPastRuns instead of dropping it.
old_return = '    return {\n        "raceId": race.get("id") or "",\n'
new_return = '''    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f_rank=fin.get("last3FRank") or horse.get("last3FRank")
    try:last3f_rank=int(last3f_rank) if last3f_rank not in (None,"") else None
    except (TypeError,ValueError):last3f_rank=None
    last3f_pct=fin.get("last3FPercentile") if fin.get("last3FPercentile") is not None else horse.get("last3FPercentile")
    try:last3f_pct=float(last3f_pct) if last3f_pct is not None else None
    except (TypeError,ValueError):last3f_pct=None
    return {
        "raceId": race.get("id") or "",
'''
if old_return in text:
    idx = text.find('def _central_run_from_race(')
    pos = text.find(old_return, idx)
    if idx < 0 or pos < 0:
        raise SystemExit("central run return anchor not found")
    text = text[:pos] + new_return + text[pos + len(old_return):]
elif 'last3f = fin.get("last3FSeconds")' not in text:
    raise SystemExit("central run last3f conversion anchor not found")

# Existing v1 patch may already have the last3f block; append rank/percentile there.
if 'last3f_rank=fin.get("last3FRank")' not in text:
    old_existing = '''    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    return {
'''
    new_existing = '''    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f_rank=fin.get("last3FRank") or horse.get("last3FRank")
    try:last3f_rank=int(last3f_rank) if last3f_rank not in (None,"") else None
    except (TypeError,ValueError):last3f_rank=None
    last3f_pct=fin.get("last3FPercentile") if fin.get("last3FPercentile") is not None else horse.get("last3FPercentile")
    try:last3f_pct=float(last3f_pct) if last3f_pct is not None else None
    except (TypeError,ValueError):last3f_pct=None
    return {
'''
    if old_existing not in text:
        raise SystemExit("existing central last3f conversion block not found")
    text = text.replace(old_existing, new_existing, 1)

old_time_field = '        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),\n        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],\n'
new_time_field = '        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),\n        "last3FSeconds": last3f,\n        "last3FRank": last3f_rank,\n        "last3FPercentile": last3f_pct,\n        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],\n'
if old_time_field in text:
    text = text.replace(old_time_field, new_time_field, 1)
elif '        "last3FSeconds": last3f,\n' in text and '        "last3FRank": last3f_rank,\n' not in text:
    text = text.replace(
        '        "last3FSeconds": last3f,\n',
        '        "last3FSeconds": last3f,\n        "last3FRank": last3f_rank,\n        "last3FPercentile": last3f_pct,\n',
        1,
    )
elif '        "last3FRank": last3f_rank,\n' not in text:
    raise SystemExit("central run payload time anchor not found")

# 4) Preserve the derived fields while merging duplicate historical starts.
old_numeric_v0 = '    if key in {"finish","fieldSize","distance","timeSeconds","carriedWeight","racePrize1","raceNumber"}:\n'
old_numeric_v1 = '    if key in {"finish","fieldSize","distance","timeSeconds","last3FSeconds","carriedWeight","racePrize1","raceNumber"}:\n'
new_numeric = '    if key in {"finish","fieldSize","distance","timeSeconds","last3FSeconds","last3FRank","last3FPercentile","carriedWeight","racePrize1","raceNumber"}:\n'
if old_numeric_v0 in text:
    text = text.replace(old_numeric_v0, new_numeric, 1)
elif old_numeric_v1 in text:
    text = text.replace(old_numeric_v1, new_numeric, 1)
elif '"last3FSeconds","last3FRank","last3FPercentile"' not in text:
    raise SystemExit("JRA run numeric merge set anchor not found")

for required in (
    '"last3f":hidx("推定上り","上り")',
    '"last3FSeconds":last3f',
    'x["last3FRank"]=',
    'x["last3FPercentile"]=',
    'last3f_rank=fin.get("last3FRank")',
    '"last3FRank": last3f_rank',
    '"last3FPercentile": last3f_pct',
    '"last3FSeconds","last3FRank","last3FPercentile"',
):
    if required not in text:
        raise SystemExit(f"JRA sectional patch missing: {required}")

PATH.write_text(text, encoding="utf-8")
print("JRA sectional evidence patch", "updated" if text != original else "already-current")
