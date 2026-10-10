// Verify that pre-race evidence gaps cannot be presented as a purchasable ticket.
// Synthetic test rows only; historical hit rate is NOT inferred from these tests.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function paceEvidenceProfile(');
const end=src.indexOf('function buildAiBetPlan(',start);
assert.ok(start>=0&&end>start,'pace evidence gate must precede ticket generation');
const n=(v,f=0)=>{
  if(v===null||v===undefined||v==='')return f;
  const x=Number(v);return Number.isFinite(x)?x:f;
};
const completeReadiness={prediction:.92,card:1,history:1,actualOdds:1,
  bodyWeight:1,environment:1,analysis:.85};
const sourceHistory=src.slice(src.indexOf('function historicalWindow('),src.indexOf('function minetaPastProfile('));
const win={};
new Function('window',fs.readFileSync('arvexq/ui/static/betting/bet_readiness.js','utf8'))(win);
const api=new Function('n','isScratchHorse','dataReadinessProfile','window',
  sourceHistory+src.slice(start,end)+'\nreturn {paceEvidenceProfile,gateBetByPaceEvidence};')(
    n,h=>!!h.scratched,(race,p)=>p.readiness||completeReadiness,win);
const race={id:'nar-2026-10-08-大井-04',date:'2026-10-08',circuit:'地方',track:'大井',
  careerReadiness:{ready:true}};
function row(no,positions=3,options={}){
  const runs=Array.from({length:positions},(_,i)=>({
    date:'2026-09-'+String(30-i).padStart(2,'0'),fieldSize:12,
    cornerPositions:[no===1?1:Math.min(no+1,8),no===1?2:Math.min(no+1,8),no===1?2:Math.min(no+1,8)],
  }));
  return {horse:{horseNumber:no,recentRaces:runs,...options},winnerDecisionProbability:no===1?.35:no===2?.25:.12};
}
function prediction(rows){
  return {rows,arrangement:{leadCandidates:rows.slice(0,2)}};
}
function plan(){
  return {decision:'強く買う',betQuality:95,items:[{kind:'3連単',combos:[[1,2,3]],points:1}],
    trifectaDecision:'採用',primaryKind:'3連単',secondaryKind:'',reason:'元のモデル'};
}
const sufficient=prediction([1,2,3,4,5].map(no=>row(no)));
assert.equal(api.paceEvidenceProfile(race,sufficient).ready,true,'full historical evidence should remain bettable');
const approved=api.gateBetByPaceEvidence(plan(),race,sufficient);
assert.equal(approved.decision,'強く買う','do not blank strong signal with sufficient source evidence');
assert.equal(approved.items.length,1);
const noOdds=prediction([1,2,3,4,5].map(no=>row(no)));
noOdds.readiness={...completeReadiness,actualOdds:0};
const blockedOdds=api.gateBetByPaceEvidence(plan(),race,noOdds);
assert.equal(blockedOdds.decision,'強く買う','odds are optional for model-only tickets');
assert.ok(blockedOdds.betInputGate.warnings.some(x=>x.includes('実オッズ')));
assert.equal(blockedOdds.betInputGate.oddsVerified,false);
const noWeights=prediction([1,2,3,4,5].map(no=>row(no)));
noWeights.readiness={...completeReadiness,bodyWeight:0};
assert.equal(api.gateBetByPaceEvidence(plan(),race,noWeights).decision,'強く買う',
  'body weight is not necessary for an evidence-backed model ticket');
const tooThin=prediction([row(1,0),row(2,1),row(3,3),row(4,3),row(5,3)]);
const gated=api.gateBetByPaceEvidence(plan(),race,tooThin);
assert.equal(gated.decision,'見送り');
assert.deepEqual(gated.items,[]);
assert.equal(gated.trifectaDecision,'見送り');
assert.equal(gated.betQuality,0);
assert.match(gated.reason,/位置取り/);
const future=prediction([row(1,0,{recentRaces:[{
  date:'2026-10-09',fieldSize:12,cornerPositions:[1,1,1]
}]}),row(2),row(3),row(4),row(5)]);
assert.equal(api.paceEvidenceProfile(race,future).ready,false,'future data must never satisfy the gate');
assert.equal(api.gateBetByPaceEvidence(plan(),race,future).decision,'見送り',
 'future corners alone cannot satisfy model purchase evidence');
const scratch=prediction([row(1),row(2),row(3),row(4),row(5,0,{scratched:true})]);
assert.equal(api.paceEvidenceProfile(race,scratch).totalHorses,4,'scratched horses excluded');
const unchanged=api.gateBetByPaceEvidence({decision:'見送り',items:[],reason:'別理由'},race,tooThin);
assert.equal(unchanged.reason,'別理由','do not overwrite an existing safety rationale');
assert.ok(src.includes('vp=gateBetByPaceEvidence(vp,r,p)'),'regional bet path needs pace gate');
assert.ok(src.includes('plan=gateBetByPaceEvidence(plan,r,p)'),'central bet path needs pace gate');
assert.ok(src.indexOf('vp=gateBetByPaceEvidence(vp,r,p)')<src.indexOf('vp=forceMandatoryTrifecta(vp,r,p)'));
assert.ok(src.indexOf('plan=gateBetByPaceEvidence(plan,r,p)')<src.indexOf('plan=forceMandatoryTrifecta(plan,r,p)'));
const reference=win.ARVEXQBetReadiness.promoteReference(
  {selectionAudit:{selected:false,score:64,evidence:.60}},race,
  {coverage:.7,rows:sufficient.rows},completeReadiness);
assert.equal(reference.referenceOnly,true,'routine race may have a separate reference ticket');
assert.equal(reference.selectionAudit.selected,true,'ticket gate may independently assess a routine race');
assert.equal(reference.selectionAudit.referenceOnly,true,'but it is NEVER an elite morning selection');
assert.equal(win.ARVEXQBetReadiness.promoteReference(
  {selectionAudit:{selected:false,score:12,evidence:.15}},race,
  {coverage:.7,rows:sufficient.rows},completeReadiness).selectionAudit.selected,false,
  'low-quality races remain skipped');
const caution=win.ARVEXQBetReadiness.evaluate(race,sufficient,
  api.paceEvidenceProfile(race,sufficient),{...completeReadiness,actualOdds:0,bodyWeight:0});
assert.equal(caution.ready,true,'missing early publication is not a model ticket veto');
assert.equal(caution.oddsVerified,false);
assert.ok(caution.warnings.length>=2);
console.log('PACE_BET_GATE_OK evidence=required optional_odds_and_weight=warnings future=excluded reference_only=validated');
