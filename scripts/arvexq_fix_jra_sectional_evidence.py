#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path("app.py")
text = PATH.read_text(encoding="utf-8")
original = text

# 1) JRA official result tables publish 推定上り, but the existing parser did not
# index that column at all. Preserve it as last3FSeconds on each finisher.
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

# 2) Historical central-run conversion must carry the official closing sectional
# forward into recentRaces/allPastRuns instead of dropping it.
old_return = '    return {\n        "raceId": race.get("id") or "",\n'
new_return = '''    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    return {
        "raceId": race.get("id") or "",
'''
if old_return in text:
    # Restrict replacement to the central-run function by checking preceding name.
    idx = text.find('def _central_run_from_race(')
    pos = text.find(old_return, idx)
    if idx < 0 or pos < 0:
        raise SystemExit("central run return anchor not found")
    text = text[:pos] + new_return + text[pos + len(old_return):]
elif 'last3f = fin.get("last3FSeconds")' not in text:
    raise SystemExit("central run last3f conversion anchor not found")

old_time_field = '        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),\n        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],\n'
new_time_field = '        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),\n        "last3FSeconds": last3f,\n        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],\n'
if old_time_field in text:
    text = text.replace(old_time_field, new_time_field, 1)
elif '        "last3FSeconds": last3f,\n' not in text:
    raise SystemExit("central run payload time anchor not found")

# 3) Treat last3FSeconds as a positive numeric field during duplicate-run merging.
old_numeric = '    if key in {"finish","fieldSize","distance","timeSeconds","carriedWeight","racePrize1","raceNumber"}:\n'
new_numeric = '    if key in {"finish","fieldSize","distance","timeSeconds","last3FSeconds","carriedWeight","racePrize1","raceNumber"}:\n'
if old_numeric in text:
    text = text.replace(old_numeric, new_numeric, 1)
elif '"last3FSeconds","carriedWeight"' not in text:
    raise SystemExit("JRA run numeric merge set anchor not found")

for required in (
    '"last3f":hidx("推定上り","上り")',
    '"last3FSeconds":last3f',
    'last3f = fin.get("last3FSeconds")',
    '"last3FSeconds": last3f',
    '"timeSeconds","last3FSeconds","carriedWeight"',
):
    if required not in text:
        raise SystemExit(f"JRA sectional patch missing: {required}")

PATH.write_text(text, encoding="utf-8")
print("JRA sectional evidence patch", "updated" if text != original else "already-current")
