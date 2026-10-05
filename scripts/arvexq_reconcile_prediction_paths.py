#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "arvexq" / "ui" / "static" / "app.js"
BUILD = ROOT / "build_static.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, got {count}")
    return text.replace(old, new, 1)


js = APP_JS.read_text(encoding="utf-8")

# Cache namespaces must move with the deployed build. Old fixed v86/v90/v128 keys
# could survive many prediction/data revisions and resurrect stale race/result state.
js = replace_once(
    js,
    'function cacheKey(d,c){return "keiba:v86:races:"+d+":"+(c||state.circuit||"")}',
    'function cacheKey(d,c){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":races:"+d+":"+(c||state.circuit||"")}',
    "race cache namespace",
)
js = replace_once(
    js,
    'function fullBundleKey(d){return "arvexq:v128:fullbundle:"+String(d||"")}',
    'function fullBundleKey(d){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":fullbundle:"+String(d||"")}',
    "bundle cache namespace",
)
js = replace_once(
    js,
    'function detailCacheKey(id){return "keiba:v90:detail:"+String(id||"")}',
    'function detailCacheKey(id){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":detail:"+String(id||"")}',
    "detail cache namespace",
)

# Today's live caches are display accelerators only; they must not remain authoritative
# through bodyweight/result/finalization changes.
js = replace_once(
    js,
    'if(d>=today()&&Date.now()-n(x.ts)>90*60000)return null;',
    'if(d>=today()&&Date.now()-n(x.ts)>2*60000)return null;',
    "race live ttl",
)
js = replace_once(
    js,
    'if(d>=today()&&age>6*3600000)return null;',
    'if(d>=today()&&age>5*60000)return null;',
    "bundle live ttl",
)
js = replace_once(
    js,
    'if(x.row.date>=today()&&age>12*3600000)return null;',
    'if(x.row.date>=today()&&age>2*60000)return null;',
    "detail live ttl",
)

# Server-side four-pillar marks / immutable pre-race lock are authoritative. Front-end
# V317 calculations may still produce supporting probabilities and scenarios, but are
# not allowed to silently replace ◎○▲☆+☆△注 when authoritative marks exist.
helper = r'''
function applyServerAuthoritativeMarks(rows,r){
  rows=rows||[];r=r||{};
  var byNo={},lock=r.preRacePrediction||{},locked=Array.isArray(lock.horses)?lock.horses:[],i,x,no,mark;
  for(i=0;i<locked.length;i++){x=locked[i]||{};no=n(x.horseNumber,0);mark=String(x.mark||'');if(no&&mark)byNo[no]=mark}
  if(!Object.keys(byNo).length){
    for(i=0;i<(r.horses||[]).length;i++){
      x=r.horses[i]||{};var e=x.integratedEvaluation||{};no=n(x.horseNumber,0);mark=String(e.mark||'');
      if(no&&mark&&String(e.markEngineVersion||r.markEngineVersion||'').indexOf('arvexq-four-pillar-marks-')===0)byNo[no]=mark
    }
  }
  if(!Object.keys(byNo).length)return false;
  var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};
  for(i=0;i<rows.length;i++){
    x=rows[i]||{};no=n(x.horse&&x.horse.horseNumber,0);mark=byNo[no]||'';
    x.frontendComputedMark=String(x.predMark||'');
    x.predMark=mark;
    x.predRank=order[mark]||999;
    x.authoritativeMark=!!mark;
  }
  return true
}
'''.strip()
needle = 'function predict(r){if(r._prediction)return r._prediction;'
if helper not in js:
    if needle not in js:
        raise RuntimeError("predict function anchor not found")
    js = js.replace(needle, helper + "\n" + needle, 1)

js = replace_once(
    js,
    'integratedGrades(r,rows);assignPredictionMarks(rows,modelRace);for(i=0;i<sc.length;i++)',
    'integratedGrades(r,rows);assignPredictionMarks(rows,modelRace);applyServerAuthoritativeMarks(rows,modelRace);for(i=0;i<sc.length;i++)',
    "authoritative mark application",
)

