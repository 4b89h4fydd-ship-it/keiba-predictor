#!/usr/bin/env python3
from pathlib import Path

PATH = Path("arvexq/ui/static/app.js")
text = PATH.read_text(encoding="utf-8")

old = '''function saveStoredAiBet(r,plan){
  try{
    if(!r||!r.id||!plan||isFinal(r))return;
    var st=mins(r.startTime),raceDate=String(r.date||''),todayKey=today(),started=(raceDate===todayKey&&st<9999&&nowMins()>=st);
    if(started||st>=9999||raceDate>todayKey||loadStoredAiBet(r.id,false))return;
    var rd=plan.dataReadiness||{},central=String(r.circuit||'')==='中央',minReady=central?.68:.60,ready=Number(rd.prediction),bodyReady=n(rd.bodyWeight,0)>=.70,remain=raceDate===todayKey?st-nowMins():9999,
        incomplete=/予想データの充足度が不足|データ充足待ち|予想データ不足|データ不足|準備中/.test(String(plan.reason||'')+' '+String(plan.trifectaReason||''));
    if(isFinite(ready)&&ready<minReady)return;
    if(plan.decision==='見送り'&&incomplete)return;
    if(raceDate===todayKey&&remain>45&&!bodyReady)return;
    plan.fixedAt=new Date().toISOString();plan.fixedBeforePost=true;
    localStorage.setItem(aiBetStoreKey(r.id),JSON.stringify(plan))
  }catch(e){}
}
'''

new = '''function saveStoredAiBet(r,plan){
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

if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("saveStoredAiBet block not found")

PATH.write_text(text, encoding="utf-8")
print("bet-lock-policy-ok")
