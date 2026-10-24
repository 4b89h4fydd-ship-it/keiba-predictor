/* Regression: full D1 Stage64 facts outrank stale day-summary forecast flags.
 * Pure UI merge contract. No network, second model, or forecast derivation.
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function authorizedStage64Detail(');
const end=src.indexOf('function raceDisplayCoreReady(',start);
assert(start>=0 && end>start,'live race merge/authoritative detail functions missing');
const harness=src.slice(start,end);
const ctx={
  reflectUseful:v=>v!==null && v!==undefined && v!=='' && (!Array.isArray(v) || v.length>0),
  mergePublishedResult:(oldResult,newResult)=>Object.assign({},oldResult||{},newResult||{}),
  n:v=>Number(v)||0,
  mergeHorseReflection:(old,newer,live)=>Object.assign({},old||{},newer||{},live||{}),
  mergeResultHorseFields:x=>x,
  window:{},
};
vm.createContext(ctx);
vm.runInContext(harness,ctx);

const horses=Array.from({length:5},(_,i)=>({horseNumber:i+1,name:'馬'+(i+1)}));
const symbols=['◎','○','▲','△','☆'];
function stage64(raceId,date){
  const marks=horses.map((h,i)=>({horseNumber:h.horseNumber,mark:symbols[i]}));
  const model={raceId,date,modelVersion:'arvexq-stage64-product-v1',
    predictionStatus:'ready',productionEligible:true,
    forecastText:'確認済みの展開根拠',
    stages:{pace:{value:[{1:0,2:0,3:0,4:0,5:0}]}}};
  return {id:raceId,date,circuit:'地方',track:'園田',raceNumber:3,
    predictionStatus:'ready',predictionModelVersion:model.modelVersion,
    prediction:model,predictionMarks:marks,forecastText:model.forecastText,
    recommendedBets:[{kind:'ワイド',combos:[[1,2]],points:1}],horses};
}
const id='nar-2026-10-24-園田-03',date='2026-10-24';
const full=stage64(id,date);
const summary={id,date,raceStatus:'確定',predictionStatus:'disabled',
  predictionModelVersion:'arvexq-prediction-removed',
  prediction:{modelVersion:'old-unsupported'},
  predictionMarks:[{horseNumber:5,mark:'◎'}],
  recommendedBets:[{kind:'3連単',combos:[[5,4,3]],points:1}],
  forecastText:'古い予想'};
const merged=ctx.mergeRaceReflection({id,date,horses},full,null,summary);
assert.equal(merged.predictionStatus,'ready','stale summary must not disable sealed detail');
assert.equal(merged.predictionModelVersion,'arvexq-stage64-product-v1');
assert.equal(merged.prediction.modelVersion,'arvexq-stage64-product-v1');
assert.deepEqual(JSON.parse(JSON.stringify(merged.predictionMarks)),full.predictionMarks);
assert.deepEqual(JSON.parse(JSON.stringify(merged.recommendedBets)),full.recommendedBets);
assert.equal(merged.forecastText,full.forecastText);
assert.equal(merged.raceStatus,'確定','official result state still updates');
assert.equal(merged.horses.length,5,'roster stays intact');

// A spoofed or incomplete detail is not a valid sealed forecast, and
// stale summary is not suppressed for such a record.
const broken=stage64(id,date);
broken.prediction.raceId='nar-2026-10-24-園田-04';
assert.equal(ctx.authorizedStage64Detail(broken),false);
const notSealed=ctx.mergeRaceReflection({id,date,horses},broken,null,summary);
assert.equal(notSealed.predictionStatus,'disabled');

const wrongMarks=stage64(id,date);
wrongMarks.predictionMarks[0].horseNumber=99;
assert.equal(ctx.authorizedStage64Detail(wrongMarks),false);

// The previous server-sealed receipt wins when the incoming summary is
// missing prediction fields; do not erase ticket evidence during refresh.
const refresh=ctx.mergeRaceReflection(merged,{id,date,raceStatus:'確定',horses},null,{id,date});
assert.equal(refresh.predictionStatus,'ready');
assert.equal(refresh.recommendedBets[0].kind,'ワイド');
console.log('STAGE64_LIVE_DETAIL_SUMMARY_PRECEDENCE_OK');


// The active betting view must show both Kochi final three-horse wager kinds,
// including an unmarked third runner, without consulting actual finishers.
const ticketSource=fs.readFileSync('arvexq/ui/static/forecast/ticket_frame.js','utf8');
const ticketWindow={};
vm.runInNewContext(ticketSource,{window:ticketWindow});
const kochiFinal={
  id:'nar-2026-10-25-高知-12',date:'2026-10-25',track:'高知',
  title:'ファイナルレースＣ３－１９記者選抜',
  predictionStatus:'ready',recommendedBets:[
    {kind:'3連複',combos:[[1,2,6],[1,3,6],[2,3,6]],points:3},
    {kind:'3連単',combos:[[6,1,2],[1,2,6]],points:2}
  ]
};
const finalHtml=ticketWindow.ARVEXQTicketFrame.contents(kochiFinal,{});
assert.match(finalHtml,/高知ファイナル：全出走馬から3着候補を評価/);
assert.match(finalHtml,/3連複/);
assert.match(finalHtml,/3連単/);
assert.match(finalHtml,/6 - 1 - 2/);
const normalHtml=ticketWindow.ARVEXQTicketFrame.contents({...kochiFinal,track:'大井'},{});
assert.match(normalHtml,/Stage64確率順・全印考慮/);
console.log('KOCHI_FINAL_TRIPLE_UI_PASS');
