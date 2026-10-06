#!/usr/bin/env python3
from pathlib import Path

PATH = Path("arvexq/ui/static/app.js")
text = PATH.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise SystemExit(f"{label} block not found")


# Use structured grade fields first. Title fallbacks are intentionally conservative.
old_graded = '''function raceIsGraded(r){var t=String(r&&r.title||''),c=String(r&&r.raceClass||r&&r.className||'');return /(?:Jpn\\s*)?G\\s*[ⅠⅡⅢ123]|(?:Jpn\\s*)[ⅠⅡⅢ123]|\\b(?:S|H|M)\\s*[ⅠⅡⅢ123]\\b|SP\\s*[ⅠⅡⅢ123]|重賞|グランプリ|ダービー|優駿|賞\\s*\\(重賞\\)/i.test(t+' '+c)}
'''
graded_v1 = '''function raceIsGraded(r){
  if(!r)return false;
  if(r.isGraded===true||r.graded===true||r.isGradeRace===true||r.gradeRace===true)return true;
  var t=String(r.title||''),meta=[r.grade,r.gradeLabel,r.raceGrade,r.gradeCode,r.raceClass,r.className,r.category].map(function(v){return String(v||'')}).join(' '),s=t+' '+meta;
  if(/(?:Jpn\\s*)?G\\s*(?:[ⅠⅡⅢ]|[123])|(?:Jpn\\s*)(?:[ⅠⅡⅢ]|[123])|(?:^|[\\s（(\\[])(?:S|H|M|SP)\\s*(?:[ⅠⅡⅢ]|[123])(?:$|[\\s）)\\]])|重賞|賞\\s*[（(]重賞[）)]/i.test(s))return true;
  return /(?:ダービー|優駿|グランプリ)(?:$|[（(])/i.test(t)
}
'''
new_graded = '''function raceIsGraded(r){
  if(!r)return false;
  if(r.isGraded===true||r.graded===true||r.isGradeRace===true||r.gradeRace===true)return true;
  var t=String(r.title||''),meta=[r.grade,r.gradeLabel,r.raceGrade,r.gradeCode,r.raceClass,r.className,r.category].map(function(v){return String(v||'')}).join(' '),s=t+' '+meta,grade='(?:[ⅠⅡⅢ]|I{1,3}|[123])';
  if(new RegExp('(?:Jpn\\\\s*)?G\\\\s*'+grade+'|(?:Jpn\\\\s*)'+grade+'|(?:^|[\\\\s（(\\\\[])(?:S|H|M|SP)\\\\s*'+grade+'(?:$|[\\\\s）)\\\\]])|重賞|賞\\\\s*[（(]重賞[）)]','i').test(s))return true;
  return /(?:ダービー|優駿|グランプリ)(?:$|[（(])/i.test(t)
}
'''
if old_graded in text:
    text = text.replace(old_graded, new_graded, 1)
elif graded_v1 in text:
    text = text.replace(graded_v1, new_graded, 1)
elif new_graded not in text:
    raise SystemExit("raceIsGraded block not found")

old_main = '''function mainRaceForTrack(rows){
  rows=(rows||[]).slice().sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});if(!rows.length)return null;
  var explicit=rows.find(function(r){return r.isMain||r.mainRace||r.featured||/メイン/.test(String(r.title||''))});if(explicit)return explicit;
  var r11=rows.find(function(r){return n(r.raceNumber)===11});if(r11)return r11;
  return rows.length>=2?rows[rows.length-2]:rows[rows.length-1]
}
'''
new_main = '''function mainRaceForTrack(rows){
  rows=(rows||[]).filter(function(r){return r&&r.id}).slice().sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});if(!rows.length)return null;
  var explicit=rows.find(function(r){var role=String(r.raceRole||r.role||r.raceType||'').toLowerCase();return r.isMain===true||r.mainRace===true||role==='main'||role==='mainrace'||/メイン/.test(String(r.title||''))});if(explicit)return explicit;
  var featured=rows.find(function(r){return r.featured===true});if(featured)return featured;
  var r11=rows.find(function(r){return n(r.raceNumber)===11});if(r11)return r11;
  return rows[rows.length-1]
}
function isMainForecastRace(r){
  if(!r||!r.id)return false;
  var circuit=String(r.circuit||''),track=String(r.track||''),rows=(state.races||[]).filter(function(z){
    if(!z||!z.id||String(z.track||'')!==track)return false;
    return !circuit||!z.circuit||String(z.circuit||'')===circuit
  }),main=mainRaceForTrack(rows);
  return !!(main&&String(main.id)===String(r.id))
}
'''
replace_once(old_main, new_main, "mainRaceForTrack")

