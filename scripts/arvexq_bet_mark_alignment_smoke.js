// Offline regression: visible marks must agree with still-unlocked exacta tickets.
// It deliberately does not import or execute the full browser application.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function alignBetPlanToMarks(');
const end=src.indexOf('function buildAiBetPlan(',start);
assert.ok(start>=0&&end>start,'final mark reconciliation must be defined before both bet models');
const fn=new Function('n','isScratchHorse','betComboText',src.slice(start,end)+'; return alignBetPlanToMarks;')(
 (v,f=0)=>{const z=Number(v);return Number.isFinite(z)?z:f;},
 h=>!!h.scratch,
 (kind,cs)=>cs.map(c=>c.join(kind==='馬単'?' → ':' - ')).join(' / ')
);
const marks=[
 {horse:{horseNumber:1},predMark:'☆',ticketP2Probability:.42},
 {horse:{horseNumber:2},predMark:'☆+',ticketP2Probability:.12},
 {horse:{horseNumber:3},predMark:'▲',ticketP2Probability:.3},
 {horse:{horseNumber:4},predMark:'◎',ticketP2Probability:.13},
 {horse:{horseNumber:6},predMark:'○',ticketP2Probability:.35}
];
const data={rows:marks};
const base=()=>({reason:'original forecast',items:[
 {kind:'馬単',combos:[[4,1],[4,6]],points:2,combo:'4 → 1 / 4 → 6'},
 {kind:'3連複',combos:[[3,4,6],[1,4,6]],points:2,combo:'3 - 4 - 6 / 1 - 4 - 6'}
]});
const plan=fn(base(),{},data);
assert.deepEqual(plan.items[0].combos,[[4,6],[4,2]],'◎4 must go first, ○6 / ☆+2 must outrank ☆1');
assert.equal(plan.items[0].combo,'4 → 6 / 4 → 2');
assert.deepEqual(plan.items[1].combos,[[3,4,6],[1,4,6]],'keep ☆ third-place specialist in independent 3連複');
assert.match(plan.reason,/表示印との照合/);
assert.deepEqual(fn(plan,{},data).items[0].combos,[[4,6],[4,2]],'idempotent');
const frozen=base();frozen.fixedAt='2026-10-08T00:00:00Z';
assert.strictEqual(fn(frozen,{},data),frozen,'fixed object identity retained');
assert.deepEqual(frozen.items[0].combos,[[4,1],[4,6]],'locked historical tickets untouched');
const noAxis=base();const noAxisData={rows:marks.filter(x=>x.predMark!=='◎')};
assert.deepEqual(fn(noAxis,{},noAxisData).items[0].combos,[[4,1],[4,6]],'do not synthesize an ◎');
const noTicket=fn({items:[],reason:'skip'},{},data);
assert.equal(noTicket.items.length,0,'do not create tickets when gate says 見送り');
assert.ok(src.includes('vp=alignBetPlanToMarks(vp,r,p)'), 'local server-role model wired');
assert.ok(src.includes('plan=alignBetPlanToMarks(plan,r,p)'), 'central/fallback model wired');
assert.ok(src.includes("if(stored)return immutableStoredAiBetView(r,stored)"),'locked plans use immutable view');
console.log('BET_MARK_ALIGN_OK exacta=4→6/4→2 trio=unchanged locked=unchanged both-models=wired');
