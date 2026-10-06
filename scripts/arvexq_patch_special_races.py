#!/usr/bin/env python3
from pathlib import Path

PATH = Path("arvexq/ui/static/app.js")
text = PATH.read_text(encoding="utf-8")

old_candidates = '''function specialForecastRaceCandidates(){
  return (state.races||[]).filter(function(r){return r&&r.id&&mandatoryTrifectaRace(r)}).slice().sort(raceChronologicalCompare)
}
'''
new_candidates = '''function specialForecastRaceCandidates(){
  var rows=(state.races||[]).filter(function(r){return r&&r.id}),out=[],seen={},groups={};
  function add(r){var id=String(r&&r.id||'');if(!id||seen[id])return;seen[id]=1;out.push(r)}
  rows.forEach(function(r){if(raceIsGraded(r))add(r);var key=String(r.circuit||'')+'|'+String(r.track||'');(groups[key]||(groups[key]=[])).push(r)});
  Object.keys(groups).forEach(function(k){add(mainRaceForTrack(groups[k]))});
  add(kochiFinalRace(rows));
  return out.sort(raceChronologicalCompare)
}
function specialForecastRaceTag(r){
  var title=String(r&&r.title||'');
  if(raceIsGraded(r))return '重賞';
  if(String(r&&r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r&&r.raceNumber)===12))return '高知ファイナル';
  return 'メイン'
}
'''
if old_candidates in text:
    text = text.replace(old_candidates, new_candidates, 1)
elif new_candidates not in text:
    raise SystemExit("specialForecastRaceCandidates block not found")

old_render = '''function smartSpecialForecastRaces(){
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=raceIsGraded(r)?'重賞':'高知ファイナル';
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日の重賞・高知ファイナルなし</small></div>';
  return '<section class="smart-fixed-picks smart-special-picks"><div class="smart-fixed-picks-head"><span><b>特別予想</b><small>重賞・高知ファイナル</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em></span></div><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></section>'
}
'''
new_render = '''function smartSpecialForecastRaces(){
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=specialForecastRaceTag(r);
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日のメイン・重賞・高知ファイナルなし</small></div>';
  return '<section class="smart-fixed-picks smart-special-picks"><div class="smart-fixed-picks-head"><span><b>特別予想</b><small>メイン・重賞・高知ファイナル</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em></span></div><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></section>'
}
'''
if old_render in text:
    text = text.replace(old_render, new_render, 1)
elif new_render not in text:
    raise SystemExit("smartSpecialForecastRaces block not found")

for required in (
    "function specialForecastRaceTag(r){",
    "add(mainRaceForTrack(groups[k]))",
    "add(kochiFinalRace(rows))",
    "メイン・重賞・高知ファイナル",
):
    if required not in text:
        raise SystemExit(f"special race patch missing: {required}")

PATH.write_text(text, encoding="utf-8")
print("special forecast scope patched: main + graded + Kochi final; mandatory trifecta policy unchanged")