old_candidates = '''function specialForecastRaceCandidates(){
  return (state.races||[]).filter(function(r){return r&&r.id&&mandatoryTrifectaRace(r)}).slice().sort(raceChronologicalCompare)
}
'''
new_candidates = "function specialForecastRaceCandidates(){\n  return (state.races||[]).filter(function(r){\n    if(!r||!r.id)return false;\n    var title=String(r.title||'');\n    return raceIsGraded(r)||(String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))\n  }).slice().sort(raceChronologicalCompare)\n}\nfunction specialForecastRaceTag(r){\n  var title=String(r&&r.title||'');\n  if(raceIsGraded(r))return '重賞';\n  if(String(r&&r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r&&r.raceNumber)===12))return '高知ファイナル';\n  return '特別'\n}\n"
replace_once(old_candidates, new_candidates, "specialForecastRaceCandidates")

old_featured = '''function isFeaturedBetRace(r,p){
  var title=String(r&&r.title||''),sel=null;
  try{sel=strictSelectedRaceProfile(r,p)}catch(e){}
  return !!(r&&(raceIsGraded(r)||
    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))
}
'''
new_featured = '''function isFeaturedBetRace(r,p){
  var title=String(r&&r.title||''),sel=null;
  try{sel=strictSelectedRaceProfile(r,p)}catch(e){}
  return !!(r&&(isMainForecastRace(r)||raceIsGraded(r)||
    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))
}
'''
replace_once(old_featured, new_featured, "isFeaturedBetRace")

old_render = '''function smartSpecialForecastRaces(){
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=raceIsGraded(r)?'重賞':'高知ファイナル';
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日の重賞・高知ファイナルなし</small></div>';
  return '<section class="smart-fixed-picks smart-special-picks"><div class="smart-fixed-picks-head"><span><b>特別予想</b><small>重賞・高知ファイナル</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em></span></div><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></section>'
}
'''
new_render = 'function smartSpecialForecastRaces(){\n  if(typeof state.specialForecastOpen!==\'boolean\'){\n    try{state.specialForecastOpen=localStorage.getItem(\'arvexq-special-forecast-open\')!==\'0\'}catch(e){state.specialForecastOpen=true}\n  }\n  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){\n    var tag=specialForecastRaceTag(r);\n    return \'<button type="button" class="fixed-pick-row" data-race="\'+esc(r.id)+\'"><span><b>\'+esc(r.track)+\' \'+esc(r.raceNumber)+\'R</b><small>\'+esc(r.title||\'\')+\'</small></span><time>\'+esc(r.startTime||\'--:--\')+\'</time><em>\'+tag+\'</em></button>\'\n  }).join(\'\'):\'<div class="fixed-pick-empty"><b>該当なし</b><small>本日の重賞・高知ファイナルなし</small></div>\';\n  return \'<details class="smart-fixed-picks smart-special-picks" data-special-fold="1"\'+(state.specialForecastOpen?\' open\':\'\')+\'><summary class="smart-fixed-picks-head"><span><b>特別予想</b><small>重賞・高知ファイナル</small></span><span class="smart-fixed-summary-right"><em>\'+picks.length+\'レース</em><i class="special-fold-icon" aria-hidden="true">›</i></span></summary><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">\'+body+\'</div></div></div></details>\'\n}\n'
replace_once(old_render, new_render, "smartSpecialForecastRaces")

