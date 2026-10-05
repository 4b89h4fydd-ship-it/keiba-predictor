#!/usr/bin/env python3
from pathlib import Path

PATH = Path('arvexq/ui/static/app.js')
text = PATH.read_text(encoding='utf-8')

# Mandatory prediction races are NOT the same thing as true ARVEXQ selections.
# Keep graded races and Kochi Final as mandatory prediction targets, but never
# promote them to 厳選 unless they independently pass the selection gate.
old_featured = "return !!(r&&(explicitSelectedRace(r)||raceIsGraded(r)||r.isMain||r.mainRace||r.featured||n(r.raceNumber)===11||\n    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))"
new_featured = "return !!(r&&(raceIsGraded(r)||\n    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))"
if old_featured in text:
    text = text.replace(old_featured, new_featured, 1)
elif new_featured not in text:
    raise SystemExit('featured race policy block not found')

# Make the visible 厳選 list genuinely sparse. It may be empty. Do not fill it
# with main/graded/Kochi races merely to have something to show. These stricter
# gates are selection filters, not a claim that any race is literally certain.
old_cut = "var best=n(rows[0].selection&&rows[0].selection.score),central=String((rows[0].race&&rows[0].race.circuit)||'')==='中央',floor=Math.max(central?72:68,best-4),limit=best>=(central?87:84)?3:2;\n  var elite=rows.filter(function(z){var t=z.selection||{},rd=t.readiness||{},central=String((z.race&&z.race.circuit)||'')==='中央';return n(t.score)>=floor&&n(rd.prediction)>=(central?.64:.61)&&n(t.coverage)>=(central?.44:.42)&&n(t.top3mass)>=(central?.58:.60)&&n(t.evidence)>=(central?.38:.36)&&n(t.scenarioProb)>=(central?.24:.22)&&!!t.winnerStable&&n(t.winnerConfidence)>=.60});\n  return elite.slice(0,limit).sort(raceChronologicalCompare)"
new_cut = "var best=n(rows[0].selection&&rows[0].selection.score),central=String((rows[0].race&&rows[0].race.circuit)||'')==='中央',floor=Math.max(central?82:80,best-2),limit=1;\n  var elite=rows.filter(function(z){var t=z.selection||{},rd=t.readiness||{},central=String((z.race&&z.race.circuit)||'')==='中央';return n(t.score)>=floor&&n(rd.prediction)>=(central?.74:.72)&&n(t.coverage)>=(central?.60:.58)&&n(t.top3mass)>=(central?.68:.70)&&n(t.evidence)>=(central?.55:.53)&&n(t.scenarioProb)>=(central?.30:.28)&&!!t.winnerStable&&n(t.winnerConfidence)>=.72});\n  return elite.slice(0,limit).sort(raceChronologicalCompare)"
if old_cut in text:
    text = text.replace(old_cut, new_cut, 1)
elif new_cut not in text:
    raise SystemExit('elite selection cut block not found')

# True selection needs agreement between the existing winner engine and the new
# independent multi-head layer. No arbitrary probability is introduced: require
# same winner, win-head rank 1, no danger-popular flag, and a non-tied top score.
old_gate = "var score=Math.round(clamp(qReady*.14+qTop3*.17+qMargin*.15+qEnt*.10+qScenario*.09+qEvidence*.10+qWin*.13+qTrue*.05+qCond*.04+qPos*.03,0,1)*100),\n      hard=(ready.prediction>=g.ready&&cov>=g.cov&&top3>=g.top3&&evidence>=g.evidence&&scenarioProb>=g.scenario&&winnerStable&&winnerConf>=g.confidence),\n      separation=(top>=Math.max(g.top,uniform*g.uniform)||margin>=g.margin),selected=hard&&separation&&score>=g.score;"
new_gate = "var mh=((leader.horse||{}).integratedEvaluation||{}).multiHead||{},mhSummary=(r&&r.multiHeadSummary)||{},mhReady=String(mhSummary.modelVersion||'').indexOf('arvexq-multi-head-')===0,leaderNo=n(leader.horse&&leader.horse.horseNumber),mhWinner=n(mhSummary.winnerHorseNumber),mhAgree=!mhReady||(mhWinner>0&&leaderNo===mhWinner&&n(mh.winRank,999)===1&&!mh.dangerPopular&&n(mhSummary.winnerGap,0)>0);\n  var score=Math.round(clamp(qReady*.14+qTop3*.17+qMargin*.15+qEnt*.10+qScenario*.09+qEvidence*.10+qWin*.13+qTrue*.05+qCond*.04+qPos*.03,0,1)*100),\n      hard=(ready.prediction>=g.ready&&cov>=g.cov&&top3>=g.top3&&evidence>=g.evidence&&scenarioProb>=g.scenario&&winnerStable&&winnerConf>=g.confidence),\n      separation=(top>=Math.max(g.top,uniform*g.uniform)||margin>=g.margin),selected=hard&&separation&&score>=g.score&&mhAgree;"
if new_gate not in text:
    if old_gate not in text:
        raise SystemExit('strict selection gate block not found')
    text = text.replace(old_gate, new_gate, 1)

