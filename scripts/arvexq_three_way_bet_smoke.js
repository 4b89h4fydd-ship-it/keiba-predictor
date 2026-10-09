// Synthetic-only regression: never confuse model weights with real betting accuracy.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const moduleSrc=fs.readFileSync('arvexq/ui/static/betting/three_way_engine.js','utf8');
const n=(x,f=0)=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):f;
const betGlobal={};
new Function('window',moduleSrc)(betGlobal);
const policy=(base,r,p)=>betGlobal.ARVEXQThreeWayBet.compose(base,r,p,{
 n,clamp:(x,a,b)=>Math.max(a,Math.min(b,x)),isScratchHorse:h=>!!h.scratched,
 betComboText:(kind,cs)=>cs.map(c=>c.join(kind==='馬単'||kind==='3連単'?' → ':' - ')).join(' / ')
});
const weights=[
 [.55,.03,.03],[.19,.25,.13],[.11,.22,.27],[.06,.18,.24],
 [.04,.13,.17],[.025,.10,.10],[.015,.06,.04],[.01,.03,.02]
];
const rows=weights.map((v,i)=>({
 horse:{horseNumber:i+1,integratedEvaluation:{}},
 ticketP1Probability:v[0],ticketP2Probability:v[1],ticketP3Probability:v[2],
 predMark:['☆','◎','○','▲','☆+','☆','△','注'][i]
}));
const base=()=>({
 engineVersion:'prior-model',
 decision:'通常買い',reason:'synthetic ready',
 betInputGate:{ready:true},selectionAudit:{selected:true},
 audit:{orderConfidence:.83},items:[
  {level:'本線',kind:'ワイド',combos:[[2,3]],points:1}
 ]});
const race={id:'synthetic',date:'2026-10-12',startTime:'11:00',circuit:'地方'};
const prediction={rows,outcome:{first:[rows[0]],second:[rows[1],rows[2]],third:[rows[2],rows[3],rows[4]]}};
const plan=policy(base(),race,prediction);
assert.equal(plan.engineVersion,'arvexq-three-way-v346');
assert.equal(plan.expectedValue,null,'no invented EV');
assert.equal(plan.trifectaReviewed,true,'every race is reviewed');
assert.equal(plan.trifectaDecision,'採用',JSON.stringify(plan.threeWayAudit));
assert.ok(plan.items.find(z=>z.level==='本線'),'exactly one main ticket family');
assert.equal(plan.items.filter(z=>z.level==='本線').length,1);
const trifecta=plan.items.find(z=>z.level==='3連単チャレンジ');
assert.ok(trifecta,'challenge is independent of main');
assert.ok(trifecta.points>=6&&trifecta.points<=12,'trifecta is only 6-12 points');
assert.ok(trifecta.combos.every(x=>x.length===3&&x[0]===1&&new Set(x).size===3),
  'use independent winner rather than ◎');
assert.ok(plan.trifectaSecond.length>1&&plan.trifectaThird.length>1,'conditional positions');
const insurance=plan.items.filter(z=>z.level==='保険');
assert.ok(insurance.length<=1&&(!insurance.length||insurance[0].points<=1),'minimum hedge');
assert.equal(plan.referenceBudget.points,plan.items.reduce((t,x)=>t+x.points,0));
const differentMarks={...prediction,rows:rows.map((x,i)=>({...x,predMark:i===0?'◎':'△'}))};
const again=policy(base(),race,differentMarks);
assert.deepEqual(again.items.map(x=>x.combos),plan.items.map(x=>x.combos),'marks are annotations, not ticket order');
const unsafe=policy({...base(),betInputGate:{ready:false}},race,prediction);
assert.deepEqual(unsafe.items,[],'insufficient evidence must block every ticket');
assert.equal(unsafe.trifectaDecision,'見送り');
assert.ok(unsafe.trifectaReason,'missed challenge requires a reason');
const confused=policy({...base(),audit:{orderConfidence:.03}},race,prediction);
assert.equal(confused.trifectaDecision,'見送り','low ordering confidence blocks trifecta');
assert.ok(confused.items.every(x=>x.level!=='3連単チャレンジ'));
assert.ok(!src.includes('function composeThreeWayBetPolicy(r,p)'),'policy must consume audited model');
assert.ok(src.includes('window.ARVEXQThreeWayBet.compose(base,r,p'),'bridge must invoke standalone engine');
assert.ok(src.includes('vp=composeThreeWayBetPolicy(vp,r,p)'),'local branch');
assert.ok(src.includes('plan=composeThreeWayBetPolicy(plan,r,p)'),'central branch');
assert.ok(src.includes("if(stored)return immutableStoredAiBetView(r,stored)"),'saved bets take precedence');
assert.ok(src.includes('if(terminal)return null'),'never create new bets post-off');

const markArea=src.slice(src.indexOf('function assignPredictionMarks('),src.indexOf('function applyFrozenMarks(',src.indexOf('function assignPredictionMarks(')));
assert.ok(markArea.includes("policy:'official-only-morning-lock'"),'mark selection must not use prior-race trends');
assert.ok(!markArea.includes('dayCorr=sameDayCorrectionProfileV313(r,rows)'),'no prior results in marks');
const paceArea=src.slice(src.indexOf('function paceOutcomeModel('),src.indexOf('function ',src.indexOf('function paceOutcomeModel(')+9));
assert.ok(paceArea.includes("policy:'past-results-do-not-revise-pace-or-marks'"),'pace outcomes cannot change after a prior result');
const factorArea=src.slice(src.indexOf('function v207',0),src.indexOf('function assignPredictionMarks('));
assert.ok(src.includes("mode:'observation-only-no-prediction'"),'same-day track analysis observational only');
assert.ok(src.includes("return 'morning-fixed-official-condition-only-v346'"),'results cannot trigger new marks');

console.log('THREE_WAY_BET_OK selected='+plan.items.map(z=>z.level+':'+z.kind+'='+z.points).join(',')+
  ' trifecta_skip=validated evidence_gate=validated EV=not_invented');
