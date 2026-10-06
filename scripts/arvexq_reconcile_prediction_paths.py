#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "arvexq" / "ui" / "static" / "app.js"
BUILD = ROOT / "build_static.py"


def ensure_replace(text: str, old: str, new: str, label: str) -> str:
    """Apply a generated patch once and stay safe on already-patched sources."""
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 old match, got {count}")
    return text.replace(old, new, 1)


js = APP_JS.read_text(encoding="utf-8")

# Cache namespaces move with the deployed build. Fixed historical keys survived many
# revisions and could resurrect stale result/bodyweight state in the PWA.
js = ensure_replace(
    js,
    'function cacheKey(d,c){return "keiba:v86:races:"+d+":"+(c||state.circuit||"")}',
    'function cacheKey(d,c){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":races:"+d+":"+(c||state.circuit||"")}',
    "race cache namespace",
)
js = ensure_replace(
    js,
    'function fullBundleKey(d){return "arvexq:v128:fullbundle:"+String(d||"")}',
    'function fullBundleKey(d){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":fullbundle:"+String(d||"")}',
    "bundle cache namespace",
)
js = ensure_replace(
    js,
    'function detailCacheKey(id){return "keiba:v90:detail:"+String(id||"")}',
    'function detailCacheKey(id){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":detail:"+String(id||"")}',
    "detail cache namespace",
)

# Today's local caches are accelerators only. Live state must refresh frequently enough
# for bodyweight, scratches, finalization and payouts.
js = ensure_replace(
    js,
    'if(d>=today()&&Date.now()-n(x.ts)>90*60000)return null;',
    'if(d>=today()&&Date.now()-n(x.ts)>2*60000)return null;',
    "race live ttl",
)
js = ensure_replace(
    js,
    'if(d>=today()&&age>6*3600000)return null;',
    'if(d>=today()&&age>5*60000)return null;',
    "bundle live ttl",
)
js = ensure_replace(
    js,
    'if(x.row.date>=today()&&age>12*3600000)return null;',
    'if(x.row.date>=today()&&age>2*60000)return null;',
    "detail live ttl",
)

# Server four-pillar marks / immutable pre-race lock are authoritative. Front-end V317
# may compute supporting probabilities/scenarios, but cannot silently replace marks.
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

js = ensure_replace(
    js,
    'integratedGrades(r,rows);assignPredictionMarks(rows,modelRace);for(i=0;i<sc.length;i++)',
    'integratedGrades(r,rows);assignPredictionMarks(rows,modelRace);applyServerAuthoritativeMarks(rows,modelRace);for(i=0;i<sc.length;i++)',
    "authoritative mark application",
)

# Strict selection must be market-independent AND agree with the authoritative ◎ when
# one is available. If legacy/current-win probability disagrees, the race is not elite.
old_mh = "var mh=((leader.horse||{}).integratedEvaluation||{}).multiHead||{},mhSummary=(r&&r.multiHeadSummary)||{},mhReady=String(mhSummary.modelVersion||'').indexOf('arvexq-multi-head-')===0,leaderNo=n(leader.horse&&leader.horse.horseNumber),mhWinner=n(mhSummary.winnerHorseNumber),mhAgree=!mhReady||(mhWinner>0&&leaderNo===mhWinner&&n(mh.winRank,999)===1&&!mh.dangerPopular&&n(mhSummary.winnerGap,0)>0);"
old_mh2 = "var mh=((leader.horse||{}).integratedEvaluation||{}).multiHead||{},mhSummary=(r&&r.multiHeadSummary)||{},mhReady=String(mhSummary.modelVersion||'').indexOf('arvexq-multi-head-')===0,leaderNo=n(leader.horse&&leader.horse.horseNumber),mhWinner=n(mhSummary.winnerHorseNumber),mhAgree=!mhReady||(mhWinner>0&&leaderNo===mhWinner&&n(mh.winRank,999)===1&&n(mhSummary.winnerGap,0)>0);"
new_mh = "var authAxis=rows.filter(function(z){return z&&z.predMark==='◎'})[0]||null,authAxisNo=n(authAxis&&authAxis.horse&&authAxis.horse.horseNumber),mh=((leader.horse||{}).integratedEvaluation||{}).multiHead||{},mhSummary=(r&&r.multiHeadSummary)||{},mhReady=String(mhSummary.modelVersion||'').indexOf('arvexq-multi-head-')===0,leaderNo=n(leader.horse&&leader.horse.horseNumber),mhWinner=n(mhSummary.winnerHorseNumber),authAgree=!authAxisNo||leaderNo===authAxisNo,mhAgree=authAgree&&(!mhReady||(mhWinner>0&&leaderNo===mhWinner&&n(mh.winRank,999)===1&&n(mhSummary.winnerGap,0)>0));"
if new_mh not in js:
    if old_mh in js:
        js = js.replace(old_mh, new_mh, 1)
    elif old_mh2 in js:
        js = js.replace(old_mh2, new_mh, 1)
    else:
        raise RuntimeError("strict selection multi-head anchor not found")

