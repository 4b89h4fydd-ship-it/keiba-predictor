#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

APP = Path("arvexq/ui/static/app.js")
CSS = Path("arvexq/ui/static/styles.css")
GENERATOR = Path("scripts/arvexq_patch_special_races.py")

text = APP.read_text(encoding="utf-8")

candidate_block = '''function specialForecastRaceCandidates(){
  return (state.races||[]).filter(function(r){
    if(!r||!r.id)return false;
    var title=String(r.title||'');
    return raceIsGraded(r)||(String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))
  }).slice().sort(raceChronologicalCompare)
}
function specialForecastRaceTag(r){
  var title=String(r&&r.title||'');
  if(raceIsGraded(r))return '重賞';
  if(String(r&&r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r&&r.raceNumber)===12))return '高知ファイナル';
  return '特別'
}
'''

candidate_pattern = re.compile(
    r"function specialForecastRaceCandidates\(\)\{.*?\n\}\nfunction specialForecastRaceTag\(r\)\{.*?\n\}\n",
    re.S,
)
if candidate_block not in text:
    text, count = candidate_pattern.subn(candidate_block, text, count=1)
    if count != 1:
        raise SystemExit("special forecast candidate block not found")

render_block = '''function smartSpecialForecastRaces(forceOpen){
  if(typeof state.specialForecastOpen!=='boolean'){
    try{state.specialForecastOpen=localStorage.getItem('arvexq-special-forecast-open')!=='0'}catch(e){state.specialForecastOpen=true}
  }
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=specialForecastRaceTag(r);
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日の重賞・高知ファイナルなし</small></div>';
  return '<details class="smart-fixed-picks smart-special-picks" data-special-fold="1"'+((forceOpen||state.specialForecastOpen)?' open':'')+'><summary class="smart-fixed-picks-head"><span><b>特別予想</b><small>重賞・高知ファイナル</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em><i class="special-fold-icon" aria-hidden="true">›</i></span></summary><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></details>'
}
'''
render_pattern = re.compile(r"function smartSpecialForecastRaces(?:\\(forceOpen\\)|\\(\\))\\{.*?\\n\\}", re.S)
if render_block.rstrip() not in text:
    text, count = render_pattern.subn(render_block.rstrip(), text, count=1)
    if count != 1:
        raise SystemExit("smartSpecialForecastRaces block not found")

fold_handler = "els=document.querySelectorAll('[data-special-fold]');for(i=0;i<els.length;i++)els[i].ontoggle=function(){state.specialForecastOpen=!!this.open;try{localStorage.setItem('arvexq-special-forecast-open',this.open?'1':'0')}catch(e){}};"
if fold_handler not in text:
    anchor = "els=document.querySelectorAll('[data-race]');"
    if anchor not in text:
        raise SystemExit("data-race bind anchor not found")
    text = text.replace(anchor, fold_handler + anchor, 1)

for forbidden in (
    "<small>メイン・重賞・高知ファイナル</small>",
    "本日のメイン・重賞・高知ファイナルなし",
):
    if forbidden in text:
        raise SystemExit(f"old main-race special forecast copy remains: {forbidden}")

APP.write_text(text, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
marker = "/* ARVEXQ special forecast fold v1 */"
block = '''
/* ARVEXQ special forecast fold v1 */
.smart-special-picks>summary.smart-fixed-picks-head{list-style:none;cursor:pointer;-webkit-user-select:none;user-select:none}
.smart-special-picks>summary.smart-fixed-picks-head::-webkit-details-marker{display:none}
.smart-special-picks .smart-fixed-summary-right{display:flex;align-items:center;gap:8px}
.smart-special-picks .special-fold-icon{display:inline-block;font-style:normal;font-size:20px;line-height:1;transform:rotate(90deg);transition:transform .15s ease}
.smart-special-picks:not([open]) .special-fold-icon{transform:rotate(0deg)}
.smart-special-picks:not([open]) .smart-fixed-pick-grid{display:none!important}
'''
if marker not in css:
    css = css.rstrip() + "\n" + block
CSS.write_text(css, encoding="utf-8")

# Align the upstream generator with this final UI so Auto Refactor cannot restore
# generic main races or a non-collapsible special forecast block.
generator = GENERATOR.read_text(encoding="utf-8")

def replace_assignment(source: str, name: str, value: str, anchor: str) -> str:
    anchor_pos = source.find(anchor)
    if anchor_pos < 0:
        raise SystemExit(f"generator anchor missing: {anchor}")
    start = source.rfind(name + " = ", 0, anchor_pos)
    if start < 0:
        raise SystemExit(f"generator assignment missing: {name}")
    return source[:start] + name + " = " + repr(value) + "\n" + source[anchor_pos:]

generator = replace_assignment(
    generator,
    "new_candidates",
    candidate_block,
    'replace_once(old_candidates, new_candidates, "specialForecastRaceCandidates")',
)
generator = replace_assignment(
    generator,
    "new_render",
    render_block,
    'replace_once(old_render, new_render, "smartSpecialForecastRaces")',
)
GENERATOR.write_text(generator, encoding="utf-8")

print("special-forecast-ui-ok")
