#!/usr/bin/env python3
from pathlib import Path

APP = Path("arvexq/ui/static/app.js")
SPECIAL = Path("scripts/arvexq_patch_special_races.py")

LOCK_JS = '''function saveStoredAiBet(r,plan){
  try{
    if(!r||!r.id||!plan||isFinal(r))return;
    var st=mins(r.startTime),raceDate=String(r.date||''),todayKey=today(),started=(raceDate===todayKey&&st<9999&&nowMins()>=st);
    if(started||st>=9999||raceDate!==todayKey||loadStoredAiBet(r.id,false))return;
    var rd=plan.dataReadiness||{},central=String(r.circuit||'')==='中央',minReady=central?.68:.60,ready=Number(rd.prediction),remain=st-nowMins(),lockWindow=30,
        cardReady=n(rd.card,0)>=.90,historyReady=n(rd.history,0)>=.70,oddsReady=n(rd.actualOdds,0)>=.65,bodyReady=n(rd.bodyWeight,0)>=.70,environmentReady=n(rd.environment,0)>=1,analysisReady=n(rd.analysis,0)>=.45,
        incomplete=/予想データの充足度が不足|データ充足待ち|予想データ不足|データ不足|準備中|実オッズ待ち/.test(String(plan.reason||'')+' '+String(plan.trifectaReason||''));
    if(remain>lockWindow||remain<0)return;
    if(!isFinite(ready)||ready<minReady)return;
    if(!cardReady||!historyReady||!oddsReady||!bodyReady||!environmentReady||!analysisReady)return;
    if(plan.decision==='見送り'&&incomplete)return;
    plan.fixedAt=new Date().toISOString();plan.fixedBeforePost=true;plan.fixedMinutesBeforePost=Math.max(0,Math.round(remain));
    plan.fixedInputReadiness={prediction:n(rd.prediction,0),card:n(rd.card,0),history:n(rd.history,0),actualOdds:n(rd.actualOdds,0),bodyWeight:n(rd.bodyWeight,0),environment:n(rd.environment,0),analysis:n(rd.analysis,0)};
    plan.lockPolicy='v327-final-input-window-30m';
    localStorage.setItem(aiBetStoreKey(r.id),JSON.stringify(plan))
  }catch(e){}
}
'''


def replace_function(text: str, name: str, replacement: str) -> str:
    start = text.find(f"function {name}(")
    if start < 0:
        raise SystemExit(f"{name} not found")
    if text.startswith(replacement, start):
        return text
    depth = 0
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit(f"{name} opening brace not found")
    i = brace
    quote = None
    escaped = False
    regex = False
    while i < len(text):
        ch = text[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif regex:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "/":
                regex = False
        else:
            if ch in ("'", '"', '`'):
                quote = ch
            elif ch == "/" and i + 1 < len(text) and text[i + 1] not in ("/", "*"):
                # saveStoredAiBet contains a regex literal; treat it as opaque.
                regex = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[:start] + replacement.rstrip("\n") + text[i + 1:]
        i += 1
    raise SystemExit(f"{name} closing brace not found")


app = APP.read_text(encoding="utf-8")
app = replace_function(app, "saveStoredAiBet", LOCK_JS)
APP.write_text(app, encoding="utf-8")

# Keep the generator source aligned so Auto Refactor cannot restore the old early-lock rule.
src = SPECIAL.read_text(encoding="utf-8")
anchor = 'replace_once(old_save, new_save, "saveStoredAiBet")'
anchor_pos = src.find(anchor)
if anchor_pos < 0:
    raise SystemExit("special-race save replacement anchor not found")
start = src.rfind("new_save = ", 0, anchor_pos)
if start < 0:
    raise SystemExit("special-race new_save assignment not found")
assignment = "new_save = " + repr(LOCK_JS) + "\n"
src = src[:start] + assignment + src[anchor_pos:]
SPECIAL.write_text(src, encoding="utf-8")

print("bet-lock-policy-ok")
