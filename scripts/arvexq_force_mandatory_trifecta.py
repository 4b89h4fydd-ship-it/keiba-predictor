#!/usr/bin/env python3
from pathlib import Path

PATH = Path("arvexq/ui/static/app.js")
text = PATH.read_text(encoding="utf-8")

helper = r'''function mandatoryTrifectaRace(r){
  var title=String(r&&r.title||'');
  return !!(r&&(raceIsGraded(r)||(String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))))
}
function forceMandatoryTrifecta(plan,r,p){
  if(!plan||!mandatoryTrifectaRace(r))return plan;
  var rows=(p&&p.rows||[]).slice().filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)});
  if(rows.length<3)return plan;
  function no(x){return x&&x.horse?n(x.horse.horseNumber):0}
  function win(x){return n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,0)))}
  var axis=rows.filter(function(x){return String(x.predMark||'')==='◎'})[0]||rows.slice().sort(function(a,b){return win(b)-win(a)})[0]||null;
  var axisNo=no(axis);if(!axisNo)return plan;
  var markOrder={'○':0,'▲':1,'☆+':2,'☆':3,'△':4,'注+':5,'注':6,'':7};
  var mates=rows.filter(function(x){return no(x)!==axisNo}).sort(function(a,b){
    var ma=String(a.predMark||''),mb=String(b.predMark||''),ra=markOrder.hasOwnProperty(ma)?markOrder[ma]:8,rb=markOrder.hasOwnProperty(mb)?markOrder[mb]:8;
    return ra-rb||win(b)-win(a)||no(a)-no(b)
  }).slice(0,3),combos=[];
  for(var i=0;i<mates.length;i++)for(var j=0;j<mates.length;j++)if(i!==j)combos.push([axisNo,no(mates[i]),no(mates[j])]);
  if(!combos.length)return plan;
  plan.items=(plan.items||[]).filter(function(z){return !(z&&z.kind==='3連単')});
  plan.items.push({level:'3連単チャレンジ',kind:'3連単',combos:combos,points:combos.length,combo:betComboText('3連単',combos),confidence:'チャレンジ',mandatory:true});
  plan.trifectaReviewed=true;plan.trifectaDecision='採用';plan.trifectaReason='重賞・高知ファイルは3連単チャレンジ必須。◎1着固定で相手上位3頭を2・3着入替。';
  if(plan.decision==='見送り')plan.decision='通常買い';
  plan.mandatoryTrifecta=true;
  return plan
}
'''

anchor = "function raceIsGraded(r){"
if "function mandatoryTrifectaRace(r){" not in text:
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("raceIsGraded anchor not found")
    end = text.find("\n", idx)
    if end < 0:
        raise SystemExit("raceIsGraded line end not found")
    text = text[:end+1] + helper + text[end+1:]

old = "plan=rebuildBetStrategyV242(plan,r,p);saveStoredAiBet(r,plan);return plan"
new = "plan=rebuildBetStrategyV242(plan,r,p);plan=forceMandatoryTrifecta(plan,r,p);saveStoredAiBet(r,plan);return plan"
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("buildAiBetPlan finalization anchor not found")

# Do not emit the generic trifecta-skip copy for mandatory races.
old_copy = "if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')lines.push('3連単｜検討済み｜順序信頼不足で見送り｜'+String(plan.orderScore||0)+'/100');"
new_copy = "if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り'&&!mandatoryTrifectaRace(r))lines.push('3連単｜検討済み｜順序信頼不足で見送り｜'+String(plan.orderScore||0)+'/100');"
if old_copy in text:
    text = text.replace(old_copy, new_copy, 1)
elif new_copy not in text:
    raise SystemExit("betTransferText trifecta-skip line not found")

for required in (
    "function mandatoryTrifectaRace(r){",
    "function forceMandatoryTrifecta(plan,r,p){",
    "plan=forceMandatoryTrifecta(plan,r,p)",
    "重賞・高知ファイルは3連単チャレンジ必須",
):
    if required not in text:
        raise SystemExit(f"mandatory trifecta patch missing: {required}")

PATH.write_text(text, encoding="utf-8")
print("mandatory trifecta challenge enforced for graded and Kochi final races")
