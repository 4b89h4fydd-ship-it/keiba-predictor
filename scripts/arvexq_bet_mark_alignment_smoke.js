// Offline regression: display the model's actual ticket and explain differences
// from marks. Do not turn ☆+ rank into invented exacta probabilities.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const begin=src.indexOf('function captureExactaBetEvidence('),end=src.indexOf('function buildAiBetPlan(',begin);
assert.ok(begin>=0&&end>begin,'model evidence and explanatory functions missing');
const implementation=new Function('n','isScratchHorse','betComboText','esc',
  src.slice(begin,end)+'\nreturn {captureExactaBetEvidence,alignBetPlanToMarks,attachAiBetExplanation,aiBetExplanationHtml};');
const api=implementation(
 (v,f=0)=>{const x=Number(v);return Number.isFinite(x)?x:f;},
 h=>!!h.scratch,
 (kind,cs)=>cs.map(c=>c.join(kind==='馬単'?' → ':' - ')).join(' / '),
 v=>String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;')
);
const marks=[
 {horse:{horseNumber:1},predMark:'☆'},
 {horse:{horseNumber:2},predMark:'☆+'},
 {horse:{horseNumber:3},predMark:'▲'},
 {horse:{horseNumber:4},predMark:'◎'},
 {horse:{horseNumber:6},predMark:'○'}
],race={id:'test-race'}, p={rows:marks};
const rank=[
 {combo:[4,1],score:.15},{combo:[4,6],score:.14},
 {combo:[4,2],score:.10},{combo:[4,3],score:.03}
];
const evidence=api.captureExactaBetEvidence(rank,marks);
assert.equal(evidence.axis,4);
assert.equal(evidence.pairs.length,4);
assert.ok(evidence.pairs[0].p2GivenFirst>evidence.pairs[2].p2GivenFirst);
function make(){
 return {raceId:'test-race',reason:'original model',items:[
  {kind:'馬単',combos:[[4,1],[4,6]],points:2,combo:'4 → 1 / 4 → 6'},
  {kind:'3連複',combos:[[3,4,6],[1,4,6]],points:2}
 ],exactaEvidence:evidence};
}
let plan=api.alignBetPlanToMarks(make(),race,p);
assert.deepEqual(plan.items[0].combos,[[4,1],[4,6]],'model-favoured ☆1 must NOT be rewritten to ☆+2');
assert.deepEqual(plan.items[1].combos,[[3,4,6],[1,4,6]],'trio must retain actual third-place candidates');
assert.equal(plan.markAlignment.mismatches[0].second,1,'marked divergence must be detected');
plan=api.attachAiBetExplanation(plan,race,p);
assert.ok(plan.betExplanation.lines.some(x=>/条件付き2着推定/.test(x)));
assert.ok(plan.betExplanation.lines.some(x=>/印と異なる理由/.test(x)&&/☆1/.test(x)&&/☆\+2/.test(x)));
assert.match(api.aiBetExplanationHtml(plan),/この買い目になった理由/);
assert.deepEqual(plan.items[0].combos,[[4,1],[4,6]],'explanations never change predicted picks');
const contradictory=make();
contradictory.exactaEvidence=api.captureExactaBetEvidence([
 {combo:[4,2],score:.18},{combo:[4,1],score:.10},{combo:[4,6],score:.08}
],marks);
const mismatch=api.attachAiBetExplanation(api.alignBetPlanToMarks(contradictory,race,p),race,p);
assert.ok(mismatch.betExplanation.lines.some(x=>/印との不整合を検出/.test(x)),'cannot invent favourable probabilities');
const frozen=make();frozen.fixedAt='2026-10-08T00:00:00Z';
assert.strictEqual(api.alignBetPlanToMarks(frozen,race,p),frozen);
assert.strictEqual(api.attachAiBetExplanation(frozen,race,p),frozen);
assert.deepEqual(frozen.items[0].combos,[[4,1],[4,6]],'historical tickets immutable');
assert.match(api.aiBetExplanationHtml(frozen),/後付け説明はしません/);
const noOdds=make();delete noOdds.exactaEvidence;
const noScore=api.attachAiBetExplanation(noOdds,race,p);
assert.ok(noScore.betExplanation.lines.some(x=>/確率差は断定しません/.test(x)));
const noTicket=api.attachAiBetExplanation({items:[],decision:'見送り'},race,p);
assert.ok(noTicket.betExplanation.lines.some(x=>/見送りました/.test(x)));
assert.ok(src.includes('vp=attachAiBetExplanation(vp,r,p)'),'local model requires explanations');
assert.ok(src.includes('plan=attachAiBetExplanation(plan,r,p)'),'central model requires explanations');
const legacyModel=fs.readFileSync('arvexq/ui/static/betting/legacy_v213_order_model.js','utf8');
assert.ok(legacyModel.includes('exactaEvidence:captureExactaBetEvidence(exactaRank,rows)'),'dedicated ordered-role model must persist exact score evidence');
assert.ok(src.includes('aiBetExplanationHtml(plan)'),'explanations visible on bet page');
console.log('BET_MODEL_EXPLANATION_OK picks=unchanged differential=grounded inverted_scores=warning fixed=immutable');
