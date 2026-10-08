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
const api=new Function('n','isScratchHorse','dataReadinessProfile',src.slice(start,end)+
  '\nreturn {paceEvidenceProfile,gateBetByPaceEvidence};')(
    n,h=>!!h.scratched,(race,p)=>p.readiness||completeReadiness);
const race={id:'nar-2026-10-08-大井-04',date:'2026-10-08',circuit:'地方',track:'大井'};
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
assert.equal(blockedOdds.decision,'見送り','forecast odds are insufficient to buy');
assert.ok(blockedOdds.betInputGate.missing.includes('実オッズ'));
const noWeights=prediction([1,2,3,4,5].map(no=>row(no)));
noWeights.readiness={...completeReadiness,bodyWeight:0};
assert.equal(api.gateBetByPaceEvidence(plan(),race,noWeights).decision,'見送り');
const tooThin=prediction([row(1,0),row(2,1),row(3,3),row(4,3),row(5,3)]);
const gated=api.gateBetByPaceEvidence(plan(),race,tooThin);
assert.equal(gated.decision,'見送り');
assert.deepEqual(gated.items,[]);
assert.equal(gated.trifectaDecision,'見送り');
assert.equal(gated.betQuality,0);
assert.match(gated.reason,/先行/);
const future=prediction([row(1,0,{recentRaces:[{
  date:'2026-10-09',fieldSize:12,cornerPositions:[1,1,1]
}]}),row(2),row(3),row(4),row(5)]);
assert.equal(api.paceEvidenceProfile(race,future).ready,false,'future data must never satisfy the gate');
const scratch=prediction([row(1),row(2),row(3),row(4),row(5,0,{scratched:true})]);
assert.equal(api.paceEvidenceProfile(race,scratch).totalHorses,4,'scratched horses excluded');
const unchanged=api.gateBetByPaceEvidence({decision:'見送り',items:[],reason:'別理由'},race,tooThin);
assert.equal(unchanged.reason,'別理由','do not overwrite an existing safety rationale');
assert.ok(src.includes('vp=gateBetByPaceEvidence(vp,r,p)'),'regional bet path needs pace gate');
assert.ok(src.includes('plan=gateBetByPaceEvidence(plan,r,p)'),'central bet path needs pace gate');
assert.ok(src.indexOf('vp=gateBetByPaceEvidence(vp,r,p)')<src.indexOf('vp=forceMandatoryTrifecta(vp,r,p)'));
assert.ok(src.indexOf('plan=gateBetByPaceEvidence(plan,r,p)')<src.indexOf('plan=forceMandatoryTrifecta(plan,r,p)'));
console.log('PACE_BET_GATE_OK sparse=fails odds=required weights=required future=excluded scratches=excluded complete=unchanged historical=immutable');