# Featured status means exactly strict selection OR mandatory graded/Kochi target.
old_featured = "function isFeaturedBetRace(r,p){\n  var title=String(r&&r.title||''),sel=null;\n  try{sel=raceSelectionProfile(r,p)}catch(e){}\n  return !!(r&&(raceIsGraded(r)||\n    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))\n}"
new_featured = "function isFeaturedBetRace(r,p){\n  var title=String(r&&r.title||''),sel=null;\n  try{sel=strictSelectedRaceProfile(r,p)}catch(e){}\n  return !!(r&&(raceIsGraded(r)||\n    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))\n}"
js = ensure_replace(js, old_featured, new_featured, "strict featured race policy")

# An authoritative ◎ may differ from legacy P1. In that disagreement, do not permit
# a 1st-place lock merely because the older winner model reports itself stable.
old_axis = "coreP1No=p1.length?n(p1[0].no):0,axisAgreement=!!(axisNo&&coreP1No&&axisNo===coreP1No),axisStable=!!(axisRow&&axisRow.winnerDecisionStable),centralRace=String((r&&r.circuit)||'')==='中央',axisLocked=axisStable&&axisConfidence>=(centralRace?.68:.62),"
new_axis = "coreP1No=p1.length?n(p1[0].no):0,axisAgreement=!!(axisNo&&coreP1No&&axisNo===coreP1No),axisStable=!!(axisRow&&axisRow.winnerDecisionStable),centralRace=String((r&&r.circuit)||'')==='中央',axisLocked=axisStable&&axisAgreement&&axisConfidence>=(centralRace?.68:.62),"
js = ensure_replace(js, old_axis, new_axis, "authoritative axis agreement")

