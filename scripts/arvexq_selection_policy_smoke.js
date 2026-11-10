'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={window:{},Date,Set,Number,Object,Array,String,Math};vm.createContext(ctx);
vm.runInContext(fs.readFileSync('arvexq/ui/static/morning/rank_selection.js','utf8'),ctx);
const mod=ctx.window.ARVEXQMorningRankSelection;
const detail={id:'nar-2026-11-11-川崎-01',date:'2026-11-11',startTime:'15:00',predictionStatus:'ready',
  horses:[1,2,3,4,5].map(n=>({horseNumber:n,winOdds:n===1?2:n===2?3:n===3?4:n===4?5:20})),
  predictionMarks:[{horseNumber:1,mark:'◎'}],unifiedForecast:{version:'arvexq-unified-live-v1',
    modelVersion:'arvexq-rewrite-v3-v9b',raceId:'nar-2026-11-11-川崎-01',marks:[],
    modelHash:'m',receiptSha256:'r',capturedAt:'2026-11-11T14:35:00+09:00',ticketPlan:{}}};
assert.equal(mod.judge(detail,{circuit:'地方'},{races:{[detail.id]:{marks:{5:'◎'}}}}),null,
  'v26-only rank signal never selects production ticket');
const historical=JSON.parse(JSON.stringify(detail));historical.date='2026-11-10';
assert.equal(mod.judge(historical,{circuit:'地方'},{races:{[detail.id]:{marks:{5:'◎'}}}}),null);
const e={version:mod.POLICY_VERSION,raceId:detail.id,raceDate:detail.date,selected:true,status:'selected',
  modelVersion:detail.unifiedForecast.modelVersion,modelHash:'m',forecastReceipt:'r',
  forecastCapturedAt:detail.unifiedForecast.capturedAt,decidedAt:'2026-11-11T14:41:00+09:00',
  marketObservedAt:'2026-11-11T14:40:00+09:00',marketSha256:'market',policySha256:'policy',
  validationStatus:'approved-out-of-sample',validationEvidence:{status:'approved-out-of-sample',
    modelHash:'m',policySha256:'policy',evidenceSha256:'test-only',validatedThrough:'2026-11-10'},
  hitProbability:.8,stressExpectedReturn:1.2,items:[{kind:'ワイド',combo:[1,2],oddsLow:2,probability:.8}]};
detail.unifiedForecast.ticketPlan.selectionEvaluation=e;
const now=Date.parse('2026-11-11T14:42:00+09:00');
assert.equal(mod.assess(detail,now).status,'selected');
e.validationEvidence.validatedThrough='2026-11-11';assert.equal(mod.assess(detail,now).status,'unassessed');
e.validationEvidence.validatedThrough='2026-11-10';e.items.push({...e.items[0]});
assert.equal(mod.assess(detail,now).status,'unassessed','duplicate portfolio cannot qualify');
console.log('SELECTION_IDENTITY_FRESHNESS_NO_UNVALIDATED_RECOMMENDATION_PASS');