old_failed = "var failed=[];if(ready.prediction<g.ready)failed.push('data');if(cov<g.cov)failed.push('coverage');if(top3<g.top3)failed.push('top3');if(evidence<g.evidence)failed.push('evidence');if(scenarioProb<g.scenario)failed.push('scenario');if(!winnerStable||winnerConf<g.confidence)failed.push('winner');if(!separation)failed.push('separation');if(score<g.score)failed.push('score');"
new_failed = "var failed=[];if(ready.prediction<g.ready)failed.push('data');if(cov<g.cov)failed.push('coverage');if(top3<g.top3)failed.push('top3');if(evidence<g.evidence)failed.push('evidence');if(scenarioProb<g.scenario)failed.push('scenario');if(!winnerStable||winnerConf<g.confidence)failed.push('winner');if(!separation)failed.push('separation');if(score<g.score)failed.push('score');if(!mhAgree)failed.push('multihead');"
if new_failed not in text:
    if old_failed not in text:
        raise SystemExit('strict selection failed-reason block not found')
    text = text.replace(old_failed, new_failed, 1)

old_return = "return{selected:selected,score:score,top:top,top3mass:top3,margin:margin,entropy:ent,coverage:cov,scenarioProb:scenarioProb,evidence:evidence,trueRun:trueRun,conditions:conditions,positionScenario:positionScenario,winnerConfidence:winnerConf,winnerStable:winnerStable,readiness:ready,failed:failed,reason:selected?'厳選ゲート通過':('見送り: '+failed.join(',')),base:base,model:method.id};"
new_return = "return{selected:selected,score:score,top:top,top3mass:top3,margin:margin,entropy:ent,coverage:cov,scenarioProb:scenarioProb,evidence:evidence,trueRun:trueRun,conditions:conditions,positionScenario:positionScenario,winnerConfidence:winnerConf,winnerStable:winnerStable,multiHeadReady:mhReady,multiHeadAgreement:mhAgree,multiHeadGap:mhSummary.winnerGap,multiHeadWinner:mhWinner,readiness:ready,failed:failed,reason:selected?'厳選ゲート通過':('見送り: '+failed.join(',')),base:base,model:method.id};"
if new_return not in text:
    if old_return not in text:
        raise SystemExit('strict selection return block not found')
    text = text.replace(old_return, new_return, 1)

text = text.replace(
    "reason=featured?'本日の厳選/メイン/重賞/高知ファイナル対象。v220は共通着順分布から5券種を生成し、確率差で自動的に点数を絞ります。':",
    "reason=featured?'厳選ゲート通過、または必須予想の重賞/高知ファイナル対象。必須予想は厳選扱いしません。':",
)

# For true selections, choose the bet family by hit probability / robustness,
# not by trifecta preference. Graded/Kochi races still receive the mandatory
# trifecta challenge later as a separate add-on.
old_sort = "candidates.sort(function(x,y){return y.score-x.score});"
new_sort = "candidates.sort(function(x,y){return y.score-x.score});\n  if(selected){\n    function hitPriority(c){\n      if(c.kind==='ワイド')return .42+.58*wideStrength;\n      if(c.kind==='馬連')return .34+.66*pairStrength;\n      if(c.kind==='3連複')return .30+.70*trioStrength;\n      if(c.kind==='馬単')return .18+.52*exactStrength+.30*winClarity;\n      if(c.kind==='3連単')return .08+.46*triStrength+.46*winClarity;\n      return n(c.score)\n    }\n    candidates.sort(function(x,y){return hitPriority(y)-hitPriority(x)||y.score-x.score})\n  }"
if new_sort not in text:
    if old_sort not in text:
        raise SystemExit('candidate sort block not found')
    text = text.replace(old_sort, new_sort, 1)

# UI copy: selected can be zero. This is deliberate.
text = text.replace(
    '<b>厳選レース</b><small>全レース比較から少数精鋭だけ・時間順</small>',
    '<b>厳選レース</b><small>基準未達なら0件・本当に強い時だけ</small>',
)

PATH.write_text(text, encoding='utf-8')
print('selection policy enforced: multi-head agreement + hit-first bets; graded/Kochi stay separate')