# Bodyweight/status are prediction inputs. Odds/popularity remain market-only and do
# not invalidate the market-independent prediction core.
old_merge = "function mergeOddsPayload(body){if(!state.race||!body)return false;var changed=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h;for(i=0;i<rows.length;i++){z=rows[i]||{};if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z}for(i=0;i<hs.length;i++){h=hs[i];z=map[n(h.horseNumber)];if(!z)continue;if(z.winOdds!=null&&String(z.winOdds)!==''){h.winOdds=z.winOdds;changed=true}if(z.popularity!=null&&String(z.popularity)!==''){h.popularity=z.popularity;changed=true}if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){h.bodyWeight=z.bodyWeight;changed=true}if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){h.bodyWeightChange=z.bodyWeightChange;changed=true}if(z.oddsSource)h.oddsSource=z.oddsSource}if(body.oddsSource)state.race.oddsSource=body.oddsSource;if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;return changed}"
new_merge = "function mergeOddsPayload(body){if(!state.race||!body)return false;var changed=false,predictionInputChanged=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h,old;for(i=0;i<rows.length;i++){z=rows[i]||{};if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z}for(i=0;i<hs.length;i++){h=hs[i];z=map[n(h.horseNumber)];if(!z)continue;if(z.winOdds!=null&&String(z.winOdds)!==''){if(String(h.winOdds||'')!==String(z.winOdds))changed=true;h.winOdds=z.winOdds}if(z.popularity!=null&&String(z.popularity)!==''){if(String(h.popularity||'')!==String(z.popularity))changed=true;h.popularity=z.popularity}if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){old=String(h.bodyWeight||'');if(old!==String(z.bodyWeight)){changed=true;predictionInputChanged=true}h.bodyWeight=z.bodyWeight}if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){old=String(h.bodyWeightChange||'');if(old!==String(z.bodyWeightChange)){changed=true;predictionInputChanged=true}h.bodyWeightChange=z.bodyWeightChange}if(z.status!=null&&String(z.status)!==''){old=String(h.status||'');if(old!==String(z.status)){changed=true;predictionInputChanged=true}h.status=z.status}if(z.oddsSource)h.oddsSource=z.oddsSource}if(body.oddsSource)state.race.oddsSource=body.oddsSource;if(body.oddsUpdatedAt)state.race.oddsUpdatedAt;if(predictionInputChanged){try{delete state.race._prediction}catch(e){}state.pred=null;state.analysisSaved={}}return changed}"
# Preserve the exact current implementation if it is already reconciled. The assignment
# typo above is intentionally not applied; this block only replaces the legacy source.
current_merge = "function mergeOddsPayload(body){if(!state.race||!body)return false;var changed=false,predictionInputChanged=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h,old;for(i=0;i<rows.length;i++){z=rows[i]||{};if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z}for(i=0;i<hs.length;i++){h=hs[i];z=map[n(h.horseNumber)];if(!z)continue;if(z.winOdds!=null&&String(z.winOdds)!==''){if(String(h.winOdds||'')!==String(z.winOdds))changed=true;h.winOdds=z.winOdds}if(z.popularity!=null&&String(z.popularity)!==''){if(String(h.popularity||'')!==String(z.popularity))changed=true;h.popularity=z.popularity}if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){old=String(h.bodyWeight||'');if(old!==String(z.bodyWeight)){changed=true;predictionInputChanged=true}h.bodyWeight=z.bodyWeight}if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){old=String(h.bodyWeightChange||'');if(old!==String(z.bodyWeightChange)){changed=true;predictionInputChanged=true}h.bodyWeightChange=z.bodyWeightChange}if(z.status!=null&&String(z.status)!==''){old=String(h.status||'');if(old!==String(z.status)){changed=true;predictionInputChanged=true}h.status=z.status}if(z.oddsSource)h.oddsSource=z.oddsSource}if(body.oddsSource)state.race.oddsSource=body.oddsSource;if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;if(predictionInputChanged){try{delete state.race._prediction}catch(e){}state.pred=null;state.analysisSaved={}}return changed}"
if current_merge not in js:
    js = ensure_replace(js, old_merge, current_merge, "bodyweight/status invalidation")

APP_JS.write_text(js, encoding="utf-8")

build = BUILD.read_text(encoding="utf-8")

# Remove the obsolete build-time prediction implementation entirely. Keeping a dormant
# second assignPredictionMarks implementation made accidental reactivation too easy.
legacy_start = build.find("# Ability-first prediction core.")
legacy_end = build.find("SCRATCH_OVERLAY_CSS = r'''", legacy_start if legacy_start >= 0 else 0)
if legacy_start >= 0:
    if legacy_end <= legacy_start:
        raise RuntimeError("obsolete static prediction block end not found")
    build = build[:legacy_start] + (
        "# Prediction/mark logic is owned by arvexq/ui/static/app.js and the server-side\n"
        "# four-pillar engine. build_static.py must never redefine prediction functions.\n\n"
    ) + build[legacy_end:]
elif "ABILITY_FIRST_JS" in build or "_inject_before_iife_close" in build:
    raise RuntimeError("partial obsolete static prediction override remains")

# Keep redirects for immediately preceding shells. Accept a newer compat tuple as
# already reconciled so this script remains idempotent when build versions advance.
for label, var_name, old, new in (
    ("compat css", "compat_css", 'compat_css = ("v321",', 'compat_css = ("v323","v322","v321",'),
    ("compat app", "compat_app", 'compat_app = ("v321",', 'compat_app = ("v323","v322","v321",'),
    ("compat arvexq", "compat_arvexq", 'compat_arvexq = ("v321",', 'compat_arvexq = ("v323","v322","v321",'),
):
    if new in build:
        continue
    if old in build:
        build = build.replace(old, new, 1)
        continue
    line = next((ln for ln in build.splitlines() if ln.startswith(var_name + " = (")), "")
    if line and all(v in line for v in ('"v323"', '"v322"', '"v321"')):
        continue
    raise RuntimeError(f"{label}: anchor not found")

build = ensure_replace(
    build,
    '"shell":"ability-first-evidence"',
    '"shell":"four-pillar-authoritative"',
    "version shell label",
)
BUILD.write_text(build, encoding="utf-8")

print("prediction paths reconciled; obsolete override removed; selection/bets/cache/PWA hardened")