# Strict selection must stay market-independent. Popularity disagreement can remain a
# Value/Danger diagnostic, but cannot veto the pure prediction/selection gate.
js = replace_once(
    js,
    "mhAgree=!mhReady||(mhWinner>0&&leaderNo===mhWinner&&n(mh.winRank,999)===1&&!mh.dangerPopular&&n(mhSummary.winnerGap,0)>0);",
    "mhAgree=!mhReady||(mhWinner>0&&leaderNo===mhWinner&&n(mh.winRank,999)===1&&n(mhSummary.winnerGap,0)>0);",
    "market-independent strict selection",
)

# Bodyweight/status are prediction inputs. Odds/popularity remain market-only and do
# not invalidate the market-independent prediction core.
old_merge = "function mergeOddsPayload(body){if(!state.race||!body)return false;var changed=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h;for(i=0;i<rows.length;i++){z=rows[i]||{};if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z}for(i=0;i<hs.length;i++){h=hs[i];z=map[n(h.horseNumber)];if(!z)continue;if(z.winOdds!=null&&String(z.winOdds)!==''){h.winOdds=z.winOdds;changed=true}if(z.popularity!=null&&String(z.popularity)!==''){h.popularity=z.popularity;changed=true}if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){h.bodyWeight=z.bodyWeight;changed=true}if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){h.bodyWeightChange=z.bodyWeightChange;changed=true}if(z.oddsSource)h.oddsSource=z.oddsSource}if(body.oddsSource)state.race.oddsSource=body.oddsSource;if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;return changed}"
new_merge = "function mergeOddsPayload(body){if(!state.race||!body)return false;var changed=false,predictionInputChanged=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h,old;for(i=0;i<rows.length;i++){z=rows[i]||{};if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z}for(i=0;i<hs.length;i++){h=hs[i];z=map[n(h.horseNumber)];if(!z)continue;if(z.winOdds!=null&&String(z.winOdds)!==''){if(String(h.winOdds||'')!==String(z.winOdds))changed=true;h.winOdds=z.winOdds}if(z.popularity!=null&&String(z.popularity)!==''){if(String(h.popularity||'')!==String(z.popularity))changed=true;h.popularity=z.popularity}if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){old=String(h.bodyWeight||'');if(old!==String(z.bodyWeight)){changed=true;predictionInputChanged=true}h.bodyWeight=z.bodyWeight}if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){old=String(h.bodyWeightChange||'');if(old!==String(z.bodyWeightChange)){changed=true;predictionInputChanged=true}h.bodyWeightChange=z.bodyWeightChange}if(z.status!=null&&String(z.status)!==''){old=String(h.status||'');if(old!==String(z.status)){changed=true;predictionInputChanged=true}h.status=z.status}if(z.oddsSource)h.oddsSource=z.oddsSource}if(body.oddsSource)state.race.oddsSource=body.oddsSource;if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;if(predictionInputChanged){try{delete state.race._prediction}catch(e){}state.pred=null;state.analysisSaved={}}return changed}"
js = replace_once(js, old_merge, new_merge, "bodyweight/status invalidation")

APP_JS.write_text(js, encoding="utf-8")

build = BUILD.read_text(encoding="utf-8")
# This historical injection redefined assignPredictionMarks/grade functions after the
# source app.js loaded, creating a different model in static builds than in the app source.
old_inject = 'js = _inject_before_iife_close(js, ABILITY_FIRST_JS)'
if old_inject in build:
    build = build.replace(
        old_inject,
        '# Disabled: source app.js owns prediction behavior. Injecting ABILITY_FIRST_JS here\n# caused static-build marks to diverge from server/source marks.\n# js = _inject_before_iife_close(js, ABILITY_FIRST_JS)',
        1,
    )
elif '# js = _inject_before_iife_close(js, ABILITY_FIRST_JS)' not in build:
    raise RuntimeError("build_static prediction injection anchor not found")
BUILD.write_text(build, encoding="utf-8")

print("prediction paths reconciled; live cache/input invalidation hardened")