old_save = '''function saveStoredAiBet(r,plan){try{if(!r||!r.id||!plan||isFinal(r))return;var st=mins(r.startTime),started=(r.date===today()&&st<9999&&nowMins()>=st);if(started||loadStoredAiBet(r.id,false))return;plan.fixedAt=new Date().toISOString();localStorage.setItem(aiBetStoreKey(r.id),JSON.stringify(plan))}catch(e){}}
'''
new_save = "function saveStoredAiBet(r,plan){\n  try{\n    if(!r||!r.id||!plan||isFinal(r))return;\n    var st=mins(r.startTime),raceDate=String(r.date||''),todayKey=today(),started=(raceDate===todayKey&&st<9999&&nowMins()>=st);\n    if(started||st>=9999||raceDate!==todayKey||loadStoredAiBet(r.id,false))return;\n    var rd=plan.dataReadiness||{},central=String(r.circuit||'')==='中央',minReady=central?.68:.60,ready=Number(rd.prediction),remain=st-nowMins(),lockWindow=30,\n        cardReady=n(rd.card,0)>=.90,historyReady=n(rd.history,0)>=.70,oddsReady=n(rd.actualOdds,0)>=.65,bodyReady=n(rd.bodyWeight,0)>=.70,environmentReady=n(rd.environment,0)>=1,analysisReady=n(rd.analysis,0)>=.45,\n        incomplete=/予想データの充足度が不足|データ充足待ち|予想データ不足|データ不足|準備中|実オッズ待ち/.test(String(plan.reason||'')+' '+String(plan.trifectaReason||''));\n    if(remain>lockWindow||remain<0)return;\n    if(!isFinite(ready)||ready<minReady)return;\n    if(!cardReady||!historyReady||!oddsReady||!bodyReady||!environmentReady||!analysisReady)return;\n    if(plan.decision==='見送り'&&incomplete)return;\n    plan.fixedAt=new Date().toISOString();plan.fixedBeforePost=true;plan.fixedMinutesBeforePost=Math.max(0,Math.round(remain));\n    plan.fixedInputReadiness={prediction:n(rd.prediction,0),card:n(rd.card,0),history:n(rd.history,0),actualOdds:n(rd.actualOdds,0),bodyWeight:n(rd.bodyWeight,0),environment:n(rd.environment,0),analysis:n(rd.analysis,0)};\n    plan.lockPolicy='v327-final-input-window-30m';\n    localStorage.setItem(aiBetStoreKey(r.id),JSON.stringify(plan))\n  }catch(e){}\n}\n"
replace_once(old_save, new_save, "saveStoredAiBet")

stored_helper = '''function immutableStoredAiBetView(r,plan){
  if(!plan)return plan;
  var status=String(r&&r.raceStatus||'')+' '+String(r&&r.result&&r.result.status||'');
  if(/中止|取止|取り止め|不成立/.test(status)){
    var cancelled=Object.assign({},plan);cancelled.items=[];cancelled.decision='見送り';cancelled.betQuality=0;cancelled.invalidatedAfterLock=true;cancelled.originalFixedAt=plan.fixedAt||'';cancelled.reason='レース中止・取止めのため、固定済み買い目は変更せず投票見送り。';cancelled.trifectaDecision='見送り';cancelled.trifectaReason='レース中止・取止め。';return cancelled
  }
  var scratched={};(r&&r.horses||[]).forEach(function(h){if(isScratchHorse(h))scratched[n(h.horseNumber)]=1});
  var affected=(plan.items||[]).some(function(z){return (z.combos||[]).some(function(c){return (c||[]).some(function(no){return !!scratched[n(no)]})})});
  if(!affected)return plan;
  var view=Object.assign({},plan);view.items=[];view.decision='見送り';view.betQuality=0;view.invalidatedAfterLock=true;view.originalFixedAt=plan.fixedAt||'';view.reason='発走前固定後に取消・除外馬が発生。元の買い目は変更せず、投票は見送り。';view.trifectaDecision='見送り';view.trifectaReason='固定後の取消・除外馬発生。';return view
}
'''
if stored_helper not in text:
    anchor='function buildAiBetPlan(r,p){'
    idx=text.find(anchor)
    if idx < 0:
        raise SystemExit("buildAiBetPlan anchor not found")
    text=text[:idx]+stored_helper+text[idx:]

old_plan_open = '''function buildAiBetPlan(r,p){
  var started=r&&r.date===today()&&mins(r.startTime)<9999&&nowMins()>=mins(r.startTime),terminal=isFinal(r)||started,
      stored=loadStoredAiBet(r&&r.id,terminal);
  if(terminal&&stored)return stored;
  if(terminal&&!stored)return null;
'''
plan_open_v1 = '''function buildAiBetPlan(r,p){
  var started=r&&r.date===today()&&mins(r.startTime)<9999&&nowMins()>=mins(r.startTime),terminal=isFinal(r)||started,
      stored=loadStoredAiBet(r&&r.id,terminal);
  if(stored)return stored;
  if(terminal)return null;
'''
new_plan_open = '''function buildAiBetPlan(r,p){
  var started=r&&r.date===today()&&mins(r.startTime)<9999&&nowMins()>=mins(r.startTime),terminal=isFinal(r)||started,
      stored=loadStoredAiBet(r&&r.id,terminal);
  if(stored)return immutableStoredAiBetView(r,stored);
  if(terminal)return null;
'''
if old_plan_open in text:
    text=text.replace(old_plan_open,new_plan_open,1)
