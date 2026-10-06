#!/usr/bin/env python3
from pathlib import Path
import re
import runpy

PATH = Path("arvexq/ui/static/app.js")
INDEX_PATH = Path("arvexq/ui/static/index.html")
APP_PATH = Path("app.py")
BUILD_PATH = Path("build_static.py")
text = PATH.read_text(encoding="utf-8")


def remove_between(source: str, start: str, end: str) -> str:
    a = source.find(start)
    if a < 0:
        return source
    b = source.find(end, a + len(start))
    if b < 0:
        raise SystemExit(f"end marker not found for {start}")
    return source[:a] + source[b:]


# Standalone expected-value race selection is forbidden. Expected-value math may
# still be used internally by normal betting evaluation, but it must never create
# its own race category or user-facing high-value label.
text = remove_between(text, "function eliteValueRaceCut(rows){", "function expectedValueRaceCandidates(circuit){")
text = remove_between(text, "function expectedValueRaceCandidates(circuit){", "function fixedPickLoadStatus(circuit){")
text = remove_between(text, "function fixedValueBox(circuit,picks){", "function smartExpectedValueRaces(){")
text = remove_between(text, "function smartExpectedValueRaces(){", "function selectedRaceBetPreview(r){")

text = text.replace(
    "selectedSectionsOpen={selected:false,value:false},selectedCircuitSectionsOpen={selected:{'中央':false,'地方':false},value:{'中央':false,'地方':false}};",
    "selectedSectionsOpen={selected:false},selectedCircuitSectionsOpen={selected:{'中央':false,'地方':false}};",
)
text = text.replace("      smartExpectedValueRaces()+\n", "")
text = text.replace(
    "if(k==='selected'||k==='value')selectedSectionsOpen[k]=!!el.open",
    "if(k==='selected')selectedSectionsOpen[k]=!!el.open",
)
text = text.replace(
    "if((k==='selected'||k==='value')&&(c==='中央'||c==='地方'))selectedCircuitSectionsOpen[k][c]=!!el.open",
    "if(k==='selected'&&(c==='中央'||c==='地方'))selectedCircuitSectionsOpen[k][c]=!!el.open",
)
text = text.replace(
    "label=kind==='value'?'期待値判定':'厳選判定';",
    "label='厳選判定';",
)
text = text.replace("高期待値ゲート通過", "買い目品質ゲート通過")
text = text.replace("期待値品質スコア不足", "買い目品質スコア不足")

# Home has exactly two prediction boxes:
#   1) true elite selections
#   2) mandatory special forecasts = all graded races + Kochi Final.
SPECIAL = r'''function specialForecastRaceCandidates(){
  return (state.races||[]).filter(function(r){return r&&r.id&&mandatoryTrifectaRace(r)}).slice().sort(raceChronologicalCompare)
}
function smartSpecialForecastRaces(){
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=raceIsGraded(r)?'重賞':'高知ファイナル';
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日の重賞・高知ファイナルなし</small></div>';
  return '<section class="smart-fixed-picks smart-special-picks"><div class="smart-fixed-picks-head"><span><b>特別予想</b><small>重賞・高知ファイナル</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em></span></div><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></section>'
}
'''
text = remove_between(text, "function specialForecastRaceCandidates(){", "function smartDailyAiStats(){")
if "function smartDailyAiStats(){" not in text:
    raise SystemExit("smartDailyAiStats anchor not found")
text = text.replace("function smartDailyAiStats(){", SPECIAL + "\nfunction smartDailyAiStats(){", 1)
if "      smartSpecialForecastRaces()+\n" not in text:
    text = text.replace("      smartSelectedRaces()+\n", "      smartSelectedRaces()+\n      smartSpecialForecastRaces()+\n", 1)

# Force a new PWA shell so an installed iPhone app cannot keep rendering the old
# expected-value panel from the v324 cache.
text = re.sub(r'window\.ARVEXQ_BUILD="v\d+";', 'window.ARVEXQ_BUILD="v325";', text, count=1)
text = text.replace("v324-core-data-guard-20261004", "v325-home-race-boxes-20261006")
text = text.replace("/sw-v324-reset.js", "/sw-v325-reset.js")

for forbidden in (
    "function smartExpectedValueRaces(",
    "function expectedValueRaceCandidates(",
    "function eliteValueRaceCut(",
    "function fixedValueBox(",
    ">期待値高レース<",
    "smartExpectedValueRaces()+",
    "selected:false,value:false",
    "高期待値ゲート通過",
    "期待値品質スコア不足",
):
    if forbidden in text:
        raise SystemExit(f"value-race feature still present: {forbidden}")
if "function smartSpecialForecastRaces(){" not in text or "      smartSpecialForecastRaces()+\n" not in text:
    raise SystemExit("special forecast box missing")

PATH.write_text(text, encoding="utf-8")

# Keep static shell URLs aligned with the new build and force one hard reset.
if INDEX_PATH.exists():
    idx = INDEX_PATH.read_text(encoding="utf-8")
    idx = idx.replace("v324", "v325").replace("arvexq-hard-reset-v325-20261004", "arvexq-hard-reset-v325-20261006")
    INDEX_PATH.write_text(idx, encoding="utf-8")

if APP_PATH.exists():
    app_text = APP_PATH.read_text(encoding="utf-8")
    app_text = app_text.replace("v324-core-data-guard", "v325-home-race-boxes")
    APP_PATH.write_text(app_text, encoding="utf-8")

# Old cached v324 asset URLs must redirect to the new immutable v325 assets.
if BUILD_PATH.exists():
    build = BUILD_PATH.read_text(encoding="utf-8")
    build = build.replace('compat_css = ("v323",', 'compat_css = ("v324","v323",')
    build = build.replace('compat_app = ("v323",', 'compat_app = ("v324","v323",')
    build = build.replace('compat_arvexq = ("v323",', 'compat_arvexq = ("v324","v323",')
    BUILD_PATH.write_text(build, encoding="utf-8")

print("home race boxes enforced: selected + special forecasts; value-race category removed; build v325")

# Keep selection policy enforced after every generated UI pass. True selections
# use hit-first ticket choice and now require multi-head agreement; they are not
# forced into trifecta.
policy = Path("scripts/arvexq_enforce_selection_policy.py")
if policy.exists():
    runpy.run_path(str(policy), run_name="__main__")

# Graded races and Kochi Final always add a separate trifecta challenge on top
# of the recommended bet.
mandatory_tri = Path("scripts/arvexq_force_mandatory_trifecta.py")
if mandatory_tri.exists():
    runpy.run_path(str(mandatory_tri), run_name="__main__")