elif plan_open_v1 in text:
    text=text.replace(plan_open_v1,new_plan_open,1)
elif new_plan_open not in text:
    raise SystemExit("buildAiBetPlan stored-plan lock block not found")

old_selected_preview = "var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id),st=mins(r.startTime),started=r.date===today()&&st<9999&&nowMins()>=st,plan=loadStoredAiBet(r.id,isFinal(r)||started),p=null;if(d&&!plan&&!isFinal(d)&&!started){try{p=predict(d);plan=buildAiBetPlan(d,p)}catch(e){}}"
new_selected_preview = "var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id),st=mins(r.startTime),started=r.date===today()&&st<9999&&nowMins()>=st,plan=loadStoredAiBet(r.id,isFinal(r)||started),p=null;if(plan)plan=immutableStoredAiBetView(d||r,plan);if(d&&!plan&&!isFinal(d)&&!started){try{p=predict(d);plan=buildAiBetPlan(d,p)}catch(e){}}"
replace_once(old_selected_preview,new_selected_preview,"selectedRaceBetPreview locked-plan safety")

old_lock_label = "<span>発走前固定</span>"
new_lock_label = "<span>'+esc(plan.fixedAt?'発走前固定':'暫定・更新あり')+'</span>"
if old_lock_label in text:
    text = text.replace(old_lock_label, new_lock_label, 1)
elif new_lock_label not in text:
    raise SystemExit("bet lock label not found")

prebuild_helper = '''function prebuildSpecialForecastPlans(){
  var picks=specialForecastRaceCandidates();
  picks.forEach(function(r){
    var id=String(r&&r.id||''),detail=id?(instantTrackDetails[id]||loadDetailCache(id)):null;
    if(!detail||isFinal(detail))return;
    var st=mins(detail.startTime||r.startTime),started=(detail.date||r.date)===today()&&st<9999&&nowMins()>=st;
    if(started)return;
    try{var p=predict(detail);buildAiBetPlan(detail,p)}catch(e){}
  })
}
'''
if prebuild_helper not in text:
    anchor = 'function smartSpecialForecastRaces(){'
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("smartSpecialForecastRaces anchor not found")
    text = text[:idx] + prebuild_helper + text[idx:]

old_after_details = '''        selectedRacePreload.analysisReady=analysisReady;
        lastDetailsAt=Date.now();
        render();scheduleTopRefresh()
'''
new_after_details = '''        selectedRacePreload.analysisReady=analysisReady;
        lastDetailsAt=Date.now();
        prebuildSpecialForecastPlans();
        render();scheduleTopRefresh()
'''
replace_once(old_after_details, new_after_details, "requestDetails completion")

for required in (
    "function raceIsGraded(r){",
    "I{1,3}",
    "function mainRaceForTrack(rows){",
    "return rows[rows.length-1]",
    "function isMainForecastRace(r){",
    "isMainForecastRace(r)||raceIsGraded(r)",
    "function specialForecastRaceTag(r){",
    "add(mainRaceForTrack(groups[k]))",
    "add(kochiFinalRace(rows))",
    "メイン・重賞・高知ファイナル",
    "function prebuildSpecialForecastPlans(){",
    "prebuildSpecialForecastPlans();",
    "buildAiBetPlan(detail,p)",
    "function immutableStoredAiBetView(r,plan){",
    "if(stored)return immutableStoredAiBetView(r,stored);",
    "発走前固定後に取消・除外馬が発生",
    "remain>45&&!bodyReady",
    "暫定・更新あり",
):
    if required not in text:
        raise SystemExit(f"special race patch missing: {required}")

for forbidden in (
    "return rows.length>=2?rows[rows.length-2]:rows[rows.length-1]",
    "if(terminal&&stored)return stored;",
    "if(stored)return stored;",
):
    if forbidden in text:
        raise SystemExit(f"obsolete special/bet-lock behavior remains: {forbidden}")

PATH.write_text(text, encoding="utf-8")
print("special forecast hardened: graded/main scope, pre-race lock, immutable plan, scratch/cancel safety")
